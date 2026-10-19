// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { ApiError } from '../src/api.js'
import { createPreflightPanel } from '../src/ui/preflight.js'
import { resetStateForTests, state } from '../src/state.js'

const health = { status: 'ok', gemini_configured: true, model: 'gemini-local-test', version: '1.0.0' }
const success = { success: true, model: health.model, latency_ms: 0, message: 'Conexão verificada.', error_code: null }
const flush = async () => { for (let n = 0; n < 8; n++) await Promise.resolve() }
const panels = []
const render = (readHealth = vi.fn().mockResolvedValue(health), probeGemini = vi.fn().mockResolvedValue(success)) => {
  const panel = createPreflightPanel({ readHealth, probeGemini })
  document.body.append(panel)
  panels.push(panel)
  const [refresh, test] = panel.querySelectorAll('button')
  panel.mount()
  return { panel, refresh, test, readHealth, probeGemini }
}
afterEach(() => { panels.splice(0).forEach(p => p.dispose()); document.body.replaceChildren(); resetStateForTests(); vi.unstubAllGlobals() })

it('checks health only on mount and preserves investigation state', async () => {
  const snapshot = JSON.stringify(state)
  const { panel, readHealth, probeGemini, test } = render()
  panel.mount()
  expect(test.disabled).toBe(true)
  await flush()
  expect(readHealth).toHaveBeenCalledTimes(1)
  expect(probeGemini).not.toHaveBeenCalled()
  expect(panel.textContent).toContain('Configurado · conexão não testada')
  expect(test.disabled).toBe(false)
  expect(JSON.stringify(state)).toBe(snapshot)
})

it('distinguishes absent key from a disconnected backend and can refresh after configuration', async () => {
  const read = vi.fn().mockResolvedValueOnce({ ...health, gemini_configured: false }).mockResolvedValueOnce(health)
  const { panel, refresh, test, probeGemini } = render(read)
  await flush()
  expect(panel.querySelector('[data-check="backend"]').textContent).toBe('Conectado')
  expect(panel.textContent).toContain('Não configurado')
  expect(test.disabled).toBe(true)
  test.click()
  expect(probeGemini).not.toHaveBeenCalled()
  refresh.click()
  await flush()
  expect(test.disabled).toBe(false)
  expect(panel.textContent).not.toContain('Conexão confirmada')
})

it('deduplicates the explicit probe, displays zero latency and focuses the outcome', async () => {
  let finish
  const probe = vi.fn().mockReturnValue(new Promise(resolve => { finish = resolve }))
  const { panel, refresh, test } = render(undefined, probe)
  await flush()
  const snapshot = JSON.stringify(state)
  test.click(); test.click(); refresh.click()
  expect(probe).toHaveBeenCalledTimes(1)
  expect(test.disabled && refresh.disabled).toBe(true)
  finish(success)
  await flush()
  expect(panel.textContent).toContain('Conexão confirmada')
  expect(panel.textContent).toContain('0 ms')
  expect(document.activeElement).toBe(panel.querySelector('[role="status"]'))
  expect(JSON.stringify(state)).toBe(snapshot)
})

it('shows provider failure and allows a deliberate retry without starting an investigation', async () => {
  const probe = vi.fn().mockResolvedValueOnce({ ...success, success: false, error_code: 'rate_limit', latency_ms: 24, message: 'Limite de uso atingido.' }).mockResolvedValueOnce(success)
  const { panel, test } = render(undefined, probe)
  await flush(); test.click(); await flush()
  expect(panel.querySelector('[role="alert"]').textContent).toContain('Limite de uso')
  expect(panel.textContent).toContain('24 ms')
  expect(test.disabled).toBe(false)
  test.click(); await flush()
  expect(panel.querySelector('[role="alert"]')).toBeNull()
  expect(probe).toHaveBeenCalledTimes(2)
})

it('handles backend failure and clears previous probe confirmation when status is refreshed', async () => {
  const read = vi.fn().mockResolvedValueOnce(health).mockRejectedValueOnce(new ApiError('Backend indisponível.', 0)).mockResolvedValueOnce(health)
  const { panel, refresh, test } = render(read)
  await flush(); test.click(); await flush(); refresh.click(); await flush()
  expect(panel.querySelector('[role="alert"]').textContent).toBe('Backend indisponível.')
  expect(test.disabled).toBe(true)
  expect(panel.textContent).not.toContain('Conexão confirmada')
  expect(panel.textContent).toContain('não medida')
  refresh.click(); await flush()
  expect(test.disabled).toBe(false)
  expect(panel.textContent).toContain('conexão não testada')
})

it('aborts on navigation, ignores late results, and rechecks when remounted', async () => {
  let finish
  const read = vi.fn().mockReturnValueOnce(new Promise(resolve => { finish = resolve })).mockResolvedValueOnce({ ...health, model: 'current-model' })
  const { panel } = render(read)
  const signal = read.mock.calls[0][0].signal
  panel.dispose()
  expect(signal.aborted).toBe(true)
  panel.mount(); await flush()
  finish({ ...health, model: 'STALE_MODEL' }); await flush()
  expect(panel.textContent).toContain('current-model')
  expect(panel.textContent).not.toContain('STALE_MODEL')
})

it('renders metadata as literal text and omits unknown fields', async () => {
  const attack = '<img src=x onerror="alert(1)">'
  const { panel } = render(vi.fn().mockResolvedValue({ ...health, model: attack, version: attack, api_key: 'PRIVATE' }))
  await flush()
  expect(panel.textContent).toContain(attack)
  expect(panel.querySelector('img')).toBeNull()
  expect(panel.textContent).not.toContain('PRIVATE')
})

it('exposes preflight before upload and performs only an explicit probe through the app', async () => {
  vi.resetModules()
  document.body.replaceChildren(Object.assign(document.createElement('div'), { id: 'app' }))
  const fetch = vi.fn(async url => ({ ok: true, status: 200, json: async () => url === '/api/health' ? health : { ...success, error_code: null } }))
  vi.stubGlobal('fetch', fetch)
  const store = await import('../src/state.js')
  const snapshot = JSON.stringify(store.state)
  await import('../src/main.js')
  await flush()
  expect(fetch.mock.calls.map(([url]) => url)).toEqual(['/api/health'])
  expect(document.querySelector('.preflight-panel')).not.toBeNull()
  document.querySelector('.preflight-panel .button--primary').click()
  await flush()
  expect(fetch.mock.calls.map(([url]) => url)).toEqual(['/api/health', '/api/gemini/test'])
  expect(JSON.stringify(store.state)).toBe(snapshot)
})
