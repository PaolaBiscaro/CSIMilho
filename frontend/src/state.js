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
  error: null,
}

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
  state.dataset = dataset
  state.error = null
}

export function setError(error) {
  state.error = error
}

export function resetAfterError() {
  if (state.status !== AppState.ERROR) return
  transitionTo(AppState.EMPTY)
  state.dataset = null
  state.error = null
}

export function resetStateForTests() {
  state.status = AppState.EMPTY
  state.dataset = null
  state.error = null
}
