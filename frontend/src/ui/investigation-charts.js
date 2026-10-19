import { chartColors, createChartController, distributionConfig, ndviConfig, pairedSoilConfig, textureConfig } from '../charts/analytics-charts.js'
import { control, element, formatDate, formatValue, table } from './dom.js'

const FAMILIES = { textura: 'Textura', acidez_fertilidade: 'Acidez e fertilidade', bases: 'Bases', micronutrientes: 'Micronutrientes' }
const groupName = (source) => source.measurement_group === 'group_1' ? 'Conjunto 1' : 'Conjunto 2'
const unit = (value) => value ?? 'unidade não documentada'

function graphic(title, detail, source, config, valuesTable, controllers) {
  const card = element('article', 'dashboard-card analytical-card')
  card.dataset.evidenceId = source.evidence_id
  const host = element('div', 'analytical-chart')
  const files = source.source_files.join(', ')
  card.append(element('h3', '', title), element('p', 'chart-unit', detail), host,
    element('p', 'chart-source', `${source.evidence_id} · Fonte: ${files}`), valuesTable)
  if (config) config.options.plugins.tooltip.callbacks.footer = () => [detail, `Fonte: ${files}`]
  const controller = createChartController(host)
  controllers.push({ controller, config, title })
  return card
}

// Create charts only after their cards have been attached to the visible panel.
function mount(controllers) {
  controllers.forEach(({ controller, config, title }) => controller.update(config, `${title}. Valores disponíveis na tabela abaixo.`))
}
function destroy(controllers) { controllers.forEach(({ controller }) => controller.destroy()); controllers.length = 0 }

export function createInvestigationNdviPanel(chartData, fields = []) {
  const panel = element('section', 'analytical-panel')
  panel.append(element('h2', '', 'Gráfico NDVI'))
  const source = chartData.ndvi
  const controllers = []
  if (!source) {
    panel.append(element('p', 'empty-chart', 'NDVI indisponível: a análise não foi retornada nesta investigação.'))
  } else {
    const fieldLabel = (id) => fields.find((field) => field.field_id === id)?.label ?? id
    const labels = { target: `Alvo · ${fieldLabel(source.target_field_id)}`, reference: `Referência · ${fieldLabel(source.reference_field_id)}` }
    panel.append(graphic('Trajetória NDVI pareada', `${formatValue(source.paired_dates)} datas pareadas · gap médio ${formatValue(source.mean_gap)} · ${unit(source.unit)}`,
      source, ndviConfig(source, labels, chartColors()),
      table('Série NDVI · valores recebidos', ['Data', labels.target, labels.reference, 'Gap alvo − referência'],
        source.series.map((point) => [formatDate(point.date), formatValue(point.target_ndvi), formatValue(point.reference_ndvi), formatValue(point.gap)])), controllers))
    for (const warning of source.warnings ?? []) panel.append(element('p', 'chart-hint', warning))
  }
  panel.mount = () => mount(controllers)
  panel.dispose = () => destroy(controllers)
  return panel
}

