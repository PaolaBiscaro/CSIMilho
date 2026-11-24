import { hasConsistentChartData } from './chart-data.js'

// The compiled app always uses the FastAPI origin; overrides are development-only.
const API_BASE_URL = import.meta.env.DEV ? (import.meta.env.VITE_API_BASE_URL ?? '') : ''

export async function getHealth({ signal } = {}) {
  const response = await connectivityRequest('/api/health', { signal })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError('Não foi possível conectar ao serviço de análise.', response.status)
  if (payload?.status !== 'ok' || typeof payload.gemini_configured !== 'boolean'
    || !nonEmptyText(payload.model) || !nonEmptyText(payload.version)) {
    throw new ApiError('O serviço de análise retornou um diagnóstico inválido.', 502)
  }
  return { status: 'ok', gemini_configured: payload.gemini_configured, model: payload.model, version: payload.version }
}

const nonEmptyText = (value) => typeof value === 'string' && value.trim().length > 0
const GEMINI_TEST_ERRORS = {
  missing_api_key: 'A conexão com o Gemini ainda não foi configurada.',
  authentication_error: 'O Gemini recusou a credencial configurada.',
  permission_denied: 'A chave não tem permissão para acessar o modelo configurado.',
  model_not_found: 'O modelo configurado não está disponível.',
  rate_limit: 'O limite de uso do Gemini foi atingido. Aguarde antes de tentar novamente.',
  timeout: 'O Gemini demorou além do limite do teste. Tente novamente.',
  unavailable: 'O Gemini está temporariamente indisponível. Tente novamente mais tarde.',
  network_error: 'Não foi possível acessar o Gemini. Confira a conexão com a internet.',
  invalid_response: 'A resposta do Gemini estava vazia ou bloqueada. O teste não foi confirmado.',
  configuration_error: 'A configuração do Gemini está inválida.',
  invalid_request: 'O Gemini recusou o teste. Confira o modelo configurado.',
  api_error: 'Não foi possível confirmar a conexão com o Gemini. Tente novamente.',
}

async function connectivityRequest(path, options) {
  try { return await fetch(`${API_BASE_URL}${path}`, options) } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('Não foi possível conectar ao serviço de análise.', 0)
  }
}

export async function testGemini({ signal } = {}) {
  const response = await connectivityRequest('/api/gemini/test', { method: 'POST', signal })
  const payload = await response.json().catch(() => null)
  if (typeof payload?.success !== 'boolean' || payload.success !== response.ok
    || !nonEmptyText(payload.model) || !Number.isSafeInteger(payload.latency_ms) || payload.latency_ms < 0
    || !Number.isSafeInteger(payload.configured_key_count) || payload.configured_key_count < 0 || payload.configured_key_count > 3
    || !Number.isSafeInteger(payload.available_key_count) || payload.available_key_count < 0
    || payload.available_key_count > payload.configured_key_count || !Array.isArray(payload.key_results)
    || payload.key_results.length !== payload.configured_key_count
    || payload.key_results.some((item, index) => item?.slot !== index + 1 || typeof item.success !== 'boolean'
      || !Number.isSafeInteger(item.latency_ms) || item.latency_ms < 0
      || (item.success ? item.error_code !== null : !nonEmptyText(item.error_code)))
    || (payload.success ? payload.available_key_count < 1 : !nonEmptyText(payload.error_code))) {
    throw new ApiError('Não foi possível confirmar o teste: o serviço retornou uma resposta inválida.', response.status || 502)
  }
  return {
    success: payload.success, model: payload.model, latency_ms: payload.latency_ms,
    configured_key_count: payload.configured_key_count,
    available_key_count: payload.available_key_count,
    key_results: payload.key_results.map((item) => ({ ...item })),
    error_code: payload.error_code,
    message: payload.success ? `${payload.configured_key_count === 1
      ? '1 de 1 chave do Gemini disponível'
      : `${payload.available_key_count} de ${payload.configured_key_count} chaves do Gemini disponíveis`}. Este teste não avalia a qualidade de uma investigação.`
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
    && report.recommendations.every((item) => (item.availability === undefined
      || ['continue_now', 'needs_data', 'needs_tooling'].includes(item.availability))
      && (item.suggested_question == null || text(item.suggested_question)))
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

function validateInvestigationPayload(payload) {
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
    throw new ApiError('O serviço retornou uma resposta de investigação inválida.', 502)
  }
  return payload
}

function investigationError(status) {
  const messages = {
    404: 'O pacote não está mais disponível nesta sessão. Importe os arquivos novamente.',
    422: 'Não foi possível investigar esse recorte. Confira os talhões, o período e a pergunta.',
    503: 'Não foi possível concluir a investigação por uma falha no processamento.',
  }
  return new ApiError(messages[status] ?? 'Não foi possível concluir a investigação.', status)
}

async function readInvestigationStream(response, onProgress) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result = null
  let streamError = null

  function consume(block) {
    const lines = block.split(/\r?\n/)
    const event = lines.find((line) => line.startsWith('event:'))?.slice(6).trim() ?? 'message'
    const data = lines.filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart()).join('\n')
    if (!data) return
    let payload
    try { payload = JSON.parse(data) } catch { throw new ApiError('O serviço enviou um evento de investigação inválido.', 502) }
    if (event === 'progress') {
      if (nonEmptyText(payload?.stage) && nonEmptyText(payload?.message)) {
        try { onProgress({ stage: payload.stage, message: payload.message, tool: payload.tool ?? '' }) } catch { /* UI callbacks do not cancel analysis. */ }
      }
      return
    }
    if (event === 'result') result = payload
    if (event === 'error') streamError = investigationError(Number.isInteger(payload?.status) ? payload.status : 503)
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    let separator = buffer.search(/\r?\n\r?\n/)
    while (separator >= 0) {
      const match = buffer.slice(separator).match(/^\r?\n\r?\n/)[0]
      consume(buffer.slice(0, separator))
      buffer = buffer.slice(separator + match.length)
      separator = buffer.search(/\r?\n\r?\n/)
    }
    if (done) break
  }
  if (buffer.trim()) consume(buffer)
  if (streamError) throw streamError
  return validateInvestigationPayload(result)
}

