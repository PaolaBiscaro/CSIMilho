// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
const instances = vi.hoisted(() => [])
vi.mock('chart.js/auto', () => ({ default: class {
  constructor(canvas, config) { this.canvas = canvas; this.config = config; this.destroy = vi.fn(); instances.push(this) }
} }))
import fixture from '../src/mocks/analytics-preview.json'
import { createInvestigationNdviPanel, createInvestigationSoilPanel } from '../src/ui/investigation-charts.js'
import { createInvestigationResult } from '../src/ui/results.js'
import { state, resetStateForTests } from '../src/state.js'
import { distributionConfig } from '../src/charts/analytics-charts.js'

const data = () => structuredClone({ ndvi: fixture.comparisons['103144:103145'].ndvi,
  soil_summaries: [fixture.soil_summary, fixture.soil_summary_2], soil_groups: [fixture.soil_groups] })
afterEach(() => { instances.length = 0; document.body.replaceChildren(); resetStateForTests() })
const mount = (panel) => { document.body.append(panel); panel.mount(); return panel }
const select = (panel, name, value) => {
  const control = panel.querySelector(`[name="${name}"]`)
  control.value = value
  control.dispatchEvent(new Event('change'))
}

it('renders NDVI from chart_data with exact point order, local dates, tooltip provenance and accessible values', () => {
  const source = data()
  source.ndvi.series[0].gap = -0.1234
  const snapshot = JSON.stringify(source)
  const panel = mount(createInvestigationNdviPanel(source, fixture.dataset.fields))
  const config = instances[0].config
  expect(config.data.labels).toEqual(source.ndvi.series.map((point) => point.date))
  expect(config.data.datasets[1].data).toEqual(source.ndvi.series.map((point) => point.reference_ndvi))
  expect(config.options.plugins.tooltip.callbacks.title([{ dataIndex: 0 }])).toBe('01/12/2024')
  expect(config.options.plugins.tooltip.callbacks.afterBody([{ dataIndex: 0 }])).toContain('-0,1234')
  expect(config.options.plugins.tooltip.callbacks.footer().join(' ')).toContain(source.ndvi.source_files.join(', '))
  expect(panel.querySelector('tbody tr').textContent).toContain('01/12/2024')
  expect(panel.querySelector('tbody tr').textContent).toContain('-0,1234')
  expect(panel.querySelector('canvas').getAttribute('aria-label')).toContain('tabela')
  expect(JSON.stringify(source)).toBe(snapshot)
  panel.dispose()
  expect(instances[0].destroy).toHaveBeenCalledOnce()
})

it('preserves soil statistics, pairs and texture with units, counts, sources and equivalent tables', () => {
  const source = data()
  const snapshot = JSON.stringify(source)
  const panel = mount(createInvestigationSoilPanel(source))
  const summary = source.soil_summaries[0]
  const metric = summary.metrics[0]
  const paired = source.soil_groups[0].metrics[0]
  expect(instances).toHaveLength(3)
  expect(instances[0].config.data.datasets[0].data.map((point) => point.x)).toEqual([metric.min, metric.q1, metric.median, metric.q3, metric.max])
  expect(instances[1].config.data.datasets[0].data).toEqual(summary.texture.samples.map((sample) => sample.sand))
  expect(instances[2].config.data.datasets[1].data).toEqual(paired.pairs.map((pair) => pair.group_2))
  expect(panel.querySelectorAll('table')).toHaveLength(3)
  expect(panel.querySelectorAll('.chart-source')).toHaveLength(3)
  for (const chart of instances) {
    const footer = chart.config.options.plugins.tooltip.callbacks.footer().join(' ')
    expect(footer).toContain('soil_analysis.csv')
    expect(footer).toMatch(/amostras válidas|pares válidos/)
  }
  expect(panel.textContent).toContain('unidade não documentada')
  expect(panel.textContent).toContain('Mapa, tendência temporal e perfil de profundidade indisponíveis')
  expect(JSON.stringify(source)).toBe(snapshot)
  panel.dispose()
  expect(instances.every((chart) => chart.destroy.mock.calls.length === 1)).toBe(true)
})

