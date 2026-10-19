// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import fixture from '../src/mocks/analytics-preview.json'

const charts = vi.hoisted(() => [])
vi.mock('chart.js/auto', () => ({ default: class {
  constructor(canvas, config) { this.config = config; this.destroy = vi.fn(); charts.push(this) }
} }))

let store
const dataset = { ...fixture.dataset, dataset_id: 'dataset-test' }
const pair = fixture.comparisons['103144:103145'].validation
const envelope = (origin) => ({
  investigation_id: 'result', status: 'completed', generated_by: origin,
  report: {
    overview: { headline: 'Relatório real', summary: 'Síntese observacional.', evidence_strength: 'weak' },
    findings: [{ title: 'Contraste de vigor', explanation: 'Comparação observacional.', evidence_ids: [fixture.comparisons['103144:103145'].ndvi.evidence_id] }],
    recommendations: [{ action: 'Conferir observações de campo', reason: 'O contraste não comprova causalidade.', evidence_ids: [fixture.comparisons['103144:103145'].ndvi.evidence_id] }],
    limitations: [{ title: 'Limite observacional', explanation: 'O contraste não comprova causalidade.', rule_id: 'observational_only' }],
  }, evidence: [fixture.comparisons['103144:103145'].ndvi], chart_data: { ndvi: fixture.comparisons['103144:103145'].ndvi, soil_summaries: [], soil_groups: [] },
  trace: { model: 'gemini-test', created_at: '2026-10-17T12:00:00Z', calls: [{
    sequence: 1, tool: 'compare_ndvi', tool_version: '1.0.0', status: 'success', started_at: '2026-10-17T12:00:01Z', duration_ms: 12.5,
    arguments: { target_field_id: '103144', reference_field_id: '103145', period: 'full_season' },
    source_files: ['ndvi_metadata.csv'], result_evidence_ids: [fixture.comparisons['103144:103145'].ndvi.evidence_id],
  }] },
  warnings: origin === 'gemini' ? [] : [{ code: 'deterministic_fallback', message: 'Relatório produzido por templates locais.' }],
})

beforeEach(async () => {
  charts.length = 0
  vi.resetModules()
  document.body.replaceChildren(Object.assign(document.createElement('div'), { id: 'app' }))
  store = await import('../src/state.js')
  store.transitionTo(store.AppState.UPLOADING)
  store.transitionTo(store.AppState.VALIDATING)
  store.setDataset(dataset)
  store.transitionTo(store.AppState.READY)
})

afterEach(() => {
  document.body.replaceChildren()
  vi.unstubAllGlobals()
})

const nav = (name) => document.querySelector(`.app-nav [data-page="${name}"]`)
const readyButton = async () => {
  const button = document.querySelector('.comparison-form [type="submit"]')
  await vi.waitFor(() => expect(button.disabled).toBe(false))
  return button
}

