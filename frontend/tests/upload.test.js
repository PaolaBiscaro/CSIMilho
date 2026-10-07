import { describe, expect, it } from 'vitest'

import { EXPECTED_FILES, summarizeSelection } from '../src/ui/upload.js'

describe('upload selection', () => {
  it('enables validation only with each expected file once', () => {
    const summary = summarizeSelection(EXPECTED_FILES.map((name) => ({ name })))

    expect(summary.canSubmit).toBe(true)
    expect(summary.statuses.every((item) => item.status === 'received')).toBe(true)
    expect(EXPECTED_FILES).toHaveLength(7)
    expect(EXPECTED_FILES).toContain('soil_analysis.csv')
  })

  it('rejects duplicates and unexpected files', () => {
    const files = EXPECTED_FILES.map((name) => ({ name }))
    files.push({ name: 'fields.csv' }, { name: 'private.csv' })
    const summary = summarizeSelection(files)

    expect(summary.canSubmit).toBe(false)
    expect(summary.statuses.find((item) => item.name === 'fields.csv').status).toBe('invalid')
    expect(summary.unexpected).toEqual(['private.csv'])
  })
})
