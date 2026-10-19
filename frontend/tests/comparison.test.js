// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import fixture from '../src/mocks/analytics-preview.json'
import { allowedPair, createComparisonView, defaultQuestion } from '../src/ui/comparison.js'
import { AppState, resetStateForTests, setDataset, state, transitionTo } from '../src/state.js'

const pair = fixture.comparisons['103144:103145'].validation
const dataset = { ...fixture.dataset, dataset_id: 'dataset-test' }
const change = (node, value) => { node.value = value; node.dispatchEvent(new Event('change')) }

beforeEach(() => {
  resetStateForTests()
  transitionTo(AppState.UPLOADING)
  transitionTo(AppState.VALIDATING)
  setDataset(dataset)
  transitionTo(AppState.READY)
})

it('accepts only pairs returned by the backend, including reverse order', () => {
  expect(allowedPair(dataset, '103144', '103145')).toBe(true)
  expect(allowedPair(dataset, '103145', '103144')).toBe(true)
  expect(allowedPair(dataset, '103144', '103147')).toBe(false)
  expect(allowedPair(dataset, '103144', '103144')).toBe(false)
})

describe('comparison controls', () => {
  it('uses fixtures without requests and blocks Grão × Silagem even on direct submit', () => {
    const navigate = vi.fn()
    const diagnose = vi.fn()
    const view = createComparisonView(navigate, { dataset: null, diagnose })
    const execute = view.querySelector('[type="submit"]')
    expect(execute.disabled).toBe(false)
    change(view.querySelector('[name="reference"]'), '103147')
    expect(execute.disabled).toBe(true)
    view.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
    expect(navigate).not.toHaveBeenCalled()
    expect(diagnose).not.toHaveBeenCalled()
    expect(view.querySelector('textarea').value).toContain('Silagem Convencional')
    view.dispose()
  })
  it('loads live criteria and analyses only for returned valid pairs', async () => {
    const diagnose = vi.fn().mockResolvedValue(pair)
    const view = createComparisonView(() => {}, { dataset, diagnose })
    expect(view.querySelector('[type="submit"]').disabled).toBe(true)
    await vi.waitFor(() => expect(view.querySelector('[type="submit"]').disabled).toBe(false))
    expect(diagnose.mock.calls[0][0]).toBe('validate_comparison')
    expect(diagnose.mock.calls[0][1]).toEqual({ dataset_id: 'dataset-test', target_field_id: '103144', reference_field_id: '103145', period: 'full_season' })
    expect(view.querySelectorAll('.criteria-list li')).toHaveLength(5)
    expect(view.textContent).toContain('Resumo do solo')
    change(view.querySelector('[name="reference"]'), '103147')
    expect(diagnose).toHaveBeenCalledOnce()
    expect(view.querySelector('[type="submit"]').disabled).toBe(true)
    view.dispose()
  })
  it('does not enable an invalid selection when an older response arrives', async () => {
    let resolve
    const diagnose = () => new Promise((done) => { resolve = done })
    const view = createComparisonView(() => {}, { dataset, diagnose })
    change(view.querySelector('[name="reference"]'), '103147')
    resolve(pair)
    await Promise.resolve()
    expect(view.querySelector('[type="submit"]').disabled).toBe(true)
    expect(view.querySelector('#comparison-status').textContent).toContain('Par não permitido')
    view.dispose()
  })
  it('shows controlled errors and blocked comparability', async () => {
    const diagnose = vi.fn().mockRejectedValue(new Error('Sessão indisponível'))
    const view = createComparisonView(() => {}, { dataset, diagnose })
    await vi.waitFor(() => expect(view.textContent).toContain('Sessão indisponível'))
    expect(view.querySelector('[type="submit"]').disabled).toBe(true)
    view.dispose()
    const blocked = createComparisonView(() => {}, { dataset, diagnose: async () => ({ ...pair, allowed: false }) })
    await vi.waitFor(() => expect(blocked.textContent).toContain('Comparação bloqueada'))
    expect(blocked.querySelector('[type="submit"]').disabled).toBe(true)
    blocked.dispose()
  })
  it('uses the new target/reference names in the question and preserves text as text', () => {
    const text = defaultQuestion('<img src=x>', 'Referência')
    expect(text).toContain('<img src=x> e Referência')
    const view = createComparisonView(() => {}, { dataset: null })
    const swap = [...view.querySelectorAll('button')].find((button) => button.textContent === 'Trocar talhões')
    swap.click()
    expect(view.querySelector('textarea').value).toContain('Grão Convencional e Grão 4.0')
    expect(view.querySelector('[name="target"]').value).toBe('103145')
    view.dispose()
  })
})

it('limits selectable fields to the pairs supplied by the backend', () => {
  const onlyGrain = { ...dataset, valid_pairs: dataset.valid_pairs.filter((pair) => pair.purpose === 'grain') }
  const view = createComparisonView(() => {}, { dataset: onlyGrain, diagnose: async () => pair })
  expect([...view.querySelector('[name="target"]').options].map((option) => option.value)).toEqual(['103144', '103145'])
  expect([...view.querySelector('[name="reference"]').options].map((option) => option.value)).toEqual(['103144', '103145'])
  view.dispose()
})

it('keeps the action blocked when the backend has no eligible pair', () => {
  const diagnose = vi.fn()
  const view = createComparisonView(() => {}, { dataset: { ...dataset, valid_pairs: [] }, diagnose })
  expect(view.querySelector('[name="target"]').options.length).toBe(0)
  expect(view.querySelector('[type="submit"]').disabled).toBe(true)
  expect(diagnose).not.toHaveBeenCalled()
  view.dispose()
})

