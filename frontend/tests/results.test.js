// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import fixture from '../src/mocks/analytics-preview.json'
import { AppState, resetStateForTests, runInvestigation, setDataset, state, transitionTo } from '../src/state.js'
import { createInvestigationResult } from '../src/ui/results.js'
import { formatValue } from '../src/ui/dom.js'

const originResult = () => ({
  generated_by: 'gemini', warnings: [],
  report: { overview: { headline: 'Contexto do solo & vigor', summary: 'Descrição observacional.\nSem inferência causal.', evidence_strength: 'weak' }, findings: [], recommendations: [] },
  evidence: structuredClone([fixture.soil_summary, fixture.soil_summary_2, fixture.soil_groups]),
})
beforeEach(() => resetStateForTests())
afterEach(() => { document.body.replaceChildren(); resetStateForTests() })

async function render(result = originResult()) {
  transitionTo(AppState.UPLOADING)
  transitionTo(AppState.VALIDATING)
  setDataset({ dataset_id: 'dataset-test' })
  transitionTo(AppState.READY)
  await runInvestigation(() => Promise.resolve(result))
  const navigate = vi.fn()
  const view = createInvestigationResult(navigate)
  document.body.append(view)
  return { view, navigate }
}

it.each([['weak', 'Fraca'], ['moderate', 'Moderada'], ['strong', 'Forte']])('renders the %s overview and soil immediately after its summary', async (strength, label) => {
  const result = originResult()
  result.report.overview.evidence_strength = strength
  const { view } = await render(result)
  expect(view.querySelector('h1').textContent).toBe(result.report.overview.headline)
  expect(view.querySelector('.report-summary').textContent).toBe(result.report.overview.summary)
  expect(view.textContent).toContain(`Força da evidência: ${label}`)
  expect(view.querySelector('.report-summary').parentElement.nextElementSibling.className).toBe('soil-overview')
  expect(view.textContent).toContain('Resultado do Gemini')
  expect(view.querySelector('.soil-overview').textContent).toContain('As amostras não pertencem aos talhões selecionados')
  expect(view.querySelector('.soil-overview').textContent).toContain('o significado do sufixo _2 não está documentado')
})

it('renders hostile narrative, source, warning and sample text as literal text', async () => {
  const hostile = '<img src=x onerror="alert(1)"><script>alert(2)</script> & "texto"'
  const result = originResult()
  result.generated_by = 'deterministic_fallback'
  result.report.overview.headline = hostile
  result.report.overview.summary = hostile
  result.warnings = [{ code: 'deterministic_fallback', message: hostile }]
  result.evidence[0].source_files = [hostile]
  result.evidence[0].warnings = [hostile]
  result.evidence[0].limitations = [hostile]
  result.evidence[0].metrics[0].unit = hostile
  result.evidence[2].metrics[0].pairs[0].sample_id = hostile
  const { view } = await render(result)
  expect(view.querySelector('h1').textContent).toBe(hostile)
  expect(view.querySelector('.report-summary').textContent).toBe(hostile)
  expect(view.querySelector('.report-notice').textContent).toBe(hostile)
  expect(view.querySelectorAll('img, script, [onerror]')).toHaveLength(0)
  expect(view.textContent).toContain('Relatório local · fallback')
  expect(view.textContent).not.toContain('Resultado do Gemini')
  expect([...view.querySelectorAll('th')].some((cell) => cell.textContent === hostile)).toBe(true)
})

it('identifies fallback even without an optional warning message', async () => {
  const result = originResult()
  result.generated_by = 'deterministic_fallback'
  const { view } = await render(result)
  expect(view.querySelector('.report-notice').textContent).toContain('templates locais')
})

it('preserves backend statistics, quality denominators and signed deltas without recalculating', async () => {
  const result = originResult()
  const summary = result.evidence[0]
  summary.completeness_percent = 12.3456
  summary.valid_values = 7
  summary.expected_values = 31
  Object.assign(summary.metrics[0], { min: -3, median: 0, max: 18, mean: 4.4321, q1: -1, q3: 11 })
  const paired = result.evidence[2].metrics[0]
  paired.median_delta = -9.8765 // Deliberately independent of pair values: display, never recompute.
  const snapshot = JSON.stringify(result)
  const { view, navigate } = await render(result)
  const card = view.querySelector('.soil-evidence')
  expect(card.textContent).toContain('12,3456%')
  expect(card.textContent).toContain('7 de 31 valores nas métricas retornadas')
  expect(card.querySelector('tbody tr').textContent).toContain('4,4321')
  const selection = card.querySelector('select')
  selection.value = summary.metrics[1].name
  selection.dispatchEvent(new Event('change'))
  expect(card.querySelector('.soil-metric-summary').textContent).toContain(formatValue(summary.metrics[1].median))
  const pairedCard = [...view.querySelectorAll('.soil-evidence')].at(-1)
  expect(pairedCard.textContent).toContain('-9,8765')
  const details = pairedCard.querySelector('details')
  details.open = true
  expect(details.querySelector('tbody tr').textContent).toContain(formatValue(paired.pairs[0].delta))
  expect(JSON.stringify(result)).toBe(snapshot)
  view.querySelector('[data-action="new-comparison"]').click()
  expect(navigate).toHaveBeenCalledWith('comparison')
  expect(state.status).toBe(AppState.READY)
  expect(state.dataset.dataset_id).toBe('dataset-test')
})