it('keeps filtered calls selectable and does not fill missing summary data from another call', () => {
  const source = data()
  const filtered = structuredClone(source.soil_summaries[0])
  filtered.evidence_id = 'EV-SOIL-SUMMARY-099'
  filtered.metrics = [{ ...filtered.metrics[0], min: 1, q1: 2, median: 3, q3: 4, max: 5 }]
  filtered.completeness_percent = null
  source.soil_summaries = [source.soil_summaries[1], filtered]
  source.soil_groups = []
  const panel = mount(createInvestigationSoilPanel(source))
  const firstCharts = [...instances]
  select(panel, 'chart-summary-evidence', filtered.evidence_id)
  expect(firstCharts.every((chart) => chart.destroy.mock.calls.length === 1)).toBe(true)
  const latest = instances.filter((chart) => chart.destroy.mock.calls.length === 0)
  expect(latest[0].config.data.datasets[0].data.map((point) => point.x)).toEqual([1, 2, 3, 4, 5])
  expect(panel.querySelector('[name="chart-summary-metric"]').options).toHaveLength(1)
  expect(panel.textContent).toContain('completude do recorte: Indisponível')
  expect(panel.textContent).not.toContain('Indisponível%')
  expect(panel.textContent).toContain('Comparação de conjuntos não disponível')
  select(panel, 'chart-summary-family', 'micronutrientes')
  expect(panel.querySelector('[name="chart-summary-metric"]').disabled).toBe(true)
  expect(panel.querySelector('.empty-chart')).not.toBeNull()
  expect(panel.textContent).toContain('Indisponível amostras válidas')
  panel.dispose()
})

it('supports group comparison without any summary and changes metric independently', () => {
  const source = data()
  source.soil_summaries = []
  const panel = mount(createInvestigationSoilPanel(source))
  expect(instances).toHaveLength(1)
  const next = source.soil_groups[0].metrics[1]
  select(panel, 'chart-paired-metric', next.name)
  expect(instances[0].destroy).toHaveBeenCalledOnce()
  expect(instances[1].config.data.datasets[0].data).toEqual(next.pairs.map((pair) => pair.group_1))
  expect(panel.textContent).toContain('Resumos de solo não disponíveis')
  panel.dispose()
})

it('shows missing and empty analyses without fabricated plots or null-to-zero quartiles', () => {
  const ndvi = mount(createInvestigationNdviPanel({}))
  const soil = mount(createInvestigationSoilPanel({}))
  expect(instances).toHaveLength(0)
  expect(ndvi.textContent).toContain('NDVI indisponível')
  expect(soil.textContent).toContain('Resumos de solo não disponíveis')
  const source = data()
  source.ndvi.series = []
  const empty = mount(createInvestigationNdviPanel(source))
  expect(empty.querySelector('canvas')).toBeNull()
  expect(empty.querySelectorAll('tbody tr')).toHaveLength(0)
  expect(distributionConfig({ valid_n: 1, min: null, q1: 0, median: 0, q3: 0, max: 0 }, [])).toBeNull()
  ndvi.dispose(); soil.dispose(); empty.dispose()
})

it('disposes charts on tab switches, repeated selection, overview shortcut and navigation', () => {
  const chartData = data()
  state.investigation = { generated_by: 'gemini', warnings: [], chart_data: chartData,
    evidence: [chartData.ndvi, ...chartData.soil_summaries, ...chartData.soil_groups],
    report: { overview: { headline: 'Resultado', summary: 'Resumo.', evidence_strength: 'weak' }, findings: [], recommendations: [] } }
  const view = createInvestigationResult(() => {})
  document.body.append(view)
  const soilTab = view.querySelector('[data-tab="soil"]')
  const chartTab = view.querySelector('[data-tab="chart"]')
  soilTab.click()
  expect(instances).toHaveLength(3)
  soilTab.click()
  expect(instances).toHaveLength(3)
  chartTab.click()
  expect(instances.slice(0, 3).every((chart) => chart.destroy.mock.calls.length === 1)).toBe(true)
  expect(view.querySelectorAll('canvas')).toHaveLength(1)
  view.querySelector('[data-tab="overview"]').click()
  expect(instances[3].destroy).toHaveBeenCalledOnce()
  expect(view.querySelectorAll('canvas')).toHaveLength(0)
  const shortcut = [...view.querySelectorAll('button')].find((node) => node.textContent === 'Explorar gráficos de solo')
  shortcut.click()
  expect(document.activeElement).toBe(soilTab)
  expect(view.querySelectorAll('canvas')).toHaveLength(3)
  view.dispose()
  view.dispose()
  expect(instances.every((chart) => chart.destroy.mock.calls.length === 1)).toBe(true)
})
