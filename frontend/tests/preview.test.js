import { describe, expect, it } from 'vitest'
import preview from '../src/mocks/analytics-preview.json'
import { NAV_ITEMS } from '../src/ui/navigation.js'

describe('local analytical preview contracts', () => {
  it('exposes the three application areas in order', () => {
    expect(NAV_ITEMS.map((item) => item.id)).toEqual(['data', 'comparison', 'investigation'])
  })

  it('keeps every pair, field and comparison internally consistent', () => {
    const fieldIds = preview.dataset.fields.map((field) => field.field_id)
    for (const pair of preview.dataset.valid_pairs) {
      expect(fieldIds).toContain(pair.target_field_id)
      expect(fieldIds).toContain(pair.reference_field_id)
      const result = preview.comparisons[`${pair.target_field_id}:${pair.reference_field_id}`]
      expect(result.validation.allowed).toBe(true)
      expect(result.validation.criteria).toHaveLength(5)
      expect(result.ndvi.target_field_id).toBe(pair.target_field_id)
    }
  })

  it('has unique evidence IDs in each displayed comparison', () => {
    for (const result of Object.values(preview.comparisons)) {
      const items = [...Object.values(result), preview.soil_summary, preview.soil_summary_2, preview.soil_groups]
      expect(new Set(items.map((item) => item.evidence_id)).size).toBe(items.length)
    }
  })

  it('keeps soil evidence at dataset scope with undocumented units', () => {
    for (const evidence of [preview.soil_summary, preview.soil_summary_2, preview.soil_groups]) {
      expect(evidence.scope).toBe('dataset')
      expect(evidence).not.toHaveProperty('target_field_id')
      expect(evidence.metrics.every((metric) => metric.unit === null)).toBe(true)
    }
  })

  it('provides traceable numeric chart data instead of decorative widths', () => {
    const summary = preview.soil_summary
    expect(summary.metrics.every((metric) => metric.source_files.includes('soil_analysis.csv'))).toBe(true)
    for (const sample of summary.texture.samples) {
      expect(sample.sand + sample.silt + sample.clay).toBeCloseTo(100)
      expect(sample.original_total).toBeGreaterThanOrEqual(95)
      expect(sample.original_total).toBeLessThanOrEqual(105)
    }
    expect(preview.comparisons['103144:103145'].ndvi.series).toHaveLength(5)
  })
})