it('keeps partial and filtered calls separate instead of borrowing missing group data', async () => {
  const result = originResult()
  const one = result.evidence[0]
  const filtered = structuredClone(one)
  filtered.evidence_id = 'EV-SOIL-SUMMARY-009'
  filtered.metrics = [filtered.metrics[1]]
  filtered.completeness_percent = 25
  result.evidence = [one, filtered]
  const { view } = await render(result)
  expect(view.querySelectorAll('.soil-evidence')).toHaveLength(2)
  expect(view.textContent).toContain('Conjunto 2: resumo descritivo não disponível')
  expect(view.textContent).toContain('comparação pareada não disponível')
  expect(view.querySelectorAll('select')[1].options).toHaveLength(1)
  expect(view.querySelectorAll('.soil-evidence')[1].textContent).toContain('25%')
})

it('shows unavailable statistics distinctly from zero and handles zero valid pairs', async () => {
  const result = originResult()
  const summary = result.evidence[0]
  summary.completeness_percent = null
  Object.assign(summary.metrics[0], { min: null, median: null, max: null, valid_n: 0 })
  Object.assign(result.evidence[2].metrics[0], { valid_n: 0, median_delta: null, pairs: [] })
  const { view } = await render(result)
  const values = [...view.querySelector('.soil-metric-summary').querySelectorAll('.metric-card__value')]
  expect(values.map((node) => node.textContent)).toEqual(['Indisponível', 'Indisponível', 'Indisponível'])
  expect(view.textContent).not.toContain('Indisponível%')
  expect(view.textContent).toContain('Não há pares válidos')
  expect(view.textContent).toContain('unidade não documentada')
})

it('handles absent soil evidence without illustrative data', async () => {
  const result = originResult()
  result.evidence = []
  const { view } = await render(result)
  expect(view.querySelectorAll('.soil-evidence, table, canvas')).toHaveLength(0)
  expect(view.textContent).toContain('Conjunto 1: resumo descritivo não disponível')
  expect(view.textContent).not.toContain('Prévia')
})

it('handles empty metric lists and still displays quality cards', async () => {
  const result = originResult()
  result.evidence.forEach((item) => { item.metrics = [] })
  const { view } = await render(result)
  expect(view.querySelectorAll('select')).toHaveLength(0)
  expect(view.textContent).toContain('Nenhuma métrica descritiva disponível')
  expect(view.textContent).toContain('Nenhuma métrica pareada disponível')
  expect(view.textContent).toContain('Completude do recorte')
})

it('keeps the empty result route usable', () => {
  const navigate = vi.fn()
  const view = createInvestigationResult(navigate)
  expect(view.querySelector('h1').textContent).toBe('Nenhuma investigação concluída')
  view.querySelector('button').click()
  expect(navigate).toHaveBeenCalledWith('comparison')
})

it.each(['gemini', 'deterministic_fallback'])('preserves ordered cards and resolves every reference for %s', async (origin) => {
  const result = originResult()
  result.generated_by = origin
  const [first, second] = result.evidence
  result.report.findings = [
    { title: 'Z primeiro', explanation: 'Primeira explicação.', evidence_ids: [second.evidence_id, first.evidence_id] },
    { title: 'A segundo', explanation: 'Segunda explicação.', evidence_ids: [first.evidence_id] },
  ]
  result.report.recommendations = [
    { action: 'Z ação inicial', reason: 'Primeira justificativa.', evidence_ids: [first.evidence_id] },
    { action: 'A ação seguinte', reason: 'Segunda justificativa.', evidence_ids: [second.evidence_id] },
  ]
  const snapshot = JSON.stringify(result)
  const { view } = await render(result)
  expect([...view.querySelectorAll('[data-section="findings"] h3')].map((node) => node.textContent)).toEqual(['Z primeiro', 'A segundo'])
  expect([...view.querySelectorAll('[data-section="recommendations"] h3')].map((node) => node.textContent)).toEqual(['Z ação inicial', 'A ação seguinte'])
  expect([...view.querySelectorAll('[data-section="recommendations"] .report-card__text')].map((node) => node.textContent)).toEqual(['Primeira justificativa.', 'Segunda justificativa.'])
  expect(view.querySelector('.soil-overview').nextElementSibling.dataset.section).toBe('findings')
  for (const card of view.querySelectorAll('.report-card')) {
    const refs = [...card.querySelectorAll('.evidence-reference')]
    expect(refs.length).toBeGreaterThan(0)
    for (const ref of refs) {
      const source = result.evidence.find((item) => item.evidence_id === ref.dataset.evidenceId)
      expect(source).toBeDefined()
      ref.open = true
      expect(ref.textContent).toContain(source.method)
      expect(ref.textContent).toContain(source.source_files.join(', '))
      expect(ref.textContent).toContain('sem vínculo documentado com os talhões')
    }
  }
  expect([...view.querySelector('.report-card').querySelectorAll('summary')].map((node) => node.textContent)).toEqual([second.evidence_id, first.evidence_id])
  expect(JSON.stringify(result)).toBe(snapshot)
})

