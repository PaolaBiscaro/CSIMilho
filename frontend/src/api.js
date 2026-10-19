import { hasConsistentChartData } from './chart-data.js'

// The compiled app always uses the FastAPI origin; overrides are development-only.
const API_BASE_URL = import.meta.env.DEV ? (import.meta.env.VITE_API_BASE_URL ?? '') : ''

export async function getHealth({ signal } = {}) {
  const response = await connectivityRequest('/api/health', { signal })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError('Não foi possível conectar ao backend. Confira se o servidor está em execução.', response.status)
  if (payload?.status !== 'ok' || typeof payload.gemini_configured !== 'boolean'
    || !nonEmptyText(payload.model) || !nonEmptyText(payload.version)) {
    throw new ApiError('O backend retornou um diagnóstico inválido. Atualize o status para tentar novamente.', 502)
  }
  return { status: 'ok', gemini_configured: payload.gemini_configured, model: payload.model, version: payload.version }
}

const nonEmptyText = (value) => typeof value === 'string' && value.trim().length > 0
const GEMINI_TEST_ERRORS = {
  missing_api_key: 'Chave do Gemini não configurada no backend. Configure-a e atualize o status.',
  authentication_error: 'O Gemini recusou a chave. Confira a configuração no backend.',
  permission_denied: 'A chave não tem permissão para acessar o modelo configurado.',
  model_not_found: 'O modelo configurado não está disponível. Confira GEMINI_MODEL no backend.',
  rate_limit: 'O limite de uso do Gemini foi atingido. Aguarde antes de tentar novamente.',
  timeout: 'O Gemini demorou além do limite do teste. Tente novamente.',
  unavailable: 'O Gemini está temporariamente indisponível. Tente novamente mais tarde.',
  network_error: 'O backend não conseguiu acessar o Gemini. Confira a conexão com a internet.',
  invalid_response: 'A resposta do Gemini estava vazia ou bloqueada. O teste não foi confirmado.',
  configuration_error: 'A configuração do Gemini está inválida. Confira o backend.',
  invalid_request: 'O Gemini recusou o teste. Confira o modelo e a configuração no backend.',
  api_error: 'Não foi possível confirmar a conexão com o Gemini. Tente novamente.',
}

async function connectivityRequest(path, options) {
  try { return await fetch(`${API_BASE_URL}${path}`, options) } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('Não foi possível conectar ao backend. Confira se o servidor está em execução.', 0)
  }
}

export async function testGemini({ signal } = {}) {
  const response = await connectivityRequest('/api/gemini/test', { method: 'POST', signal })
  const payload = await response.json().catch(() => null)
  if (typeof payload?.success !== 'boolean' || payload.success !== response.ok
    || !nonEmptyText(payload.model) || !Number.isSafeInteger(payload.latency_ms) || payload.latency_ms < 0
    || (payload.success ? payload.error_code !== null : !nonEmptyText(payload.error_code))) {
    throw new ApiError('Não foi possível confirmar o teste: o backend retornou uma resposta inválida. Atualize o status e tente novamente.', response.status || 502)
  }
  return {
    success: payload.success, model: payload.model, latency_ms: payload.latency_ms,
    error_code: payload.success ? null : payload.error_code,
    message: payload.success ? 'Conexão com o Gemini verificada. Este teste não avalia a qualidade de uma investigação.'
      : (Object.hasOwn(GEMINI_TEST_ERRORS, payload.error_code) ? GEMINI_TEST_ERRORS[payload.error_code] : GEMINI_TEST_ERRORS.api_error),
  }
}

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

function hasValidReportCards(report, evidence) {
  const text = (value) => typeof value === 'string' && value.trim().length > 0
  const ids = new Set()
  for (const item of evidence) {
    if (!text(item?.evidence_id) || ids.has(item.evidence_id) || !text(item.method)
      || !Array.isArray(item.source_files) || !item.source_files.length || !item.source_files.every(text)) return false
    ids.add(item.evidence_id)
  }
  const validCards = (items, fields) => Array.isArray(items) && items.every((item) => item
    && fields.every((field) => text(item[field]))
    && Array.isArray(item.evidence_ids) && item.evidence_ids.length > 0
    && item.evidence_ids.every((id) => ids.has(id)))
  return validCards(report.findings, ['title', 'explanation'])
    && validCards(report.recommendations, ['action', 'reason'])
}

