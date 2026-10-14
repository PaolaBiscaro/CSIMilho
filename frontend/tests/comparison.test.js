// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest'
import fixture from '../src/mocks/analytics-preview.json'
import { allowedPair, createComparisonView, defaultQuestion } from '../src/ui/comparison.js'

const pair = fixture.comparisons['103144:103145'].validation
const dataset = { ...fixture.dataset, dataset_id: 'dataset-test' }
const change = (node, value) => { node.value = value; node.dispatchEvent(new Event('change')) }

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
    expect(view.querySelector('[role="status"]').textContent).toContain('Par não permitido')
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