it('renders malicious card titles, explanations, actions, reasons and reference metadata literally', async () => {
  const result = originResult()
  const hostile = '<svg onload="alert(1)"></svg> & texto'
  const evidence = result.evidence[0]
  evidence.method = hostile
  evidence.source_files = [hostile]
  result.report.findings = [{ title: hostile, explanation: hostile, evidence_ids: [evidence.evidence_id] }]
  result.report.recommendations = [{ action: hostile, reason: hostile, evidence_ids: [evidence.evidence_id] }]
  const { view } = await render(result)
  for (const card of view.querySelectorAll('.report-card')) {
    expect(card.querySelector('h3').textContent).toBe(hostile)
    expect(card.querySelector('.report-card__text').textContent).toBe(hostile)
    expect(card.querySelector('.evidence-reference p').textContent).toBe(hostile)
    expect(card.querySelector('.chart-source').textContent).toBe(`Fonte: ${hostile}`)
  }
  expect(view.querySelectorAll('svg, script, [onload]')).toHaveLength(0)
})

it('shows explicit empty findings and recommendations without fabricated cards', async () => {
  const { view } = await render()
  expect(view.querySelectorAll('.report-card')).toHaveLength(0)
  expect(view.querySelector('[data-section="findings"]').textContent).toContain('Nenhum achado foi incluído')
  expect(view.querySelector('[data-section="recommendations"]').textContent).toContain('Nenhuma recomendação foi incluída')
})

it('switches accessible tabs by mouse and keyboard while preserving the overview and result', async () => {
  const result = originResult()
  const { view, navigate } = await render(result)
  const tabs = [...view.querySelectorAll('[role="tab"]')]
  expect(tabs.map((node) => node.textContent)).toEqual(['Visão geral', 'Solo', 'Evidências', 'Gráfico NDVI', 'Métodos', 'Limitações'])
  const overview = view.querySelector('#investigation-panel-overview')
  const evidence = view.querySelector('#investigation-panel-evidence')
  for (const tab of tabs) expect(view.querySelector(`#${tab.getAttribute('aria-controls')}`)).not.toBeNull()
  expect(overview.hidden).toBe(false)
  expect(evidence.hidden).toBe(true)
  const metric = overview.querySelector('select')
  metric.value = result.evidence[0].metrics[1].name
  metric.dispatchEvent(new Event('change'))
  tabs[2].click()
  expect(overview.hidden).toBe(true)
  expect(evidence.hidden).toBe(false)
  expect(evidence.getAttribute('aria-labelledby')).toBe(tabs[2].id)
  expect(tabs[2].getAttribute('aria-selected')).toBe('true')
  expect(evidence.querySelectorAll('.evidence-card')).toHaveLength(result.evidence.length)
  tabs[2].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))
  expect(document.activeElement).toBe(tabs[3])
  tabs[3].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))
  expect(document.activeElement).toBe(tabs[4])
  tabs[4].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))
  expect(document.activeElement).toBe(tabs[5])
  tabs[5].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))
  expect(document.activeElement).toBe(tabs[0])
  expect(overview.hidden).toBe(false)
  expect(metric.value).toBe(result.evidence[0].metrics[1].name)
  tabs[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }))
  expect(document.activeElement).toBe(tabs[5])
  tabs[5].dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }))
  expect(document.activeElement).toBe(tabs[0])
  tabs[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }))
  expect(document.activeElement).toBe(tabs[5])
  expect(evidence.querySelectorAll('.evidence-card')).toHaveLength(result.evidence.length)
  expect(state.investigation).toBe(result)
  view.querySelector('[data-action="new-comparison"]').click()
  expect(navigate).toHaveBeenCalledWith('comparison')
  expect(state.status).toBe(AppState.READY)
})
