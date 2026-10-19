import { element, formatDate, formatValue } from './dom.js'

const TOOLS = {
  validate_comparison: 'Validar comparabilidade', compare_ndvi: 'Comparar NDVI',
  check_initial_condition: 'Verificar condição inicial', compare_population: 'Comparar população',
  application_compliance: 'Verificar conformidade de aplicação', summarize_soil_analysis: 'Resumir análise de solo',
  compare_soil_measurement_groups: 'Comparar conjuntos de solo',
}
const FIELD_TOOLS = new Set(['validate_comparison', 'compare_ndvi', 'check_initial_condition', 'compare_population', 'application_compliance'])
const STATUS = { success: 'Concluída', error: 'Falha' }
const ERRORS = {
  analysis_unavailable: 'Dados insuficientes para executar a análise.',
  dataset_not_found: 'Pacote indisponível durante a execução.',
  invalid_tool_result: 'Resultado da ferramenta rejeitado pela validação.',
  tool_execution_failed: 'Não foi possível concluir a ferramenta.',
}
const text = (value) => typeof value === 'string' && value.trim() ? value : 'Indisponível'
const duration = (value) => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? `${formatValue(value)} ms` : 'Indisponível'
const strings = (value) => Array.isArray(value) ? value.filter((item) => typeof item === 'string') : []
const lookup = (map, key, fallback = 'Indisponível') => Object.hasOwn(map, key) ? map[key] : fallback

function timestamp(value) {
  if (typeof value !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/i.test(value)) return 'Indisponível'
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return 'Indisponível'
  return `${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'medium', timeZone: 'UTC' }).format(date)} UTC`
}

function descriptionList(items) {
  const list = element('dl', 'audit-metadata')
  for (const [label, value] of items) {
    const row = element('div')
    row.append(element('dt', '', label), element('dd', '', value))
    list.append(row)
  }
  return list
}

function period(value) {
  if (value === 'full_season') return 'Safra completa'
  if (value && typeof value.start === 'string' && typeof value.end === 'string'
    && /^\d{4}-\d{2}-\d{2}$/.test(value.start) && /^\d{4}-\d{2}-\d{2}$/.test(value.end)) {
    return `${formatDate(value.start)} a ${formatDate(value.end)}`
  }
  return 'Indisponível'
}

function publicArguments(call) {
  const args = call.arguments ?? {}
  // Explicit per-tool projection: never enumerate or stringify the trace/arguments.
  if (FIELD_TOOLS.has(call.tool)) {
    const items = [['Talhão alvo', text(args.target_field_id)], ['Talhão de referência', text(args.reference_field_id)], ['Período', period(args.period)]]
    if (call.tool === 'application_compliance') items.push(['Operação', text(args.operation)])
    return items
  }
  if (call.tool === 'summarize_soil_analysis' || call.tool === 'compare_soil_measurement_groups') {
    const items = [['Escopo', 'Dataset, sem vínculo com talhão'],
      ['Métricas', args.metrics === null ? 'Todas as métricas disponíveis' : strings(args.metrics).join(', ') || 'Indisponível']]
    if (call.tool === 'summarize_soil_analysis') items.push(['Conjunto', lookup({ group_1: 'Conjunto 1', group_2: 'Conjunto 2' }, args.measurement_group)])
    return items
  }
  return []
}

export function createLimitationsPanel(limitations = []) {
  const panel = element('section', 'audit-panel')
  panel.append(element('h2', '', 'Limitações'))
  if (!limitations.length) panel.append(element('p', 'status-message', 'Limitações indisponíveis neste resultado. Isso não significa ausência de restrições.'))
  for (const item of limitations) {
    const card = element('article', 'dashboard-card limitation-card')
    card.append(element('h3', '', text(item.title)), element('p', 'report-card__text', text(item.explanation)),
      element('p', 'chart-source', `Regra associada: ${text(item.rule_id)}`))
    panel.append(card)
  }
  return panel
}

export function createMethodsPanel(result) {
  const panel = element('section', 'audit-panel')
  const trace = result.trace ?? {}
  const fallback = result.generated_by === 'deterministic_fallback'
  panel.append(element('h2', '', 'Métodos'), descriptionList([
    ['Origem do relatório', fallback ? 'Fallback determinístico · gerado localmente' : result.generated_by === 'gemini' ? 'Gemini' : 'Indisponível'],
    ['Modelo configurado', text(trace.model)], ['Início da investigação', timestamp(trace.created_at)],
  ]))
  if (fallback) panel.append(element('p', 'report-notice', 'O relatório foi produzido por templates locais. O modelo configurado não identifica o autor deste relatório.'))
  const calls = Array.isArray(trace.calls) ? trace.calls : []
  if (!calls.length) panel.append(element('p', 'status-message', 'Nenhuma execução de ferramenta registrada neste resultado.'))
  const evidenceById = new Map((result.evidence ?? []).map((item) => [item.evidence_id, item]))
  for (const call of calls) {
    const card = element('article', 'dashboard-card method-card')
    card.append(element('h3', '', `${Number.isInteger(call.sequence) && call.sequence > 0 ? call.sequence : '—'} · ${lookup(TOOLS, call.tool, 'Ferramenta não reconhecida')}`),
      descriptionList([['Ferramenta', Object.hasOwn(TOOLS, call.tool) ? call.tool : 'Indisponível'],
        ['Versão', text(call.tool_version)], ['Estado', lookup(STATUS, call.status)],
        ['Início da chamada', timestamp(call.started_at)], ['Duração da chamada', duration(call.duration_ms)],
        ...publicArguments(call)]))
    const sources = strings(call.source_files)
    card.append(element('p', 'chart-source', sources.length ? `Fontes: ${sources.join(', ')}` : 'Fontes: nenhuma registrada para esta chamada.'))
    const ids = strings(call.result_evidence_ids)
    if (ids.length) {
      const list = element('ul', 'detail-list')
      for (const id of ids) {
        const evidence = evidenceById.get(id)
        list.append(element('li', '', `${id} · ${evidence ? text(evidence.method) : 'Evidência não disponível neste resultado.'}`))
      }
      card.append(element('h4', '', 'Evidências produzidas'), list)
    } else card.append(element('p', 'status-message', 'Nenhuma evidência produzida por esta chamada.'))
    if (call.status === 'error') card.append(element('p', 'report-notice',
      lookup(ERRORS, call.error?.code, 'A ferramenta não concluiu a execução.')))
    panel.append(card)
  }
  if (trace.repair) {
    const repair = trace.repair
    const card = element('section', 'dashboard-card')
    card.append(element('h3', '', 'Reparo do relatório'), descriptionList([
      ['Estado', lookup(STATUS, repair.status)], ['Início', timestamp(repair.started_at)], ['Duração', duration(repair.duration_ms)],
    ]))
    panel.append(card)
  }
  return panel
}
