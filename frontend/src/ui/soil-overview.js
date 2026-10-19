import { control, element, formatValue, table } from './dom.js'

const GROUPS = { group_1: 'Conjunto 1', group_2: 'Conjunto 2' }
const unit = (metric) => metric.unit ?? 'unidade não documentada'
const percent = (value) => value == null ? 'Indisponível' : `${formatValue(value)}%`

function metricsCard(items) {
  const grid = element('div', 'metric-grid metric-grid--three')
  for (const [label, value, detail] of items) {
    const card = element('article', 'metric-card metric-card--compact')
    card.append(element('span', 'metric-card__label', label), element('strong', 'metric-card__value', value),
      element('small', 'metric-card__detail', detail))
    grid.append(card)
  }
  return grid
}

function evidenceCard(evidence, title) {
  const card = element('article', 'dashboard-card soil-evidence')
  card.dataset.evidenceId = evidence.evidence_id
  card.append(element('h3', '', title), element('p', 'chart-source',
    `${evidence.evidence_id} · Fonte: ${evidence.source_files.join(', ')}`))
  for (const text of [...evidence.warnings, ...evidence.limitations]) {
    card.append(element('p', 'chart-hint', text))
  }
  return card
}

function details(label, ...contents) {
  const section = element('details', 'soil-details')
  section.append(element('summary', '', label), ...contents)
  return section
}

function summaryCard(evidence) {
  const group = GROUPS[evidence.measurement_group]
  const card = evidenceCard(evidence, `Resumo descritivo · ${group}`)
  card.append(metricsCard([
    ['Amostras', formatValue(evidence.sample_count), 'Escopo geral do dataset'],
    ['Completude do recorte', percent(evidence.completeness_percent), `${formatValue(evidence.valid_values)} de ${formatValue(evidence.expected_values)} valores nas métricas retornadas`],
    ['Textura válida', formatValue(evidence.texture.valid_n), `${formatValue(evidence.texture.excluded_n)} amostras excluídas da composição`],
  ]))
  if (!evidence.metrics.length) {
    card.append(element('p', 'status-message', 'Nenhuma métrica descritiva disponível neste recorte.'))
    return card
  }
  const metric = control(`Métrica descritiva · ${group} · ${evidence.evidence_id}`, 'overview-soil-metric',
    evidence.metrics.map((item) => [item.name, item.name]))
  const selected = element('div', 'soil-metric-summary')
  function render() {
    const item = evidence.metrics.find((item) => item.name === metric.select.value)
    selected.replaceChildren(element('p', 'chart-unit', `${item.name} · ${unit(item)} · ${formatValue(item.valid_n)} valores válidos · ${formatValue(item.missing_n)} ausentes`),
      metricsCard([['Mínimo', formatValue(item.min), unit(item)], ['Mediana', formatValue(item.median), unit(item)],
        ['Máximo', formatValue(item.max), unit(item)]]))
  }
  metric.select.addEventListener('change', render)
  card.append(metric.label, selected, details(`Ver estatísticas detalhadas · ${group}`,
    table(`Estatísticas descritivas · ${group} · ${evidence.evidence_id}`,
      ['Métrica', 'Unidade', 'Válidas', 'Ausentes', 'Média', 'Mín.', 'Q1', 'Mediana', 'Q3', 'Máx.'],
      evidence.metrics.map((item) => [item.name, unit(item), formatValue(item.valid_n), formatValue(item.missing_n),
        ...['mean', 'min', 'q1', 'median', 'q3', 'max'].map((key) => formatValue(item[key]))])),
    element('p', 'chart-hint', evidence.method)))
  render()
  return card
}

function groupsCard(evidence) {
  const card = evidenceCard(evidence, 'Conjunto 1 × Conjunto 2')
  card.append(element('p', '', 'Comparação por amostra. Delta = Conjunto 2 − Conjunto 1; os conjuntos não representam talhões ou profundidades.'))
  if (!evidence.metrics.length) {
    card.append(element('p', 'status-message', 'Nenhuma métrica pareada disponível neste recorte.'))
    return card
  }
  const metric = control(`Métrica pareada · ${evidence.evidence_id}`, 'overview-soil-paired-metric',
    evidence.metrics.map((item) => [item.name, item.name]))
  const selected = element('div', 'soil-metric-summary')
  function render() {
    const item = evidence.metrics.find((item) => item.name === metric.select.value)
    selected.replaceChildren(metricsCard([
      ['Pares válidos', formatValue(item.valid_n), item.name],
      ['Delta mediano · 2 − 1', formatValue(item.median_delta), unit(item)],
      ['Amostras no dataset', formatValue(evidence.sample_count), 'Sem associação aos talhões'],
    ]), details(`Ver valores por amostra · ${item.name}`,
      table(`Pares · ${item.name} · ${unit(item)} · ${evidence.evidence_id}`, ['Amostra', 'Conjunto 1', 'Conjunto 2', 'Delta 2 − 1'],
        item.pairs.map((pair) => [pair.sample_id, formatValue(pair.group_1), formatValue(pair.group_2), formatValue(pair.delta)])),
      element('p', 'chart-hint', item.valid_n ? evidence.method : 'Não há pares válidos para esta métrica.')))
  }
  metric.select.addEventListener('change', render)
  card.append(metric.label, selected)
  render()
  return card
}

export function createSoilOverview(evidence) {
  const section = element('section', 'soil-overview')
  section.setAttribute('aria-labelledby', 'soil-overview-title')
  const title = element('h2', '', 'Visão de solo')
  title.id = 'soil-overview-title'
  const scope = element('aside', 'soil-summary')
  scope.append(element('strong', '', 'Contexto geral do dataset'),
    element('span', '', 'As amostras não pertencem aos talhões selecionados. Não há vínculo documentado com talhão, coordenada, data ou profundidade.'),
    element('span', '', 'Conjunto 1 e Conjunto 2 são grupos de medição; o significado do sufixo _2 não está documentado. Não há classificação de suficiência agronômica.'))
  section.append(title, scope)
  // Keep each tool call separate: filtered calls can contain different metrics
  // and coverage denominators, so they must not be aggregated in the browser.
  const soil = evidence.filter((item) => item?.scope === 'dataset')
  for (const [key, label] of Object.entries(GROUPS)) {
    const summaries = soil.filter((item) => item.measurement_group === key)
    if (summaries.length) summaries.forEach((item) => section.append(summaryCard(item)))
    else section.append(element('p', 'status-message', `${label}: resumo descritivo não disponível nesta investigação.`))
  }
  const groups = soil.filter((item) => item.comparison === 'group_2_minus_group_1')
  if (groups.length) groups.forEach((item) => section.append(groupsCard(item)))
  else section.append(element('p', 'status-message', 'Conjunto 1 × Conjunto 2: comparação pareada não disponível nesta investigação.'))
  return section
}
