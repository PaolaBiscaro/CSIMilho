// @vitest-environment happy-dom
import { expect, it } from 'vitest'
import fixture from '../src/mocks/analytics-preview.json'
import { createEvidencePanel } from '../src/ui/evidence.js'
import { formatValue } from '../src/ui/dom.js'

const comparison = fixture.comparisons['103144:103145']
const values = (row) => [...row.children].map((cell) => cell.textContent)

it('preserves null and undefined as unavailable, while displaying real zero values', () => {
  const evidence = { ...comparison.ndvi, target_value: null, reference_value: 0, difference: undefined, observation_count: null, paired_dates: 0 }
  const panel = createEvidencePanel([evidence])
  expect(values(panel.querySelector('tbody tr'))).toEqual(['NDVI médio', 'Indisponível', '0', 'Indisponível', 'ndvi'])
  expect([...panel.querySelectorAll('dd')].map((node) => node.textContent)).toEqual(['Indisponível', '0'])
  expect(panel.textContent).not.toContain('NaN')
})

it('uses the supplied scalar differences, ordered fields, row counts and sources without recalculating', () => {
  const evidence = { ...comparison.population, target_value: 10, reference_value: 20, difference: -123.4567,
    target_rows: { valid: 0, discarded: 2 }, reference_rows: { valid: 7, discarded: 0 } }
  const snapshot = JSON.stringify(evidence)
  const panel = createEvidencePanel([evidence], fixture.dataset.fields)
  expect(values(panel.querySelector('tbody tr'))).toEqual(['População por hectare', '10', '20', '-123,4567', 'plants/ha'])
  expect(panel.textContent).toContain(`(${evidence.target_field_id})`)
  expect(panel.textContent).toContain(`(${evidence.reference_field_id})`)
  expect(panel.querySelector('.chart-source').textContent).toBe(`Fonte: ${evidence.source_files.join(', ')}`)
  expect([...panel.querySelectorAll('dd')].map((node) => node.textContent)).toEqual([formatValue(evidence.observation_count), '0', '2', '7', '0'])
  expect(JSON.stringify(evidence)).toBe(snapshot)
})

it('distinguishes percentage points from percent in application compliance', () => {
  const panel = createEvidencePanel([comparison.application])
  expect(panel.textContent).toContain('Diferença em pontos percentuais')
  expect(values(panel.querySelector('tbody tr'))).toEqual(['Conformidade de aplicação', formatValue(comparison.application.target_value),
    formatValue(comparison.application.reference_value), formatValue(comparison.application.difference), '%'])
})

it('keeps unavailable initial condition and comparison criteria explicit', () => {
  const initial = { ...comparison.initial, target_value: null, reference_value: null, difference: null, unit: null, paired_dates: 0 }
  const validation = { ...comparison.validation, criteria: [
    { label: 'A', satisfied: null, detail: 'Não observado' },
    { label: 'B', satisfied: false, detail: 'Incompatível' },
    { label: 'C', satisfied: true, detail: 'Compatível' },
  ] }
  const panel = createEvidencePanel([initial, validation])
  expect(values(panel.querySelector('tbody tr')).slice(1)).toEqual(['Indisponível', 'Indisponível', 'Indisponível', 'unidade não documentada'])
  expect([...panel.querySelectorAll('table')].at(-1).textContent).toContain('Não atendido')
  expect([...panel.querySelectorAll('table')].at(-1).textContent).toContain('Indisponível')
})

it('shows soil statistics and paired values without assigning them to target or reference', () => {
  const summary = structuredClone(fixture.soil_summary_2)
  const groups = structuredClone(fixture.soil_groups)
  summary.metrics = [{ ...fixture.soil_summary.metrics[0], mean: 0, median: null, unit: null }]
  groups.metrics = [{ ...groups.metrics[0], median_delta: -0.1234 }]
  const snapshot = JSON.stringify([summary, groups])
  const panel = createEvidencePanel([summary, groups])
  const cards = panel.querySelectorAll('.evidence-card')
  expect(cards[0].textContent).toContain('Conjunto 2')
  const row = values(cards[0].querySelector('tbody tr'))
  expect(row[1]).toBe('unidade não documentada')
  expect(row[4]).toBe('0')
  expect(row[7]).toBe('Indisponível')
  expect([...cards[0].querySelectorAll('thead th')].map((node) => node.textContent)).not.toContain('Alvo')
  expect(cards[1].querySelector('summary').textContent).toContain('delta mediano -0,1234')
  expect(values(cards[1].querySelector('tbody tr'))).toEqual([groups.metrics[0].pairs[0].sample_id,
    ...['group_1', 'group_2', 'delta'].map((key) => formatValue(groups.metrics[0].pairs[0][key]))])
  expect(panel.textContent).toContain('sem vínculo documentado com talhão')
  expect(JSON.stringify([summary, groups])).toBe(snapshot)
})

it('renders hostile evidence labels, metadata and field names literally', () => {
  const hostile = '<img src=x onerror="alert(1)"> & texto'
  const evidence = { ...comparison.ndvi, evidence_id: hostile, metric: hostile, unit: hostile, source_files: [hostile], warnings: [hostile] }
  const panel = createEvidencePanel([evidence], [{ field_id: evidence.target_field_id, label: hostile }])
  expect(panel.querySelector('h3').textContent).toBe(hostile)
  expect(panel.textContent).toContain(`Fonte: ${hostile}`)
  expect(panel.textContent).toContain(`Alvo: ${hostile}`)
  expect(panel.querySelector('tbody th').textContent).toBe(hostile)
  expect(panel.querySelectorAll('img, script, [onerror]')).toHaveLength(0)
})

it('handles absent evidence, empty soil metrics and zero valid pairs without invented values', () => {
  const empty = createEvidencePanel([])
  expect(empty.textContent).toContain('Nenhuma evidência disponível')
  expect(empty.querySelectorAll('table, .evidence-card')).toHaveLength(0)
  const panel = createEvidencePanel([
    { ...fixture.soil_summary, metrics: [] },
    { ...fixture.soil_groups, metrics: [{ ...fixture.soil_groups.metrics[0], valid_n: 0, median_delta: null, pairs: [] }] },
  ])
  expect(panel.textContent).toContain('Nenhuma métrica descritiva disponível')
  expect(panel.textContent).toContain('0 pares válidos · delta mediano Indisponível')
  expect(panel.textContent).toContain('Não há pares válidos')
  expect(panel.querySelectorAll('tbody tr')).toHaveLength(0)
})
