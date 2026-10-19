import { afterEach, expect, it, vi } from 'vitest'
import { ApiError, getHealth, testGemini } from '../src/api.js'

const health = { status: 'ok', gemini_configured: true, model: 'configured-model', version: '1.0.0' }
const probe = { success: true, model: 'configured-model', latency_ms: 0, error_code: null }
const respond = (payload, status = 200) => {
  const fetch = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => payload })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
afterEach(() => vi.unstubAllGlobals())

it('reads only public health fields without calling Gemini', async () => {
  const fetch = respond({ ...health, api_key: 'PRIVATE' })
  expect(await getHealth()).toEqual(health)
  expect(fetch).toHaveBeenCalledExactlyOnceWith('/api/health', { signal: undefined })
})

it('posts an empty probe without a dataset, question, key or model override', async () => {
  const fetch = respond({ ...probe, message: 'PRIVATE', prompt: 'PRIVATE' })
  const controller = new AbortController()
  const result = await testGemini({ signal: controller.signal })
  expect(fetch).toHaveBeenCalledExactlyOnceWith('/api/gemini/test', { method: 'POST', signal: controller.signal })
  expect(result.latency_ms).toBe(0)
  expect(result.message).toContain('Conexão com o Gemini verificada')
  expect(JSON.stringify(result)).not.toContain('PRIVATE')
})

it.each([
  [401, 'authentication_error', 'recusou a chave'], [403, 'permission_denied', 'permissão'],
  [429, 'rate_limit', 'limite de uso'], [504, 'timeout', 'demorou'],
  [503, 'unavailable', 'indisponível'], [503, 'missing_api_key', 'não configurada'],
  [502, 'invalid_response', 'vazia ou bloqueada'], [502, '__proto__', 'Não foi possível confirmar'],
])('translates HTTP %i / %s into a safe message', async (status, error_code, message) => {
  respond({ ...probe, success: false, error_code, message: 'PRIVATE_STACK_TRACE' }, status)
  const result = await testGemini()
  expect(result.success).toBe(false)
  expect(result.message).toContain(message)
  expect(result.message).not.toContain('PRIVATE')
})

it.each([{}, { ...health, gemini_configured: 'yes' }, { ...health, model: '' }])('rejects malformed health %#', async (payload) => {
  respond(payload)
  await expect(getHealth()).rejects.toBeInstanceOf(ApiError)
})

it.each([{}, { ...probe, latency_ms: -1 }, { ...probe, success: false }, { ...probe, model: null }])('rejects malformed probe %#', async (payload) => {
  respond(payload)
  await expect(testGemini()).rejects.toThrow('resposta inválida')
})

it.each([getHealth, testGemini])('handles network, non-JSON and cancellation without leaking details %#', async (request) => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('PRIVATE_NETWORK')))
  await expect(request()).rejects.toThrow('conectar ao backend')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => { throw new Error('PRIVATE_HTML') } }))
  const error = await request().catch((caught) => caught)
  expect(error).toBeInstanceOf(ApiError)
  expect(error.message).not.toContain('PRIVATE')
  const abort = new DOMException('Aborted', 'AbortError')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort))
  await expect(request()).rejects.toBe(abort)
})
