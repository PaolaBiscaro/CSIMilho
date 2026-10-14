import { chartColors, createChartController, distributionConfig, ndviConfig, pairedSoilConfig, textureConfig } from '../charts/analytics-charts.js'
import { control, element, formatValue, table } from './dom.js'

function chartCard(title, detail, sources) {
  const card = element('article', 'dashboard-card analytical-card')
  const host = element('div', 'analytical-chart')
  card.append(element('h3', '', title), element('p', 'chart-unit', detail), host,
    element('small', 'chart-source', `Fonte: ${sources.join(', ')}`))
  return { card, host, controller: createChartController(host) }
}

export function createNdviPanel(evidence, labels) {
  const panel = element('section', 'analytical-panel')
  const info = evidence ? `${evidence.paired_dates} datas pareadas · gap ${formatValue(evidence.mean_gap)} · ${evidence.unit}` : 'NDVI indisponível'
  const chart = chartCard('Trajetória NDVI pareada', info, evidence?.source_files ?? [])
  chart.controller.update(ndviConfig(evidence, labels, chartColors()), 'NDVI do alvo e da referência nas mesmas datas. Valores na tabela abaixo.')
  panel.append(chart.card, table('Valores exatos da série NDVI', ['Data', labels.target, labels.reference, 'Gap alvo − referência'],
    (evidence?.series ?? []).map((point) => [point.date, formatValue(point.target_ndvi), formatValue(point.reference_ndvi), formatValue(point.gap)])))
  panel.dispose = () => chart.controller.destroy()
  return panel
}

const FAMILY_NAMES = { textura: 'Textura', acidez_fertilidade: 'Acidez e fertilidade', bases: 'Bases', micronutrientes: 'Micronutrientes' }

export function createSoilPanel(summary, summary2, groups) {
  const panel = element('section', 'analytical-panel')
  const quality = element('div', 'metric-grid metric-grid--three')
  for (const [label, value, detail] of [
    ['Amostras', summary.sample_count, 'Escopo geral do dataset'],
    ['Completude · Conjunto 1', `${formatValue(summary.completeness_percent)}%`, `${summary.valid_values} de ${summary.expected_values} valores`],
    ['Textura válida · Conjunto 1', summary.texture.valid_n, `${summary.texture.excluded_n} amostras excluídas`],
  ]) {
    const card = element('article', 'metric-card')
    card.append(element('span', 'metric-card__label', label), element('strong', 'metric-card__value', String(value)), element('small', 'metric-card__detail', detail))
    quality.append(card)
  }
  const limitations = element('aside', 'preview-notice')
  limitations.append(element('strong', '', 'Solo · escopo do dataset'), element('span', '', summary.limitations.join(' ')))
  const filters = element('div', 'form-grid analytical-filters')
  const family = control('Família de métricas', 'soil-family', [['all', 'Todas as famílias'], ...Object.entries(FAMILY_NAMES)])
  const metric = control('Métrica', 'soil-metric', [])
  const group = control('Conjunto da distribuição', 'soil-group', [['group_1', 'Conjunto 1'], ['group_2', 'Conjunto 2']])
  filters.append(family.label, metric.label, group.label)
  const charts = element('div', 'analytical-grid')
  const details = element('div', 'analytical-tables')
  const warning = element('p', 'chart-hint')
  warning.setAttribute('role', 'status')
  let controllers = []
  const selectedSummary = () => group.select.value === 'group_1' ? summary : summary2
  function fillMetrics() {
    const previous = metric.select.value
    const available = selectedSummary().metrics.filter((item) => family.select.value === 'all' || item.family === family.select.value)
    metric.select.replaceChildren(...available.map((item) => {
      const option = element('option', '', item.name)
      option.value = item.name
      return option
    }))
    if (available.some((item) => item.name === previous)) metric.select.value = previous
    else if (available.some((item) => item.name === 'PHCACL2')) metric.select.value = 'PHCACL2'
    metric.select.disabled = !available.length
    render()
  }
  function render() {
    controllers.forEach((controller) => controller.destroy())
    controllers = []
    charts.replaceChildren()
    details.replaceChildren()
    const source = selectedSummary()
    const selected = source.metrics.find((item) => item.name === metric.select.value)
    const paired = groups.metrics.find((item) => item.name === metric.select.value)
    const unit = selected?.unit ?? 'unidade não documentada'
    const pairedUnit = paired?.unit ?? 'unidade não documentada'
    warning.textContent = [...source.warnings, ...groups.warnings].join(' ')
    const distribution = chartCard(`Distribuição · ${selected?.name ?? 'sem métrica'}`, `${group.select.selectedOptions[0].textContent} · ${selected?.valid_n ?? 0} válidas · ${unit}`, selected?.source_files ?? source.source_files)
    const pairedCard = chartCard(`Conjunto 1 × Conjunto 2 · ${selected?.name ?? 'sem métrica'}`, `${paired?.valid_n ?? 0} pares · delta mediano ${formatValue(paired?.median_delta)} · ${pairedUnit}`, paired?.source_files ?? groups.source_files)
    const texture = chartCard('Composição de textura', `${source.texture.valid_n} válidas · ${source.texture.excluded_n} excluídas · % normalizado`, source.texture.source_files)
    charts.append(distribution.card, pairedCard.card, texture.card)
    const colors = chartColors()
    distribution.controller.update(distributionConfig(selected, colors), 'Mínimo, Q1, mediana, Q3 e máximo. Resumo na tabela abaixo.')
    pairedCard.controller.update(pairedSoilConfig(paired, colors), 'Conjuntos 1 e 2 pareados por amostra. Valores e deltas na tabela abaixo.')
    texture.controller.update(textureConfig(source.texture, colors), 'Areia, silte e argila normalizados para 100% por amostra válida. Valores na tabela abaixo.')
    controllers.push(distribution.controller, pairedCard.controller, texture.controller)
    details.append(
      table(`Distribuição · ${selected?.name ?? 'indisponível'} · ${unit}`, ['Conjunto', 'Válidas', 'Mín.', 'Q1', 'Mediana', 'Q3', 'Máx.'],
        selected ? [[group.select.selectedOptions[0].textContent, selected.valid_n, ...['min', 'q1', 'median', 'q3', 'max'].map((key) => formatValue(selected[key]))]] : []),
      table(`Pares · ${selected?.name ?? 'indisponível'} · ${pairedUnit}`, ['Amostra', 'Conjunto 1', 'Conjunto 2', 'Delta 2 − 1'],
        (paired?.pairs ?? []).map((pair) => [pair.sample_id, formatValue(pair.group_1), formatValue(pair.group_2), formatValue(pair.delta)])),
      table('Textura · composição normalizada (%) e soma original', ['Amostra', 'Areia %', 'Silte %', 'Argila %', 'Soma original'],
        source.texture.samples.map((sample) => [sample.sample_id, formatValue(sample.sand), formatValue(sample.silt), formatValue(sample.clay), formatValue(sample.original_total)])),
      element('p', 'chart-hint', source.texture.method),
    )
  }
  family.select.addEventListener('change', fillMetrics)
  group.select.addEventListener('change', fillMetrics)
  metric.select.addEventListener('change', render)
  panel.append(quality, limitations, filters, warning, charts, details)
  panel.dispose = () => controllers.forEach((controller) => controller.destroy())
  fillMetrics()
  return panel
}