function hasValidAuditMetadata(report, trace) {
  const text = (value) => typeof value === 'string' && value.trim().length > 0
  const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)
  const texts = (value) => Array.isArray(value) && value.every(text)
  const timestamp = (value) => text(value) && /(Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value))
  const duration = (value) => typeof value === 'number' && Number.isFinite(value) && value >= 0
  return Array.isArray(report.limitations) && report.limitations.length > 0
    && report.limitations.every((item) => object(item) && ['title', 'explanation', 'rule_id'].every((key) => text(item[key])))
    && object(trace) && text(trace.model) && timestamp(trace.created_at) && Array.isArray(trace.calls)
    && trace.calls.every((call) => object(call) && Number.isInteger(call.sequence) && call.sequence > 0
      && text(call.tool) && text(call.tool_version) && object(call.arguments)
      && timestamp(call.started_at) && duration(call.duration_ms) && ['success', 'error'].includes(call.status)
      && texts(call.source_files) && texts(call.result_evidence_ids))
    && (trace.repair == null || (object(trace.repair) && ['success', 'error'].includes(trace.repair.status)
      && timestamp(trace.repair.started_at) && duration(trace.repair.duration_ms)))
}

export async function requestInvestigation(request) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/investigations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  } catch {
    throw new ApiError('Não foi possível comunicar com o backend. Confira se o servidor está em execução.', 0)
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const messages = {
      404: 'O pacote não está mais disponível nesta sessão. Importe os arquivos novamente.',
      422: 'Não foi possível investigar esse recorte. Confira os talhões, o período e a pergunta.',
      503: 'Não foi possível concluir a investigação. O backend informou uma falha no processamento.',
    }
    throw new ApiError(messages[response.status] ?? 'Não foi possível concluir a investigação.', response.status)
  }
  const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)
  if (payload?.status !== 'completed' || typeof payload.investigation_id !== 'string' || !payload.investigation_id.trim()
    || !['gemini', 'deterministic_fallback'].includes(payload.generated_by)
    || !isObject(payload.report) || !isObject(payload.report.overview)
    || !['headline', 'summary'].every((key) => typeof payload.report.overview[key] === 'string' && payload.report.overview[key].trim())
    || !['weak', 'moderate', 'strong'].includes(payload.report.overview.evidence_strength)
    || !Array.isArray(payload.evidence) || !hasValidReportCards(payload.report, payload.evidence) || !isObject(payload.chart_data)
    || !hasConsistentChartData(payload.chart_data, payload.evidence)
    || !hasValidAuditMetadata(payload.report, payload.trace) || !Array.isArray(payload.warnings)
    || !payload.warnings.every((item) => isObject(item) && typeof item.code === 'string' && typeof item.message === 'string')) {
    throw new ApiError('O backend retornou uma resposta de investigação inválida.', 502)
  }
  return payload
}

export async function requestReport(investigationId, { signal } = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/report`, { signal })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError('Não foi possível baixar o relatório. Confira a conexão com o backend.', 0)
  }
  if (!response.ok) throw new ApiError(response.status === 404
    ? 'O relatório não está mais disponível nesta sessão. Execute uma nova investigação.'
    : 'Não foi possível baixar o relatório. Tente novamente.', response.status)
  if (!response.headers.get('content-type')?.toLowerCase().startsWith('text/html')) {
    throw new ApiError('O backend retornou um arquivo de relatório inválido.', 502)
  }
  try { return await response.blob() } catch {
    throw new ApiError('O download do relatório foi interrompido. Tente novamente.', 0)
  }
}

export async function uploadDataset(files) {
  const body = new FormData()
  for (const file of files) {
    body.append('files', file, file.name)
  }

  const response = await fetch(`${API_BASE_URL}/api/datasets`, {
    method: 'POST',
    body,
  })
  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(
      payload?.errors?.[0]?.message ?? 'Não foi possível validar o pacote.',
      response.status,
      payload,
    )
  }

  return payload
}

export async function runDiagnostic(tool, arguments_, { signal } = {}) {
  const response = await fetch(`${API_BASE_URL}/api/diagnostics/tools`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool, arguments: arguments_ }),
    signal,
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(
      response.status === 404
        ? 'Diagnóstico indisponível. Use o ambiente de desenvolvimento e importe o pacote novamente se a sessão expirou.'
        : typeof payload?.detail === 'string' ? payload.detail : 'Não foi possível validar esta comparação.',
      response.status, payload,
    )
  }
  return payload
}
