// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import fixture from './fixtures/analytics-result.json'
import { investigationEnvelope } from './fixtures/chat-result.js'

vi.mock('chart.js/auto', () => ({ default: class { destroy() {} } }))

let store
const dataset = { ...fixture.dataset, dataset_id: 'dataset-test' }
const pair = fixture.comparisons['103144:103145'].validation

beforeEach(async () => {
  vi.resetModules(); document.body.replaceChildren(Object.assign(document.createElement('div'), { id: 'app' }))
  store = await import('../src/state.js'); store.transitionTo(store.AppState.UPLOADING); store.transitionTo(store.AppState.VALIDATING)
  store.setDataset(dataset); store.transitionTo(store.AppState.READY)
})
afterEach(() => { document.body.replaceChildren(); vi.unstubAllGlobals() })

const response = (payload, status = 200) => ({ ok: status < 400, status, headers: new Headers({ 'content-type': 'application/json' }), json: async () => payload })
const streamResponse = (...blocks) => {
  const encoder = new TextEncoder()
  return {
    ok: true,
    status: 200,
    headers: new Headers({ 'content-type': 'text/event-stream' }),
    body: new ReadableStream({
      start(controller) {
        blocks.forEach((block) => controller.enqueue(encoder.encode(block)))
        controller.close()
      },
    }),
  }
}
const nav = (name) => document.querySelector(`.app-nav [data-page="${name}"]`)
const readyButton = async () => {
  const button = document.querySelector('.comparison-form [type="submit"]')
  await vi.waitFor(() => expect(button.disabled).toBe(false)); return button
}

it('sends one chat request and opens the Top-Down report returned by the backend', async () => {
  let finish
  const fetch = vi.fn(async (url) => {
    if (url === '/api/diagnostics/tools') return response(pair)
    if (url === '/api/chat/respond/stream') return new Promise((resolve) => { finish = resolve })
    throw new Error(`Unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetch); await import('../src/main.js'); nav('comparison').click()
  const execute = await readyButton(); expect(execute.textContent).toBe('Enviar pergunta')
  execute.click(); execute.click(); await vi.waitFor(() => expect(finish).toBeTypeOf('function'))
  expect(fetch.mock.calls.filter(([url]) => url === '/api/chat/respond/stream')).toHaveLength(1)
  expect(document.querySelector('.investigation-progress')).not.toBeNull()
  finish(response(investigationEnvelope()))
  await vi.waitFor(() => expect(store.state.status).toBe(store.AppState.COMPLETED))
  expect(document.querySelector('.answer-label').textContent).toBe('Resposta')
  expect(document.querySelector('.executive-answer h1').textContent).toContain('vigor')
  expect(document.querySelectorAll('[role="tab"]')).toHaveLength(2)
  expect(document.querySelector('main').textContent).not.toContain('Próximos passos')
  expect(store.state.dataset).toBe(dataset)
})

it('keeps the dataset available after a provider failure and allows retry', async () => {
  const fetch = vi.fn(async (url) => url === '/api/diagnostics/tools' ? response(pair)
    : response({ detail: { code: 'unavailable', message: 'O Gemini está indisponível.', retryable: true } }, 503))
  vi.stubGlobal('fetch', fetch); await import('../src/main.js'); nav('comparison').click(); (await readyButton()).click()
  await vi.waitFor(() => expect(document.querySelector('[role="alert"]')?.textContent).toContain('indisponível'))
  expect(store.state.status).toBe(store.AppState.READY)
  expect(store.state.dataset).toBe(dataset)
  expect(document.querySelector('.comparison-form [type="submit"]').disabled).toBe(false)
})

it('shows streamed activities and unlocks the exact comparison question after a final error', async () => {
  const fetch = vi.fn(async (url) => {
    if (url === '/api/diagnostics/tools') return response(pair)
    if (url === '/api/chat/respond/stream') return streamResponse(
      'event: progress\ndata: {"stage":"tool_completed","message":"Comparação concluída com evidência validada."}\n\n',
      'event: progress\ndata: {"stage":"report_synthesizing","message":"Organizando as evidências no relatório executivo."}\n\n',
      'event: error\ndata: {"status":429,"code":"rate_limit","message":"O limite de uso do Gemini foi atingido.","retryable":true}\n\n',
    )
  })
  vi.stubGlobal('fetch', fetch)
  await import('../src/main.js')
  nav('comparison').click()
  const execute = await readyButton()
  const scoreBefore = document.querySelector('.score-orbit strong').textContent
  document.querySelector('textarea').value = 'Quais são as principais divergências entre os talhões analisados?'
  execute.click()
  await vi.waitFor(() => expect(document.querySelector('[role="alert"]')?.textContent).toContain('limite de uso'))
  expect(document.querySelector('.comparison-form [type="submit"]').disabled).toBe(false)
  expect(document.querySelector('.investigation-progress').hidden).toBe(false)
  expect(document.querySelector('.investigation-progress').textContent).toContain('Não foi possível gerar o relatório')
  expect(document.querySelector('.investigation-progress progress').value).toBe(1)
  expect(document.querySelector('.investigation-progress progress').getAttribute('aria-label')).toContain('erro')
  expect(document.querySelector('.score-orbit strong').textContent).toBe(scoreBefore)
  expect(store.state.status).toBe(store.AppState.READY)
  expect(store.state.dataset).toBe(dataset)
  expect(fetch.mock.calls.filter(([url]) => url === '/api/chat/respond/stream')).toHaveLength(1)
})

it('cancels a running request without discarding the imported package', async () => {
  const fetch = vi.fn(async (url, options) => {
    if (url === '/api/diagnostics/tools') return response(pair)
    if (url === '/api/chat/respond/stream') return new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))))
  })
  vi.stubGlobal('fetch', fetch); await import('../src/main.js'); nav('comparison').click(); (await readyButton()).click()
  await vi.waitFor(() => expect(document.querySelector('.investigation-progress button')).not.toBeNull())
  document.querySelector('.investigation-progress button').click()
  await vi.waitFor(() => expect(document.querySelector('[role="alert"]')?.textContent).toContain('cancelada'))
  expect(store.state.status).toBe(store.AppState.READY); expect(store.state.dataset).toBe(dataset)
})