it.each(['gemini', 'deterministic_fallback'])('completes the real UI route with a fake %s API and reuses its dataset', async (origin) => {
  let finish
  const fetch = vi.fn(async (url) => {
    if (url === '/api/diagnostics/tools') return { ok: true, json: async () => pair }
    if (url === '/api/investigations') return new Promise((resolve) => { finish = resolve })
    throw new Error(`Unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetch)
  await import('../src/main.js')

  const skip = document.querySelector('.skip-link')
  skip.click()
  expect(document.activeElement.id).toBe('main-content')

  // An imported package must never enter the illustrative results screen.
  nav('investigation').click()
  expect(document.querySelector('main').textContent).toContain('Nenhuma investigação concluída')
  expect(document.querySelector('main').textContent).not.toContain('dados fictícios')
  nav('comparison').click()
  expect(document.activeElement).toBe(document.querySelector('h1'))
  const execute = await readyButton()
  expect(execute.textContent).toBe('Executar investigação')
  const oldDataNav = nav('data')
  execute.click()
  execute.click()
  await vi.waitFor(() => expect(finish).toBeTypeOf('function'))
  expect([...document.querySelectorAll('header button')].every((button) => button.disabled)).toBe(true)
  oldDataNav.click() // The navigation guard also rejects events from stale nodes.
  expect(document.querySelector('main > section').dataset.page).toBe('comparison')
  expect(document.querySelector('progress').hasAttribute('value')).toBe(false)
  expect(document.activeElement).toBe(document.querySelector('.investigation-progress'))
  expect(document.querySelector('.investigation-progress').closest('[aria-busy="true"]')).toBeNull()
  expect(fetch.mock.calls.filter(([url]) => url === '/api/investigations')).toHaveLength(1)

  const result = envelope(origin)
  finish({ ok: true, json: async () => result })
  await vi.waitFor(() => expect(document.querySelector('h1').textContent).toBe('Relatório real'))
  expect(document.querySelector('.report-summary').textContent).toBe('Síntese observacional.')
  expect(document.querySelector('.soil-overview').textContent).toContain('Visão de solo')
  expect(document.querySelector('[data-section="findings"] h3').textContent).toBe('Contraste de vigor')
  expect(document.querySelector('[data-section="recommendations"] .report-card__text').textContent).toBe('O contraste não comprova causalidade.')
  expect([...document.querySelectorAll('.evidence-reference')].every((node) => result.evidence.some((item) => item.evidence_id === node.dataset.evidenceId))).toBe(true)
  expect(store.state.investigation).toEqual(result)
  expect(document.querySelector('main').textContent).toContain(origin === 'gemini' ? 'Resultado do Gemini' : 'Relatório local · fallback')
  expect(document.querySelector('main').textContent).not.toContain('Prévia')
  expect(document.title).toBe('Investigação · FarmLab Investigator')
  expect(document.activeElement).toBe(document.querySelector('h1'))
  document.querySelector('#investigation-tab-evidence').click()
  expect(document.querySelector('#investigation-panel-evidence').hidden).toBe(false)
  expect(document.querySelector('.evidence-card').dataset.evidenceId).toBe(result.evidence[0].evidence_id)
  expect(document.querySelector('.evidence-card').textContent).toContain('NDVI médio')
  document.querySelector('#investigation-tab-chart').click()
  expect(charts).toHaveLength(1)
  expect(charts[0].config.data.datasets[0].data).toEqual(result.chart_data.ndvi.series.map((point) => point.target_ndvi))
  document.querySelector('#investigation-tab-methods').click()
  expect(charts[0].destroy).toHaveBeenCalledOnce()
  expect(document.querySelector('.method-card').textContent).toContain('12,5 ms')
  expect(document.querySelector('#investigation-panel-methods').textContent).toContain('gemini-test')
  document.querySelector('#investigation-tab-limitations').click()
  expect(document.querySelector('.limitation-card').textContent).toContain('observational_only')
  expect([...document.querySelectorAll('header button')].every((button) => !button.disabled)).toBe(true)
  document.querySelector('[data-action="new-comparison"]').click()
  expect(charts[0].destroy).toHaveBeenCalledOnce()
  await readyButton()
  expect(store.state.status).toBe(store.AppState.READY)
  expect(store.state.dataset).toBe(dataset)
  expect(store.state.investigation).toBeNull()
  expect(fetch.mock.calls.some(([url]) => url === '/api/datasets')).toBe(false)
})

it('shows an API failure and resets the upload screen without reloading the app', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url) => url === '/api/diagnostics/tools'
    ? { ok: true, json: async () => pair }
    : { ok: false, status: 404, json: async () => ({ detail: { code: 'dataset_not_found' } }) }))
  await import('../src/main.js')
  nav('comparison').click()
  const execute = await readyButton()
  execute.click()
  await vi.waitFor(() => expect(document.querySelector('[role="alert"]')?.textContent).toContain('Importe os arquivos novamente'))
  expect(store.state.status).toBe(store.AppState.ERROR)
  const restart = [...document.querySelectorAll('main button')].find((button) => button.textContent === 'Reiniciar pacote')
  restart.click()
  expect(store.state.status).toBe(store.AppState.EMPTY)
  expect(document.querySelector('h1').textContent).toBe('Pacote da safra')
  expect(document.querySelector('#upload-status').textContent).toBe('Nenhum arquivo selecionado.')
  expect(document.querySelector('.validation-result').hidden).toBe(true)
  expect(document.querySelector('.continue-button').disabled).toBe(true)
})

it.each([
  ['missing_key', 'Chave do provedor não configurada.'],
  ['timeout', 'Prazo da geração automática excedido.'],
  ['rate_limit', 'Limite de requisições do provedor atingido.'],
  ['invalid_report', 'O relatório gerado não passou pela validação de formato.'],
  ['invalid_response', 'O provedor não retornou uma resposta utilizável.'],
])('keeps the UI usable after %s fallback and allows a new investigation', async (scenario, reason) => {
  const fallback = envelope('deterministic_fallback')
  fallback.warnings[0].message = `${reason} Relatório produzido por templates locais.`
  let investigations = 0
  const fetch = vi.fn(async (url) => {
    if (url === '/api/health') return { ok: true, json: async () => ({ status: 'ok',
      gemini_configured: scenario !== 'missing_key', model: 'gemini-test', version: '1.0.0' }) }
    if (url === '/api/diagnostics/tools') return { ok: true, json: async () => pair }
    if (url === '/api/investigations') {
      investigations++
      return { ok: true, json: async () => investigations === 1 ? fallback : envelope('gemini') }
    }
    throw new Error(`Unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetch)
  await import('../src/main.js')
  nav('comparison').click()
  const execute = await readyButton()
  execute.click()
  await vi.waitFor(() => expect(store.state.status).toBe(store.AppState.COMPLETED))
  expect(document.querySelector('.report-notice').textContent).toBe(fallback.warnings[0].message)
  expect(document.querySelector('main').textContent).toContain('Relatório local · fallback')
  expect(document.querySelector('.investigation-progress')).toBeNull()
  expect(document.querySelector('main [role="alert"]')).toBeNull()
  expect([...document.querySelectorAll('header button')].every((button) => !button.disabled)).toBe(true)
  expect(document.querySelector('[data-action="download-report"]').disabled).toBe(false)
  expect(store.state.dataset).toBe(dataset)

  document.querySelector('[data-action="new-comparison"]').click()
  const retry = await readyButton()
  expect(store.state.status).toBe(store.AppState.READY)
  retry.click()
  await vi.waitFor(() => expect(store.state.status).toBe(store.AppState.COMPLETED))
  expect(document.querySelector('main').textContent).toContain('Resultado do Gemini')
  expect(document.querySelector('.report-notice')).toBeNull()
  expect(store.state.dataset).toBe(dataset)
  expect(investigations).toBe(2)
  expect(fetch.mock.calls.some(([url]) => url === '/api/datasets' || url === '/api/gemini/test')).toBe(false)
})