it('submits the selected payload once, locks controls, and navigates after completion', async () => {
  let finish
  const investigate = vi.fn(() => new Promise((resolve) => { finish = resolve }))
  const navigate = vi.fn()
  const onBusyChange = vi.fn()
  const onPreview = vi.fn()
  const view = createComparisonView(navigate, { dataset, diagnose: async () => pair, investigate, onBusyChange, onPreview })
  await vi.waitFor(() => expect(view.querySelector('[type="submit"]').disabled).toBe(false))
  view.querySelector('textarea').value = '  Compare o NDVI e o solo deste pacote.  '
  const form = view.querySelector('form')
  form.dispatchEvent(new Event('submit', { cancelable: true }))
  form.dispatchEvent(new Event('submit', { cancelable: true }))
  await Promise.resolve()
  expect(investigate).toHaveBeenCalledExactlyOnceWith({
    dataset_id: 'dataset-test', target_field_id: '103144', reference_field_id: '103145',
    period: 'full_season', question: 'Compare o NDVI e o solo deste pacote.',
  })
  expect(state.status).toBe(AppState.INVESTIGATING)
  expect(form.getAttribute('aria-busy')).toBe('true')
  expect([...form.querySelectorAll('select, textarea, button:not([hidden])')].every((node) => node.disabled)).toBe(true)
  expect(view.querySelector('progress').hasAttribute('value')).toBe(false)
  expect(view.querySelector('.investigation-progress').hidden).toBe(false)
  expect(view.querySelectorAll('.investigation-progress li')).toHaveLength(5)
  expect(navigate).not.toHaveBeenCalled()
  const result = { status: 'completed', generated_by: 'gemini', investigation_id: 'result' }
  finish(result)
  await vi.waitFor(() => expect(navigate).toHaveBeenCalledExactlyOnceWith('investigation'))
  expect(state.investigation).toBe(result)
  expect(state.dataset).toBe(dataset)
  expect(onPreview).not.toHaveBeenCalled()
  expect(onBusyChange.mock.calls).toEqual([[true], [false]])
  expect(view.querySelector('.investigation-progress').hidden).toBe(true)
  view.dispose()
})

it.each(['curta', 'a'.repeat(501)])('rejects an invalid question before making a request (%#. case)', async (question) => {
  const investigate = vi.fn()
  const view = createComparisonView(vi.fn(), { dataset, diagnose: async () => pair, investigate })
  await vi.waitFor(() => expect(view.querySelector('[type="submit"]').disabled).toBe(false))
  view.querySelector('textarea').value = question
  view.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
  expect(investigate).not.toHaveBeenCalled()
  expect(view.textContent).toContain('entre 10 e 500 caracteres')
  expect(state.status).toBe(AppState.READY)
  view.dispose()
})

it('shows an error safely, supports revisiting it, and restarts without reloading', async () => {
  const navigate = vi.fn()
  const failure = new Error('<img src=x onerror=alert(1)> Serviço indisponível')
  const view = createComparisonView(navigate, { dataset, diagnose: async () => pair, investigate: async () => { throw failure } })
  await vi.waitFor(() => expect(view.querySelector('[type="submit"]').disabled).toBe(false))
  view.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
  await vi.waitFor(() => expect(state.status).toBe(AppState.ERROR))
  await vi.waitFor(() => expect(view.querySelector('[role="alert"]')?.textContent).toBe(failure.message))
  expect(view.querySelector('img')).toBeNull()
  expect(view.querySelector('[type="submit"]').disabled).toBe(true)
  expect(view.querySelector('.investigation-progress').hidden).toBe(true)
  expect(navigate).not.toHaveBeenCalled()
  view.dispose()
  const diagnose = vi.fn()
  const revisited = createComparisonView(navigate, { dataset, diagnose })
  expect(revisited.querySelector('[role="alert"]').textContent).toBe(failure.message)
  expect(diagnose).not.toHaveBeenCalled()
  const restart = [...revisited.querySelectorAll('button')].find((node) => node.textContent === 'Reiniciar pacote')
  expect(restart.hidden).toBe(false)
  restart.click()
  expect(state.status).toBe(AppState.EMPTY)
  expect(state.dataset).toBeNull()
  expect(navigate).toHaveBeenCalledExactlyOnceWith('data')
  revisited.dispose()
})

it('keeps a valid preview separate from the real request and store', () => {
  const investigate = vi.fn()
  const onPreview = vi.fn()
  const navigate = vi.fn()
  const view = createComparisonView(navigate, { dataset: null, investigate, onPreview })
  view.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
  expect(investigate).not.toHaveBeenCalled()
  expect(onPreview).toHaveBeenCalledExactlyOnceWith('103144:103145')
  expect(state.status).toBe(AppState.READY)
  expect(state.investigation).toBeNull()
  view.dispose()
})

it('does not submit after disposal or with a pair that was not checked', async () => {
  const investigate = vi.fn()
  const view = createComparisonView(vi.fn(), { dataset, diagnose: async () => pair, investigate })
  await vi.waitFor(() => expect(view.querySelector('[type="submit"]').disabled).toBe(false))
  view.querySelector('[name="target"]').value = '103145'
  view.querySelector('[name="reference"]').value = '103144'
  view.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
  expect(investigate).not.toHaveBeenCalled()
  view.querySelector('[name="target"]').value = '103144'
  view.querySelector('[name="reference"]').value = '103145'
  view.dispose()
  view.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
  expect(investigate).not.toHaveBeenCalled()
})