function soilCollection(sources, paired) {
  const panel = element('section', 'analytical-panel')
  const prefix = paired ? 'paired' : 'summary'
  panel.append(element('h3', '', paired ? 'Conjunto 1 × Conjunto 2' : 'Distribuição e textura'))
  if (!sources.length) {
    panel.append(element('p', 'empty-chart', paired ? 'Comparação de conjuntos não disponível nesta investigação.' : 'Resumos de solo não disponíveis nesta investigação.'))
    return panel
  }
  const call = control('Evidência de solo', `chart-${prefix}-evidence`, sources.map((source) => [source.evidence_id,
    `${paired ? 'Conjuntos 1 × 2' : groupName(source)} · ${source.evidence_id}`]))
  const family = control('Família de métricas', `chart-${prefix}-family`, [['all', 'Todas as famílias'], ...Object.entries(FAMILIES)])
  const metric = control('Métrica', `chart-${prefix}-metric`, [])
  const filters = element('div', 'form-grid analytical-filters')
  filters.append(call.label, family.label, metric.label)
  const quality = element('p', 'soil-summary')
  const notices = element('div', 'chart-hint')
  const charts = element('div', 'analytical-panel')
  panel.append(filters, quality, notices, charts)
  let controllers = []
  let mounted = false
  const selectedSource = () => sources.find((source) => source.evidence_id === call.select.value)
  function render() {
    destroy(controllers)
    const source = selectedSource()
    const selected = source.metrics.find((item) => item.name === metric.select.value)
    notices.replaceChildren(...[...source.warnings, ...source.limitations].map((text) => element('p', '', text)))
    quality.textContent = paired ? `${formatValue(source.sample_count)} amostras no dataset · delta = Conjunto 2 − Conjunto 1`
      : `${groupName(source)} · ${formatValue(source.sample_count)} amostras · completude do recorte: ${source.completeness_percent == null ? 'Indisponível' : `${formatValue(source.completeness_percent)}%`} · ${formatValue(source.valid_values)} de ${formatValue(source.expected_values)} valores`
    charts.replaceChildren()
    const colors = chartColors()
    const metricSource = { ...source, source_files: selected?.source_files ?? source.source_files }
    if (paired) {
      charts.append(graphic(`Conjunto 1 × Conjunto 2 · ${selected?.name ?? 'sem métrica'}`,
        `${formatValue(selected?.valid_n)} pares válidos · delta mediano ${formatValue(selected?.median_delta)} · ${unit(selected?.unit)}`,
        metricSource, pairedSoilConfig(selected, colors),
        table(`Pares · ${selected?.name ?? 'indisponível'} · ${unit(selected?.unit)}`, ['Amostra', 'Conjunto 1', 'Conjunto 2', 'Delta 2 − 1'],
          (selected?.pairs ?? []).map((pair) => [pair.sample_id, formatValue(pair.group_1), formatValue(pair.group_2), formatValue(pair.delta)])), controllers))
    } else {
      charts.append(graphic(`Distribuição · ${selected?.name ?? 'sem métrica'}`,
        `${groupName(source)} · ${formatValue(selected?.valid_n)} amostras válidas · ${unit(selected?.unit)}`, metricSource,
        distributionConfig(selected, colors), table(`Distribuição · ${selected?.name ?? 'indisponível'} · ${unit(selected?.unit)}`,
          ['Métrica', 'Válidas', 'Mín.', 'Q1', 'Mediana', 'Q3', 'Máx.'], selected ? [[selected.name, formatValue(selected.valid_n),
            ...['min', 'q1', 'median', 'q3', 'max'].map((key) => formatValue(selected[key]))]] : []), controllers),
      graphic('Composição de textura', `${groupName(source)} · ${formatValue(source.texture.valid_n)} amostras válidas · ${formatValue(source.texture.excluded_n)} excluídas · % normalizado`,
        { ...source, source_files: source.texture.source_files }, textureConfig(source.texture, colors),
        table('Textura · composição normalizada (%) e soma original', ['Amostra', 'Areia %', 'Silte %', 'Argila %', 'Soma original'],
          source.texture.samples.map((sample) => [sample.sample_id, formatValue(sample.sand), formatValue(sample.silt), formatValue(sample.clay), formatValue(sample.original_total)])), controllers),
      element('p', 'chart-hint', source.texture.method))
    }
    if (mounted) mount(controllers)
  }
  function fillMetrics() {
    const previous = metric.select.value
    const available = selectedSource().metrics.filter((item) => family.select.value === 'all' || item.family === family.select.value)
    metric.select.replaceChildren(...available.map((item) => Object.assign(element('option', '', item.name), { value: item.name })))
    if (available.some((item) => item.name === previous)) metric.select.value = previous
    metric.select.disabled = !available.length
    render()
  }
  call.select.addEventListener('change', fillMetrics)
  family.select.addEventListener('change', fillMetrics)
  metric.select.addEventListener('change', render)
  panel.mount = () => { mounted = true; mount(controllers) }
  panel.dispose = () => { mounted = false; destroy(controllers) }
  fillMetrics()
  return panel
}

export function createInvestigationSoilPanel(chartData) {
  const panel = element('section', 'analytical-panel')
  panel.append(element('h2', '', 'Solo'), element('p', 'soil-summary',
    'Escopo geral do dataset, sem vínculo com os talhões. O sufixo _2 não tem significado documentado. Mapa, tendência temporal e perfil de profundidade indisponíveis: faltam coordenadas, datas e profundidades. Não há classificação agronômica.'))
  const summaries = soilCollection(chartData.soil_summaries ?? [], false)
  const pairs = soilCollection(chartData.soil_groups ?? [], true)
  panel.append(summaries, pairs)
  panel.mount = () => { summaries.mount?.(); pairs.mount?.() }
  panel.dispose = () => { summaries.dispose?.(); pairs.dispose?.() }
  return panel
}
