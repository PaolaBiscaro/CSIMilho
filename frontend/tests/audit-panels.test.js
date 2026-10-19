// @vitest-environment happy-dom
import { expect, it } from 'vitest'
import { createLimitationsPanel, createMethodsPanel } from '../src/ui/audit-panels.js'

const call = (overrides = {}) => ({ sequence: 1, tool: 'compare_ndvi', tool_version: '1.0.0',
  arguments: { target_field_id: 'alvo', reference_field_id: 'referencia', period: 'full_season' },
  started_at: '2026-10-17T09:00:01-03:00', duration_ms: 12.3456, status: 'success',
  source_files: ['ndvi_metadata.csv'], result_evidence_ids: ['EV-NDVI-001'], ...overrides })
const result = (calls = [call()]) => ({ generated_by: 'gemini',
  trace: { model: 'gemini-test', created_at: '2026-10-17T09:00:00-03:00', calls },
  evidence: [{ evidence_id: 'EV-NDVI-001', method: 'Média sobre datas pareadas.' }],
})

it('shows ordered limitations and associated rules using literal text', () => {
  const hostile = '<img src=x onerror="alert(1)"> & regra'
  const limitations = [{ title: 'Primeira', explanation: hostile, rule_id: 'observational_only' },
    { title: hostile, explanation: 'Segunda explicação.', rule_id: hostile }]
  const panel = createLimitationsPanel(limitations)
  expect([...panel.querySelectorAll('h3')].map((node) => node.textContent)).toEqual(['Primeira', hostile])
  expect(panel.textContent).toContain(`Regra associada: ${hostile}`)
  expect(panel.querySelectorAll('img, script, [onerror]')).toHaveLength(0)
})

it('shows model, UTC time, exact call duration, arguments, sources and evidence methods', () => {
  const payload = result()
  const snapshot = JSON.stringify(payload)
  const panel = createMethodsPanel(payload)
  expect(panel.textContent).toContain('Modelo configuradogemini-test')
  expect(panel.textContent).toContain('17/10/2026, 12:00:00 UTC')
  expect(panel.textContent).toContain('17/10/2026, 12:00:01 UTC')
  expect(panel.querySelector('.method-card').textContent).toContain('12,3456 ms')
  expect(panel.textContent).toContain('Safra completa')
  expect(panel.textContent).toContain('ndvi_metadata.csv')
  expect(panel.textContent).toContain('EV-NDVI-001 · Média sobre datas pareadas.')
  expect(JSON.stringify(payload)).toBe(snapshot)
})

it('projects only public arguments per tool, preserving order and reporting fallback correctly', () => {
  const payload = result([
    call({ sequence: 1, tool: 'summarize_soil_analysis', arguments: { measurement_group: 'group_2', metrics: ['P', 'CA'], target_field_id: 'HIDDEN_TARGET' } }),
    call({ sequence: 2, tool: 'application_compliance', arguments: { operation: 'CALAGEM', target_field_id: 'alvo', reference_field_id: 'referencia', period: { start: '2025-01-01', end: '2025-02-01' } } }),
    call({ sequence: 3, tool: 'compare_soil_measurement_groups', arguments: { metrics: null } }),
  ])
  payload.generated_by = 'deterministic_fallback'
  const panel = createMethodsPanel(payload)
  expect([...panel.querySelectorAll('.method-card h3')].map((node) => node.textContent)).toEqual(['1 · Resumir análise de solo', '2 · Verificar conformidade de aplicação', '3 · Comparar conjuntos de solo'])
  expect(panel.textContent).toContain('Conjunto 2')
  expect(panel.textContent).toContain('P, CA')
  expect(panel.textContent).toContain('01/01/2025 a 01/02/2025')
  expect(panel.textContent).toContain('CALAGEM')
  expect(panel.textContent).toContain('Todas as métricas disponíveis')
  expect(panel.textContent).not.toContain('HIDDEN_TARGET')
  expect(panel.textContent).toContain('Fallback determinístico · gerado localmente')
  expect(panel.textContent).toContain('não identifica o autor deste relatório')
})

it('never inserts unknown trace fields, credentials, prompts, raw rows or raw error messages into the DOM', () => {
  const secret = 'PRIVATE_SENTINEL_DO_NOT_RENDER'
  const payload = result([call({ status: 'error', source_files: [], result_evidence_ids: [],
    prompt: secret, response: secret, stack: secret, raw_data: secret,
    arguments: { ...call().arguments, api_key: secret, question: secret, dataset_id: secret, dataframe: [{ secret }] },
    error: { code: 'tool_execution_failed', message: secret },
  })])
  Object.assign(payload.trace, { api_key: secret, system_prompt: secret, conversation: secret })
  payload.trace.repair = { status: 'error', started_at: '2026-10-17T12:00:02Z', duration_ms: 20,
    trigger: { message: secret }, trigger_issues: [{ message: secret }], validation_issues: [{ message: secret }], error: { message: secret } }
  const panel = createMethodsPanel(payload)
  expect(panel.outerHTML).not.toContain(secret)
  expect(panel.textContent).toContain('Não foi possível concluir a ferramenta.')
  expect(panel.textContent).toContain('Reparo do relatório')
  expect(panel.textContent).toContain('20 ms')
  expect(panel.textContent).toContain('Fontes: nenhuma registrada')
})

it('renders supported metadata as text and hides unknown tool and error internals', () => {
  const hostile = '<svg onload="alert(1)"></svg>'
  const payload = result([call({ tool_version: hostile, source_files: [hostile] }),
    call({ sequence: 2, tool: 'PRIVATE_TOOL', status: 'error', arguments: { prompt: 'PRIVATE_PROMPT' }, error: { code: 'PRIVATE_CODE', message: 'PRIVATE_MESSAGE' } })])
  payload.trace.model = hostile
  payload.evidence[0].method = hostile
  const panel = createMethodsPanel(payload)
  expect(panel.textContent).toContain(hostile)
  expect(panel.querySelectorAll('svg, script, [onload]')).toHaveLength(0)
  expect(panel.outerHTML).not.toContain('PRIVATE_')
  expect(panel.textContent).toContain('Ferramenta não reconhecida')
  expect(panel.textContent).toContain('A ferramenta não concluiu a execução.')
})

it('handles unavailable metadata distinctly from zero and missing evidence safely', () => {
  const payload = result([call({ duration_ms: 0, result_evidence_ids: ['EV-MISSING-001'] }),
    call({ sequence: 2, duration_ms: null, started_at: 'bad-date' })])
  payload.trace.created_at = null
  const panel = createMethodsPanel(payload)
  expect(panel.textContent).toContain('0 ms')
  expect(panel.textContent).toContain('Duração da chamadaIndisponível')
  expect(panel.textContent).toContain('Início da investigaçãoIndisponível')
  expect(panel.textContent).toContain('Evidência não disponível neste resultado.')
  expect(panel.textContent).not.toContain('Invalid Date')
  expect(createMethodsPanel(result([])).textContent).toContain('Nenhuma execução de ferramenta registrada')
  expect(createLimitationsPanel().textContent).toContain('Isso não significa ausência de restrições')
})
