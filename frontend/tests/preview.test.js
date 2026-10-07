import { describe, expect, it } from 'vitest'

import {
  COMPARISON_PREVIEW,
  INVESTIGATION_PREVIEW,
  INVESTIGATION_TABS,
  PREVIEW_NOTICE,
  PREVIEW_FIELDS,
} from '../src/mocks/preview-data.js'
import { NAV_ITEMS } from '../src/ui/navigation.js'

describe('navigable preview contracts', () => {
  it('exposes the three application areas in order', () => {
    expect(NAV_ITEMS.map((item) => item.id)).toEqual(['data', 'comparison', 'investigation'])
  })

  it('keeps comparison mock references internally consistent', () => {
    const fieldIds = PREVIEW_FIELDS.map((field) => field.id)

    expect(fieldIds).toContain(COMPARISON_PREVIEW.targetId)
    expect(fieldIds).toContain(COMPARISON_PREVIEW.referenceId)
    expect(COMPARISON_PREVIEW.criteria).toHaveLength(4)
  })

  it('provides every investigation preview panel without claiming a real result', () => {
    expect(INVESTIGATION_TABS.map((tab) => tab.id)).toEqual([
      'overview', 'soil', 'evidence', 'chart', 'methods', 'limitations',
    ])
    expect(INVESTIGATION_PREVIEW.summary).toContain('composição demonstrativa')
    expect(INVESTIGATION_PREVIEW.highlights).toHaveLength(4)
  })

  it('labels both future screens as a preview with mocked data', () => {
    expect(PREVIEW_NOTICE.label).toBe('Prévia · dados mocados')
    expect(PREVIEW_NOTICE.detail).toContain('backend')
    expect(PREVIEW_NOTICE.detail).toContain('Gemini')
  })

  it('provides chart-ready mocked soil and NDVI contracts', () => {
    expect(INVESTIGATION_PREVIEW.soil.quality).toHaveLength(4)
    expect(INVESTIGATION_PREVIEW.soil.metrics.length).toBeGreaterThanOrEqual(4)
    expect(INVESTIGATION_PREVIEW.soil.metrics.every((metric) => metric.group1.plot.length === 5)).toBe(true)
    expect(INVESTIGATION_PREVIEW.soil.texture.samples.every((sample) => sample.sand + sample.silt + sample.clay === 100)).toBe(true)
    expect(INVESTIGATION_PREVIEW.ndvi.points.length).toBeGreaterThanOrEqual(8)
  })
})
