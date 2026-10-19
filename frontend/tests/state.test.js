// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  AppState, resetAfterError, resetStateForTests, runInvestigation, setDataset,
  startNewComparison, state, transitionTo,
} from '../src/state.js'

function readyDataset() {
  const dataset = { dataset_id: 'validated-dataset', fields: [{ field_id: 'target' }], warnings: [] }
  transitionTo(AppState.UPLOADING)
  transitionTo(AppState.VALIDATING)
  setDataset(dataset)
  transitionTo(AppState.READY)
  return dataset
}

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

describe('state transitions', () => {
  beforeEach(resetStateForTests)

  it('reaches READY only through upload and validation', () => {
    transitionTo(AppState.UPLOADING)
    transitionTo(AppState.VALIDATING)
    transitionTo(AppState.READY)

    expect(state.status).toBe(AppState.READY)
  })

  it('rejects an invalid direct transition', () => {
    expect(() => transitionTo(AppState.READY)).toThrow('Transição inválida')
  })

  it('repeated clicks share a single pending operation and the same result', async () => {
    const dataset = readyDataset()
    const pending = deferred()
    const execute = vi.fn(() => pending.promise)
    const button = document.createElement('button')
    const operations = []
    button.addEventListener('click', () => operations.push(runInvestigation(execute)))

    button.click()
    button.click()
    button.click()
    expect(state.status).toBe(AppState.INVESTIGATING)
    expect(state.investigation).toBeNull()
    expect(operations[1]).toBe(operations[0])
    expect(operations[2]).toBe(operations[0])
    await Promise.resolve()
    expect(execute).toHaveBeenCalledTimes(1)
    button.click()
    expect(operations[3]).toBe(operations[0])

    const result = { investigation_id: 'result', generated_by: 'gemini', report: {} }
    pending.resolve(result)
    await expect(operations[0]).resolves.toBe(result)
    expect(execute).toHaveBeenCalledTimes(1)
    expect(state.status).toBe(AppState.COMPLETED)
    expect(state.investigation).toBe(result)
    expect(state.dataset).toBe(dataset)
    expect(state.error).toBeNull()
  })

  it('a fallback is a completed investigation, not an error', async () => {
    readyDataset()
    const fallback = { generated_by: 'deterministic_fallback', report: {}, warnings: ['provider unavailable'] }
    await runInvestigation(() => fallback)
    expect(state.status).toBe(AppState.COMPLETED)
    expect(state.investigation).toBe(fallback)
    expect(state.error).toBeNull()
  })

  it('starts a new comparison without uploading or modifying the dataset', async () => {
    const dataset = readyDataset()
    const before = structuredClone(dataset)
    await runInvestigation(() => ({ investigation_id: 'first' }))
    expect(startNewComparison()).toBe(true)
    expect(state.status).toBe(AppState.READY)
    expect(state.dataset).toBe(dataset)
    expect(dataset).toEqual(before)
    expect(state.investigation).toBeNull()
    expect(state.error).toBeNull()

    const second = { investigation_id: 'second' }
    await runInvestigation(() => second)
    expect(state.investigation).toBe(second)
    expect(state.dataset).toBe(dataset)
  })

  it.each(['async rejection', 'sync exception'])('stores %s and releases the lock for a future session', async (kind) => {
    const dataset = readyDataset()
    const failure = new Error('Serviço indisponível')
    const execute = kind === 'sync exception' ? () => { throw failure } : () => Promise.reject(failure)
    await expect(runInvestigation(execute)).rejects.toBe(failure)
    expect(state.status).toBe(AppState.ERROR)
    expect(state.error).toBe(failure)
    expect(state.investigation).toBeNull()
    expect(state.dataset).toBe(dataset)
    expect(startNewComparison()).toBe(false)

    resetAfterError()
    expect(state.status).toBe(AppState.EMPTY)
    expect(state.dataset).toBeNull()
    expect(state.error).toBeNull()
    readyDataset()
    await runInvestigation(() => ({ investigation_id: 'recovered' }))
    expect(state.status).toBe(AppState.COMPLETED)
  })

  it('shares a rejection without running another callback', async () => {
    readyDataset()
    const pending = deferred()
    const first = runInvestigation(() => pending.promise)
    const extra = vi.fn()
    const second = runInvestigation(extra)
    const settled = Promise.allSettled([first, second])
    const error = new Error('Falha na investigação')
    pending.reject(error)
    expect(await settled).toEqual([
      { status: 'rejected', reason: error }, { status: 'rejected', reason: error },
    ])
    expect(extra).not.toHaveBeenCalled()
    expect(state.status).toBe(AppState.ERROR)
  })

  it('cannot replace the dataset or start a new comparison during a request', async () => {
    const dataset = readyDataset()
    const pending = deferred()
    const operation = runInvestigation(() => pending.promise)
    expect(startNewComparison()).toBe(false)
    expect(() => setDataset({ dataset_id: 'replacement' })).toThrow('Aguarde')
    resetAfterError()
    expect(state.status).toBe(AppState.INVESTIGATING)
    expect(state.dataset).toBe(dataset)
    pending.resolve({ investigation_id: 'result' })
    await operation
  })

  it('blocks execution without a ready dataset and after completion', async () => {
    const execute = vi.fn(() => ({ investigation_id: 'result' }))
    await expect(runInvestigation(execute)).rejects.toThrow('Importe')
    expect(execute).not.toHaveBeenCalled()
    expect(state.status).toBe(AppState.EMPTY)
    readyDataset()
    setDataset(null)
    await expect(runInvestigation(execute)).rejects.toThrow('Importe')
    expect(execute).not.toHaveBeenCalled()
    setDataset({ dataset_id: 'dataset' })
    await runInvestigation(execute)
    await expect(runInvestigation(execute)).rejects.toThrow('prepare')
    expect(execute).toHaveBeenCalledTimes(1)
    expect(state.investigation.investigation_id).toBe('result')
  })

  it('rejects a missing execution function without changing the ready state', async () => {
    readyDataset()
    await expect(runInvestigation(null)).rejects.toThrow('função de execução')
    expect(state.status).toBe(AppState.READY)
  })

  it('does not let a result from a reset test session overwrite the new state', async () => {
    readyDataset()
    const pending = deferred()
    const previous = runInvestigation(() => pending.promise)
    await Promise.resolve()
    resetStateForTests()
    const dataset = readyDataset()
    const next = deferred()
    const current = runInvestigation(() => next.promise)
    pending.resolve({ investigation_id: 'obsolete' })
    await previous
    expect(state.status).toBe(AppState.INVESTIGATING)
    expect(state.investigation).toBeNull()
    expect(state.dataset).toBe(dataset)
    const extra = vi.fn()
    expect(runInvestigation(extra)).toBe(current)
    expect(extra).not.toHaveBeenCalled()
    next.resolve({ investigation_id: 'current' })
    await current
    expect(state.investigation.investigation_id).toBe('current')
  })
})
