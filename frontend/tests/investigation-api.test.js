import { afterEach, expect, it, vi } from 'vitest'
import { ApiError, requestInvestigation } from '../src/api.js'
import fixture from '../src/mocks/analytics-preview.json'

const request = { dataset_id: 'dataset', target_field_id: 'target', reference_field_id: 'reference', period: 'full_season', question: 'Compare os talhões.' }
const result = {
  investigation_id: 'result', status: 'completed', generated_by: 'gemini',
  report: { overview: { headline: 'Título', summary: 'Resumo.', evidence_strength: 'weak' }, findings: [], recommendations: [],
    limitations: [{ title: 'Observação', explanation: 'Não comprova causalidade.', rule_id: 'observational_only' }] },
  evidence: [], chart_data: {}, trace: { model: 'gemini-test', created_at: '2026-10-17T12:00:00Z', calls: [] }, warnings: [],
}
afterEach(() => vi.unstubAllGlobals())

it.each(['gemini', 'deterministic_fallback'])('posts JSON and accepts a completed %s response', async (origin) => {
  const payload = { ...result, generated_by: origin }
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => payload })
  vi.stubGlobal('fetch', fetch)
  expect(await requestInvestigation(request)).toBe(payload)
  expect(fetch).toHaveBeenCalledExactlyOnceWith('/api/investigations', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request),
  })
})

it.each([404, 422, 503, 500])('handles HTTP %i without exposing a raw server body', async (status) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status, json: async () => ({ detail: 'PRIVATE_STACK_TRACE' }) }))
  const error = await requestInvestigation(request).catch((caught) => caught)
  expect(error).toBeInstanceOf(ApiError)
  expect(error.status).toBe(status)
  expect(error.message).not.toContain('PRIVATE')
  expect(error.payload).toBeNull()
})

it('handles network failures with a controlled error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('INTERNAL_NETWORK_DETAILS')))
  await expect(requestInvestigation(request)).rejects.toThrow('comunicar com o backend')
})

it.each([null, {}, { ...result, status: 'pending' }, { ...result, generated_by: 'unknown' }, { ...result, report: null }])(
  'rejects an invalid success envelope %#', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
    await expect(requestInvestigation(request)).rejects.toThrow('resposta de investigação inválida')
  },
)

it('handles a non-JSON response', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => { throw new SyntaxError('HTML_BODY') } }))
  await expect(requestInvestigation(request)).rejects.toThrow('resposta de investigação inválida')
})

it.each([
  { headline: {}, summary: 'Resumo.', evidence_strength: 'weak' },
  { headline: 'Título', summary: ' ', evidence_strength: 'weak' },
  { headline: 'Título', summary: 'Resumo.', evidence_strength: 'unknown' },
])('rejects an invalid overview %# before rendering', async (overview) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...result, report: { ...result.report, overview } }) }))
  await expect(requestInvestigation(request)).rejects.toThrow('resposta de investigação inválida')
})

const evidence = { evidence_id: 'EV-TEST-001', method: 'Método local.', source_files: ['source.csv'] }
const finding = { title: 'Achado', explanation: 'Explicação.', evidence_ids: [evidence.evidence_id] }
const recommendation = { action: 'Ação', reason: 'Justificativa.', evidence_ids: [evidence.evidence_id] }

it.each([
  ['lista de achados ausente', { recommendations: [] }, [evidence]],
  ['recomendação sem justificativa', { findings: [], recommendations: [{ ...recommendation, reason: '' }] }, [evidence]],
  ['achado sem evidências', { findings: [{ ...finding, evidence_ids: [] }], recommendations: [] }, [evidence]],
  ['recomendação sem evidências', { findings: [], recommendations: [{ ...recommendation, evidence_ids: null }] }, [evidence]],
  ['referência parcialmente inexistente', { findings: [{ ...finding, evidence_ids: [evidence.evidence_id, 'EV-MISSING-999'] }], recommendations: [] }, [evidence]],
  ['recomendação com referência inexistente', { findings: [], recommendations: [{ ...recommendation, evidence_ids: ['EV-MISSING-999'] }] }, [evidence]],
  ['IDs de evidência ambíguos', { findings: [finding], recommendations: [] }, [evidence, evidence]],
  ['evidência nula', { findings: [], recommendations: [] }, [null]],
  ['explicação inválida', { findings: [{ ...finding, explanation: {} }], recommendations: [] }, [evidence]],
  ['fonte inválida', { findings: [finding], recommendations: [] }, [{ ...evidence, source_files: [] }]],
])('rejects %s without silently dropping unsupported cards', async (_name, cards, evidenceList) => {
  const payload = { ...result, report: { overview: result.report.overview, limitations: result.report.limitations, ...cards }, evidence: evidenceList }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
  const error = await requestInvestigation(request).catch((caught) => caught)
  expect(error).toBeInstanceOf(ApiError)
  expect(error.status).toBe(502)
  expect(error.payload).toBeNull()
})

it('accepts chart_data copies matching their evidence even with different object key order', async () => {
  const ndvi = fixture.comparisons['103144:103145'].ndvi
  const payload = { ...result, evidence: [ndvi, fixture.soil_summary, fixture.soil_groups],
    chart_data: { ndvi: Object.fromEntries(Object.entries(ndvi).reverse()), soil_summaries: [structuredClone(fixture.soil_summary)], soil_groups: [structuredClone(fixture.soil_groups)] } }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
  expect(await requestInvestigation(request)).toBe(payload)
})

it.each(['different_point', 'unknown_id', 'different_summary', 'wrong_collection', 'duplicate_call'])(
  'rejects chart data inconsistent with evidence: %s', async (scenario) => {
    const ndvi = structuredClone(fixture.comparisons['103144:103145'].ndvi)
    const soil = structuredClone(fixture.soil_summary)
    const chart = { ndvi: structuredClone(ndvi), soil_summaries: [structuredClone(soil)], soil_groups: [] }
    if (scenario === 'different_point') chart.ndvi.series[0].target_ndvi = 999
    if (scenario === 'unknown_id') chart.ndvi.evidence_id = 'EV-UNKNOWN-999'
    if (scenario === 'different_summary') chart.soil_summaries[0].metrics[0].median = 999
    if (scenario === 'wrong_collection') chart.soil_summaries = [ndvi]
    if (scenario === 'duplicate_call') chart.soil_summaries.push(chart.soil_summaries[0])
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...result, evidence: [ndvi, soil], chart_data: chart }) }))
    await expect(requestInvestigation(request)).rejects.toThrow('resposta de investigação inválida')
  },
)

it.each(['no_limitations', 'invalid_rule', 'invalid_time', 'invalid_calls', 'invalid_duration'])(
  'rejects malformed audit data: %s', async (scenario) => {
    const payload = structuredClone(result)
    if (scenario === 'no_limitations') payload.report.limitations = []
    if (scenario === 'invalid_rule') payload.report.limitations[0].rule_id = null
    if (scenario === 'invalid_time') payload.trace.created_at = '2026-10-17T12:00:00'
    if (scenario === 'invalid_calls') payload.trace.calls = [null]
    if (scenario === 'invalid_duration') payload.trace.repair = { status: 'error', started_at: '2026-10-17T12:00:00Z', duration_ms: -1 }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
    await expect(requestInvestigation(request)).rejects.toThrow('resposta de investigação inválida')
  },
)
