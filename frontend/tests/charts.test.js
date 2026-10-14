// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest'

const instances = vi.hoisted(() => [])
vi.mock('chart.js/auto', () => ({ default: class {
  constructor(canvas, config) { this.canvas = canvas; this.config = config; this.destroy = vi.fn(); instances.push(this) }
} }))

import fixture from '../src/mocks/analytics-preview.json'
import { createChartController, distributionConfig, ndviConfig, pairedSoilConfig, textureConfig } from '../src/charts/analytics-charts.js'
import { createSoilPanel } from '../src/ui/analytical-panels.js'
import { createInvestigationPreview } from '../src/ui/investigation-preview.js'

const colors = ['primary', 'soft', 'secondary', 'dark']
const ndvi = fixture.comparisons['103144:103145'].ndvi
const ph = fixture.soil_summary.metrics.find((item) => item.name === 'PHCACL2')
const paired = fixture.soil_groups.metrics.find((item) => item.name === 'PHCACL2')
afterEach(() => { instances.length = 0; document.body.replaceChildren() })

describe('chart contracts preserve backend values', () => {
  it('copies paired NDVI dates and values without interpolating', () => {
    const config = ndviConfig(ndvi, { target: 'Alvo', reference: 'Referência' }, colors)
    expect(config.data.labels).toEqual(ndvi.series.map((point) => point.date))
    expect(config.data.datasets[0].data).toEqual(ndvi.series.map((point) => point.target_ndvi))
    expect(config.data.datasets[1].data).toEqual(ndvi.series.map((point) => point.reference_ndvi))
    expect(config.options.spanGaps).toBe(false)
    expect(ndviConfig(null, {}, colors)).toBeNull()
  })
  it('uses exactly the five-number summary for a single metric', () => {
    const config = distributionConfig(ph, colors)
    expect(config.data.datasets).toHaveLength(1)
    expect(config.data.datasets[0].data.map((point) => point.x)).toEqual([ph.min, ph.q1, ph.median, ph.q3, ph.max])
    expect(config.options.scales.x.title.text).toBe('unidade não documentada')
    expect(distributionConfig({ valid_n: 0 }, colors)).toBeNull()
  })
  it('copies the two soil groups and backend deltas, preserving sample order', () => {
    const config = pairedSoilConfig(paired, colors)
    expect(config.data.labels).toEqual(paired.pairs.map((point) => `Amostra ${point.sample_id}`))
    expect(config.data.datasets[0].data).toEqual(paired.pairs.map((point) => point.group_1))
    expect(config.data.datasets[1].data).toEqual(paired.pairs.map((point) => point.group_2))
    expect(config.options.plugins.tooltip.callbacks.afterBody([{ dataIndex: 0 }])).toContain('Delta 2 − 1')
  })
  it('uses only backend-approved texture samples without recalculating percentages', () => {
    const texture = fixture.soil_summary.texture
    const config = textureConfig(texture, colors)
    expect(config.data.datasets[0].data).toEqual(texture.samples.map((sample) => sample.sand))
    expect(config.data.datasets[1].data).toEqual(texture.samples.map((sample) => sample.silt))
    expect(config.data.datasets[2].data).toEqual(texture.samples.map((sample) => sample.clay))
    expect(config.options.scales.y.max).toBe(100)
    expect(textureConfig({ samples: [] }, colors)).toBeNull()
  })
})

describe('chart lifecycle and accessible UI', () => {
  it('destroys the previous instance and has one canvas after replacement', () => {
    const host = document.createElement('div')
    const chart = createChartController(host)
    const config = ndviConfig(ndvi, { target: 'Alvo', reference: 'Referência' }, colors)
    chart.update(config, 'NDVI')
    const first = instances[0]
    chart.update(config, 'NDVI novo')
    expect(first.destroy).toHaveBeenCalledOnce()
    expect(host.querySelectorAll('canvas')).toHaveLength(1)
    chart.update(null, '')
    expect(instances[1].destroy).toHaveBeenCalledOnce()
    expect(host.querySelectorAll('canvas')).toHaveLength(0)
    expect(host.textContent).toContain('Não há observações suficientes')
  })
  it('filters soil by family/metric and preserves one instance per chart', () => {
    const panel = createSoilPanel(fixture.soil_summary, fixture.soil_summary_2, fixture.soil_groups)
    document.body.append(panel)
    expect(panel.querySelectorAll('canvas')).toHaveLength(3)
    expect(panel.querySelectorAll('table')).toHaveLength(3)
    expect(panel.textContent).toContain('unidade não documentada')
    const initial = [...instances]
    const family = panel.querySelector('[name="soil-family"]')
    family.value = 'micronutrientes'
    family.dispatchEvent(new Event('change'))
    expect(initial.every((chart) => chart.destroy.mock.calls.length === 1)).toBe(true)
    const metric = panel.querySelector('[name="soil-metric"]')
    expect([...metric.options].map((option) => option.value)).toEqual(['B', 'ZN', 'MN', 'CU', 'FE'])
    expect(panel.querySelectorAll('canvas').length).toBeLessThanOrEqual(3)
    const group = panel.querySelector('[name="soil-group"]')
    group.value = 'group_2'
    group.dispatchEvent(new Event('change'))
    expect(metric.disabled).toBe(true)
    expect(panel.querySelector('.empty-chart')).not.toBeNull()
    panel.dispose()
    expect(instances.every((chart) => chart.destroy.mock.calls.length === 1)).toBe(true)
  })
  it('cleans up chart instances on tab change and navigation', () => {
    const view = createInvestigationPreview(() => {})
    document.body.append(view)
    const initial = [...instances]
    view.querySelector('[data-tab="chart"]').click()
    expect(initial.every((chart) => chart.destroy.mock.calls.length === 1)).toBe(true)
    expect(view.querySelectorAll('canvas')).toHaveLength(1)
    expect(view.querySelector('table').textContent).toContain('2024-12-01')
    view.querySelector('[data-tab="soil"]').click()
    expect(view.querySelectorAll('canvas')).toHaveLength(3)
    view.dispose()
    expect(instances.every((chart) => chart.destroy.mock.calls.length === 1)).toBe(true)
    expect(view.textContent).toContain('dados demonstrativos locais')
    expect(view.textContent).not.toContain('Visão geral do Gemini')
  })
})

it('preserves six preview tabs and keyboard navigation while leaving the report unavailable', () => {
  const view = createInvestigationPreview(() => {})
  document.body.append(view)
  expect([...view.querySelectorAll('[role="tab"]')].map((tab) => tab.textContent)).toEqual(['Visão geral', 'Solo', 'Evidências', 'Gráfico NDVI', 'Métodos', 'Limitações'])
  const soil = view.querySelector('[data-tab="soil"]')
  soil.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }))
  expect(view.querySelector('[data-tab="overview"]').getAttribute('aria-selected')).toBe('true')
  expect(view.querySelector('[role="tabpanel"]').textContent).toContain('Resumo demonstrativo')
  expect([...view.querySelectorAll('button')].find((button) => button.textContent === 'Relatório indisponível na prévia').disabled).toBe(true)
  expect(view.querySelectorAll('canvas')).toHaveLength(0)
  view.dispose()
})
