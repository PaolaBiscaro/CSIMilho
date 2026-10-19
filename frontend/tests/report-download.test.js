// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { ApiError, requestReport } from '../src/api.js'
import { AppState, resetStateForTests, runInvestigation, setDataset, state, transitionTo } from '../src/state.js'
import { createInvestigationResult } from '../src/ui/results.js'

const htmlResponse = () => ({ ok: true, headers: new Headers({ 'Content-Type': 'text/html; charset=utf-8' }),
  blob: async () => new Blob(['<!doctype html><html lang="pt-BR"><title>Relatório</title></html>'], { type: 'text/html' }) })
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve() }

afterEach(() => {
  document.body.replaceChildren()
  resetStateForTests()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

it('downloads HTML using an encoded ID and a cancellable GET', async () => {
  const fetch = vi.fn().mockResolvedValue(htmlResponse())
  vi.stubGlobal('fetch', fetch)
  const controller = new AbortController()
  const blob = await requestReport('report/id?', { signal: controller.signal })
  expect(fetch).toHaveBeenCalledExactlyOnceWith('/api/investigations/report%2Fid%3F/report', { signal: controller.signal })
  expect(blob.type).toBe('text/html')
  expect(await blob.text()).toContain('Relatório')
})

it.each([404, 503])('handles HTTP %i without exposing server details', async (status) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status, text: async () => 'PRIVATE_SERVER_DETAILS' }))
  const error = await requestReport('report').catch((caught) => caught)
  expect(error).toBeInstanceOf(ApiError)
  expect(error.status).toBe(status)
  expect(error.message).not.toContain('PRIVATE')
  if (status === 404) expect(error.message).toContain('nova investigação')
})

it.each(['network', 'content-type', 'body'])('handles %s failures with safe messages', async (failure) => {
  const response = htmlResponse()
  if (failure === 'content-type') response.headers = new Headers({ 'Content-Type': 'application/json' })
  if (failure === 'body') response.blob = async () => { throw new Error('PRIVATE_BODY') }
  vi.stubGlobal('fetch', failure === 'network' ? vi.fn().mockRejectedValue(new TypeError('PRIVATE_NETWORK')) : vi.fn().mockResolvedValue(response))
  const error = await requestReport('report').catch((caught) => caught)
  expect(error).toBeInstanceOf(ApiError)
  expect(error.message).not.toContain('PRIVATE')
})

it('preserves abort errors from fetch', async () => {
  const error = new DOMException('Aborted', 'AbortError')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
  await expect(requestReport('report')).rejects.toBe(error)
})

async function render() {
  resetStateForTests()
  transitionTo(AppState.UPLOADING)
  transitionTo(AppState.VALIDATING)
  setDataset({ dataset_id: 'dataset-test' })
  transitionTo(AppState.READY)
  const result = { investigation_id: 'completed-id', generated_by: 'gemini', warnings: [], evidence: [],
    report: { overview: { headline: 'Resultado', summary: 'Resumo.', evidence_strength: 'weak' }, findings: [], recommendations: [] } }
  await runInvestigation(async () => result)
  const view = createInvestigationResult(vi.fn())
  document.body.append(view)
  const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:report')
  const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  const clicks = []
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () { clicks.push({ href: this.href, download: this.download }) })
  return { view, button: view.querySelector('[data-action="download-report"]'), result, create, revoke, clicks }
}

it('prevents duplicate downloads and releases the URL while preserving the result', async () => {
  vi.useFakeTimers()
  let resolve
  const fetch = vi.fn().mockReturnValue(new Promise((done) => { resolve = done }))
  vi.stubGlobal('fetch', fetch)
  const { view, button, result, create, revoke, clicks } = await render()
  button.click()
  button.click()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(button.disabled).toBe(true)
  resolve(htmlResponse())
  await flush()
  expect(create).toHaveBeenCalledTimes(1)
  expect(clicks).toEqual([{ href: 'blob:report', download: 'farmlab-completed-id.html' }])
  expect(document.body.querySelector('a[download]')).toBeNull()
  expect(button.disabled).toBe(false)
  expect(view.querySelector('[role="status"]').textContent).toContain('offline')
  expect(state.investigation).toBe(result)
  expect(state.status).toBe(AppState.COMPLETED)
  expect(state.dataset.dataset_id).toBe('dataset-test')
  expect(revoke).not.toHaveBeenCalled()
  await vi.advanceTimersByTimeAsync(1000)
  expect(revoke).toHaveBeenCalledExactlyOnceWith('blob:report')
})

it('allows retry after a failure without losing the completed investigation', async () => {
  vi.useFakeTimers()
  const fetch = vi.fn().mockResolvedValueOnce({ ok: false, status: 404 }).mockResolvedValueOnce(htmlResponse())
  vi.stubGlobal('fetch', fetch)
  const { view, button, result, clicks } = await render()
  button.click()
  await flush()
  expect(view.querySelector('[role="alert"]').textContent).toContain('nova investigação')
  expect(button.disabled).toBe(false)
  expect(state.investigation).toBe(result)
  button.click()
  await flush()
  expect(fetch).toHaveBeenCalledTimes(2)
  expect(clicks).toHaveLength(1)
  expect(view.querySelector('[role="alert"]')).toBeNull()
  await vi.runAllTimersAsync()
})

it('aborts when leaving the page and ignores a late response', async () => {
  let resolve
  const fetch = vi.fn().mockReturnValue(new Promise((done) => { resolve = done }))
  vi.stubGlobal('fetch', fetch)
  const { view, button, create, clicks } = await render()
  button.click()
  const signal = fetch.mock.calls[0][1].signal
  view.dispose()
  expect(signal.aborted).toBe(true)
  resolve(htmlResponse())
  await flush()
  expect(create).not.toHaveBeenCalled()
  expect(clicks).toHaveLength(0)
  button.click()
  expect(fetch).toHaveBeenCalledTimes(1)
})
