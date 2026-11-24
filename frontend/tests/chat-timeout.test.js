import { afterEach, expect, it, vi } from 'vitest'
import { ApiError, requestChat } from '../src/api.js'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

it('aborts a stalled chat stream and returns an explicit deadline error', async () => {
  vi.useFakeTimers()
  vi.stubGlobal('fetch', vi.fn((_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  })))

  const pending = requestChat({ dataset_id: 'dataset', message: 'Analise os dados disponíveis.' })
  const assertion = expect(pending).rejects.toMatchObject({
    name: 'ApiError', status: 504,
    message: expect.stringContaining('95 segundos'),
  })
  await vi.advanceTimersByTimeAsync(95_000)
  await assertion
})

it('preserves an explicit user cancellation instead of reporting a timeout', async () => {
  const controller = new AbortController()
  vi.stubGlobal('fetch', vi.fn((_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  })))
  const pending = requestChat(
    { dataset_id: 'dataset', message: 'Analise os dados disponíveis.' },
    { signal: controller.signal },
  )
  controller.abort()
  const error = await pending.catch((caught) => caught)
  expect(error).toBeInstanceOf(DOMException)
  expect(error.name).toBe('AbortError')
  expect(error).not.toBeInstanceOf(ApiError)
})