export async function requestInvestigation(request, { onProgress = () => {} } = {}) {
  let response
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  }
  try {
    response = await fetch(`${API_BASE_URL}/api/investigations/stream`, options)
    if ([404, 405].includes(response.status)) {
      try { onProgress({ stage: 'legacy_request', message: 'Executando a investigação no serviço de análise', tool: '' }) } catch { /* UI callbacks do not cancel analysis. */ }
      response = await fetch(`${API_BASE_URL}/api/investigations`, options)
    }
  } catch {
    throw new ApiError('Não foi possível comunicar com o serviço de análise.', 0)
  }
  if (!response.ok) {
    throw investigationError(response.status)
  }
  const contentType = response.headers?.get?.('content-type')?.toLowerCase() ?? ''
  if (contentType.startsWith('text/event-stream') && response.body?.getReader) {
    return readInvestigationStream(response, onProgress)
  }
  // Compatibility for test doubles and deployments that have not enabled streaming yet.
  return validateInvestigationPayload(await response.json().catch(() => null))
}

export async function requestReport(investigationId, { signal } = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/report`, { signal })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError('Não foi possível baixar o relatório. Confira a conexão com o serviço.', 0)
  }
  if (!response.ok) throw new ApiError(response.status === 404
    ? 'O relatório não está mais disponível nesta sessão. Execute uma nova investigação.'
    : 'Não foi possível baixar o relatório. Tente novamente.', response.status)
  if (!response.headers.get('content-type')?.toLowerCase().startsWith('text/html')) {
    throw new ApiError('O serviço retornou um arquivo de relatório inválido.', 502)
  }
  try { return await response.blob() } catch {
    throw new ApiError('O download do relatório foi interrompido. Tente novamente.', 0)
  }
}

function validateChatEnvelope(payload) {
  const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)
  const kinds = ['data_catalog', 'capability_catalog', 'descriptive', 'investigation_report', 'unsupported']
  if (!object(payload) || !nonEmptyText(payload.turn_id) || !object(payload.intent)
    || !object(payload.response) || !kinds.includes(payload.response.kind)
    || payload.intent.response_kind !== payload.response.kind) {
    throw new ApiError('O serviço retornou uma resposta analítica inválida.', 502)
  }
  const response = payload.response
  if (response.kind === 'investigation_report') {
    const report = response.report
    if (!object(report) || !object(report.executive_answer) || !nonEmptyText(report.question)
      || !nonEmptyText(report.executive_answer.headline) || !nonEmptyText(report.executive_answer.answer)
      || !Array.isArray(report.insights) || !Array.isArray(report.unanswered_parts)
      || !Array.isArray(report.limitations) || !object(report.technical_appendix)
      || !Array.isArray(response.evidence) || !object(response.chart_data)) {
      throw new ApiError('O relatório analítico retornado é inválido.', 502)
    }
  } else if (!nonEmptyText(response.answer)) {
    throw new ApiError('A resposta analítica retornada está vazia.', 502)
  }
  return payload
}

function chatError(status, payload = null) {
  const detail = payload?.detail ?? payload
  if (status === 404 && (detail === 'Not Found' || detail?.detail === 'Not Found')) {
    return new ApiError(
      'O backend em execução não possui o chat analítico atual. Reinicie o backend e tente novamente.',
      status,
      payload,
    )
  }
  const defaults = {
    401: 'As chaves configuradas foram recusadas pelo Gemini.',
    403: 'As chaves configuradas não têm permissão para o modelo.',
    404: 'O pacote ou o contexto da conversa não está mais disponível.',
    422: 'A pergunta não pôde ser executada neste escopo.',
    429: 'As cotas das chaves configuradas foram atingidas.',
    502: 'O relatório não passou pela validação das evidências.',
    503: 'O Gemini está indisponível. O pacote foi preservado para uma nova tentativa.',
    504: 'A análise ultrapassou o limite de 90 segundos. O pacote foi preservado.',
  }
  return new ApiError(nonEmptyText(detail?.message) ? detail.message : (defaults[status] ?? 'Não foi possível concluir a solicitação.'), status, payload)
}

async function readChatStream(response, onProgress) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result = null
  let failure = null
  function consume(block) {
    const lines = block.split(/\r?\n/)
    const event = lines.find((line) => line.startsWith('event:'))?.slice(6).trim() ?? 'message'
    const data = lines.filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart()).join('\n')
    if (!data) return
    let payload
    try { payload = JSON.parse(data) } catch { throw new ApiError('O serviço enviou um evento inválido.', 502) }
    if (event === 'progress') {
      if (nonEmptyText(payload?.stage) && nonEmptyText(payload?.message)) onProgress(payload)
    } else if (event === 'result') result = payload
    else if (event === 'error') failure = chatError(Number(payload?.status) || 503, payload)
  }
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    let separator = buffer.search(/\r?\n\r?\n/)
    while (separator >= 0) {
      const match = buffer.slice(separator).match(/^\r?\n\r?\n/)[0]
      consume(buffer.slice(0, separator))
      buffer = buffer.slice(separator + match.length)
      separator = buffer.search(/\r?\n\r?\n/)
    }
    if (done) break
  }
  if (buffer.trim()) consume(buffer)
  if (failure) throw failure
  return validateChatEnvelope(result)
}

const CHAT_DEADLINE_MS = 95_000

export async function requestChat(request, { onProgress = () => {}, signal } = {}) {
  const controller = new AbortController()
  let deadlineReached = false
  const forwardAbort = () => controller.abort(signal?.reason)
  if (signal?.aborted) forwardAbort()
  else signal?.addEventListener('abort', forwardAbort, { once: true })
  const deadline = setTimeout(() => {
    deadlineReached = true
    controller.abort()
  }, CHAT_DEADLINE_MS)
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/respond/stream`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request), signal: controller.signal,
    })
    if (!response.ok) throw chatError(response.status, await response.json().catch(() => null))
    const contentType = response.headers?.get?.('content-type')?.toLowerCase() ?? ''
    if (contentType.startsWith('text/event-stream') && response.body?.getReader) {
      return await readChatStream(response, onProgress)
    }
    return validateChatEnvelope(await response.json().catch(() => null))
  } catch (error) {
    if (error?.name === 'AbortError' && deadlineReached) {
      throw new ApiError('A análise não terminou dentro de 95 segundos. O processamento foi encerrado e o pacote continua disponível.', 504)
    }
    if (error?.name === 'AbortError' || error instanceof ApiError) throw error
    throw new ApiError('Não foi possível comunicar com o serviço de análise.', 0)
  } finally {
    clearTimeout(deadline)
    signal?.removeEventListener('abort', forwardAbort)
  }
}

export async function requestChatReport(turnId, { signal } = {}) {
  let response
  try { response = await fetch(`${API_BASE_URL}/api/chat/reports/${encodeURIComponent(turnId)}`, { signal }) } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('Não foi possível baixar o relatório.', 0)
  }
  if (!response.ok) {
    const payload = typeof response.json === 'function' ? await response.json().catch(() => null) : null
    throw chatError(response.status, payload)
  }
  if (!response.headers.get('content-type')?.toLowerCase().startsWith('text/html')) {
    throw new ApiError('O serviço retornou um arquivo de relatório inválido.', 502)
  }
  try { return await response.blob() } catch {
    throw new ApiError('O download do relatório foi interrompido.', 0)
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
        ? 'A sessão do pacote expirou. Importe os arquivos novamente.'
        : typeof payload?.detail === 'string' ? payload.detail : 'Não foi possível validar esta comparação.',
      response.status, payload,
    )
  }
  return payload
}
