export const AppState = Object.freeze({
  EMPTY: 'EMPTY',
  UPLOADING: 'UPLOADING',
  VALIDATING: 'VALIDATING',
  READY: 'READY',
  INVESTIGATING: 'INVESTIGATING',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
})

export const state = {
  status: AppState.EMPTY,
  dataset: null,
  investigation: null,
  error: null,
}

let activeInvestigation = null

const ALLOWED_TRANSITIONS = Object.freeze({
  [AppState.EMPTY]: [AppState.UPLOADING],
  [AppState.UPLOADING]: [AppState.VALIDATING, AppState.ERROR],
  [AppState.VALIDATING]: [AppState.READY, AppState.ERROR],
  [AppState.READY]: [AppState.INVESTIGATING],
  [AppState.INVESTIGATING]: [AppState.COMPLETED, AppState.ERROR],
  [AppState.COMPLETED]: [AppState.READY],
  [AppState.ERROR]: [AppState.EMPTY],
})

export function transitionTo(nextStatus) {
  if (!ALLOWED_TRANSITIONS[state.status]?.includes(nextStatus)) {
    throw new Error(`Transição inválida: ${state.status} → ${nextStatus}`)
  }
  state.status = nextStatus
}

export function setDataset(dataset) {
  if (activeInvestigation || state.status === AppState.INVESTIGATING) {
    throw new Error('Aguarde a investigação terminar antes de trocar o pacote.')
  }
  state.dataset = dataset
  state.investigation = null
  state.error = null
}

export function setError(error) {
  state.error = error
}

// The caller supplies the API operation in W4.02. Lock before scheduling it,
// so repeated clicks share the same promise instead of starting another request.
export function runInvestigation(execute) {
  if (activeInvestigation) return activeInvestigation
  if (state.status !== AppState.READY || !state.dataset?.dataset_id) {
    return Promise.reject(new Error('Importe um pacote válido e prepare a comparação antes de investigar.'))
  }
  if (typeof execute !== 'function') {
    return Promise.reject(new TypeError('A investigação exige uma função de execução.'))
  }

  transitionTo(AppState.INVESTIGATING)
  state.investigation = null
  state.error = null
  const operation = Promise.resolve().then(execute).then(
    (result) => {
      if (activeInvestigation === operation) {
        state.investigation = result
        transitionTo(AppState.COMPLETED)
      }
      return result
    },
    (error) => {
      if (activeInvestigation === operation) {
        setError(error)
        transitionTo(AppState.ERROR)
      }
      throw error
    },
  ).finally(() => {
    if (activeInvestigation === operation) activeInvestigation = null
  })
  activeInvestigation = operation
  return operation
}

export function startNewComparison() {
  if (activeInvestigation || state.status !== AppState.COMPLETED || !state.dataset?.dataset_id) {
    return false
  }
  transitionTo(AppState.READY)
  state.investigation = null
  state.error = null
  return true
}

export function resetAfterError() {
  if (state.status !== AppState.ERROR || activeInvestigation) return
  transitionTo(AppState.EMPTY)
  state.dataset = null
  state.investigation = null
  state.error = null
}

export function resetStateForTests() {
  activeInvestigation = null
  state.status = AppState.EMPTY
  state.dataset = null
  state.investigation = null
  state.error = null
}
