import { beforeEach, describe, expect, it } from 'vitest'

import { AppState, resetStateForTests, state, transitionTo } from '../src/state.js'

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
})
