// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { createGeminiTestControl } from '../src/ui/preflight.js'
import { resetStateForTests } from '../src/state.js'

const success = {
  success: true, model: 'configured-model', latency_ms: 0,
  message: '1 de 1 chaves do Gemini disponíveis.', error_code: null,
  configured_key_count: 1, available_key_count: 1,
  key_results: [{ slot: 1, success: true, latency_ms: 0, error_code: null }],
}
const flush = async () => { for (let n = 0; n < 8; n++) await Promise.resolve() }
const controls = []

function render(probeGemini = vi.fn().mockResolvedValue(success)) {
  const control = createGeminiTestControl({ probeGemini })
  controls.push(control)
  document.body.append(control)
  return { control, button: control.querySelector('button'), probeGemini }
}

afterEach(() => {
  controls.splice(0).forEach((control) => control.dispose())
  document.body.replaceChildren()
  resetStateForTests()
  vi.unstubAllGlobals()
})

it('shows one compact button without running an automatic diagnostic', () => {
  const { control, button, probeGemini } = render()
  expect(button.textContent).toBe('Testar conexão com o Gemini')
  expect(control.querySelectorAll('button')).toHaveLength(1)
  expect(control.textContent).not.toContain('Backend')
  expect(control.textContent).not.toContain('Modelo configurado')
  expect(probeGemini).not.toHaveBeenCalled()
})

it('runs only after a click, deduplicates clicks and shows a short success state', async () => {
  let finish
  const probe = vi.fn().mockReturnValue(new Promise((resolve) => { finish = resolve }))
  const { control, button } = render(probe)
  button.click(); button.click()
  expect(probe).toHaveBeenCalledTimes(1)
  expect(button.disabled).toBe(true)
  finish(success)
  await flush()
  expect(button.disabled).toBe(false)
  expect(control.querySelector('[role="status"]').textContent).toBe(success.message)
})

it('shows a useful failure and allows retry', async () => {
  const probe = vi.fn().mockResolvedValueOnce({ ...success, success: false, message: 'Limite de uso atingido.' }).mockResolvedValueOnce(success)
  const { control, button } = render(probe)
  button.click(); await flush()
  expect(control.querySelector('[role="alert"]').textContent).toBe('Limite de uso atingido.')
  button.click(); await flush()
  expect(control.querySelector('[role="status"]').textContent).toBe(success.message)
})

it('warns when only part of the configured key pool is available', async () => {
  const partial = {
    ...success,
    message: 'Somente 1 de 2 chaves do Gemini está disponível.',
    configured_key_count: 2,
    available_key_count: 1,
    error_code: 'partial_availability',
    key_results: [
      { slot: 1, success: true, latency_ms: 1, error_code: null },
      { slot: 2, success: false, latency_ms: 1, error_code: 'rate_limit' },
    ],
  }
  const { control, button } = render(vi.fn().mockResolvedValue(partial))
  button.click(); await flush()
  expect(control.querySelector('[role="alert"]').textContent).toContain('1 de 2')
})

it('does not request health on app load and tests Gemini only by explicit action', async () => {
  vi.resetModules()
  document.body.replaceChildren(Object.assign(document.createElement('div'), { id: 'app' }))
  const fetch = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ ...success, error_code: null }) }))
  vi.stubGlobal('fetch', fetch)
  await import('../src/main.js')
  await flush()
  expect(fetch).not.toHaveBeenCalled()
  expect(document.querySelector('.preflight-panel')).toBeNull()
  document.querySelector('.gemini-test-control button').click()
  await flush()
  expect(fetch).toHaveBeenCalledExactlyOnceWith('/api/gemini/test', expect.objectContaining({ method: 'POST' }))
})
