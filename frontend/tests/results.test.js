// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AppState, resetStateForTests, runInvestigation, setDataset, state, transitionTo } from '../src/state.js'
import { createInvestigationResult } from '../src/ui/results.js'
import { descriptiveEnvelope, investigationEnvelope } from './fixtures/chat-result.js'

vi.mock('chart.js/auto', () => ({ default: class { destroy() {} } }))

beforeEach(() => resetStateForTests())
afterEach(() => { document.body.replaceChildren(); resetStateForTests(); vi.unstubAllGlobals() })

async function render(result) {
  transitionTo(AppState.UPLOADING); transitionTo(AppState.VALIDATING)
  setDataset({ dataset_id: 'dataset-test', fields: [{ field_id: '103144', label: 'Grão 4.0' }, { field_id: '103145', label: 'Convencional' }] })
  transitionTo(AppState.READY); await runInvestigation(() => Promise.resolve(result))
  const navigate = vi.fn(); const view = createInvestigationResult(navigate); document.body.append(view)
  return { view, navigate }
}

it('renders a concise Top-Down answer and keeps deterministic technical details in a second tab', async () => {
  const result = investigationEnvelope(); const { view } = await render(result)
  expect(view.querySelector('.answer-label').textContent).toBe('Resposta')
  expect(view.querySelector('.executive-answer h1').textContent).toBe(result.response.report.executive_answer.headline)
  expect(view.querySelector('.report-summary').textContent).toBe(result.response.report.executive_answer.answer)
  expect(view.textContent).not.toContain('Principais insights')
  expect(view.textContent).toContain('O que não pôde ser respondido')
  expect(view.textContent).not.toContain('Próximos passos')
  const tabs = [...view.querySelectorAll('[role="tab"]')]
  expect(tabs.map((item) => item.textContent)).toEqual(['Resposta', 'Rastreabilidade técnica'])
  expect(view.querySelector('.investigation-technical').hidden).toBe(true)
  expect(view.querySelector('.technical-shortcut').textContent).toBe('Abrir rastreabilidade técnica')
  view.querySelector('.technical-shortcut').click()
  expect(view.querySelector('.investigation-technical').hidden).toBe(false)
  expect(tabs[1].getAttribute('aria-selected')).toBe('true')
  expect(view.querySelector('.investigation-technical').textContent).toContain('Teste pareado')
  expect(view.querySelector('.investigation-technical').textContent).toContain('ndvi_metadata.csv')
  expect(view.querySelector('.investigation-technical').textContent).toContain('Inputs')
  expect(view.querySelector('.investigation-technical').textContent).toContain('Outputs')
  expect(view.querySelector('.investigation-technical').textContent).toContain('Adequação do p-valor')
  expect(view.querySelector('.investigation-technical').textContent).toContain('Baixa sustentação')
})

it('renders narrative as text and never interprets injected markup', async () => {
  const result = investigationEnvelope(); const hostile = '<img src=x onerror=alert(1)><script>x</script>'
  result.response.report.executive_answer.headline = hostile
  result.response.report.executive_answer.answer = hostile
  const { view } = await render(result)
  expect(view.querySelector('h1').textContent).toBe(hostile)
  expect(view.querySelectorAll('img, script, [onerror]')).toHaveLength(0)
})

it('renders descriptive answers without pretending they are reports', async () => {
  const { view } = await render(descriptiveEnvelope())
  expect(view.querySelector('h1').textContent).toBe('O que os dados mostram')
  expect(view.textContent).toContain('Série disponível')
  expect(view.querySelectorAll('[role="tab"]')).toHaveLength(0)
  expect(view.querySelector('button').textContent).toBe('Fazer outra pergunta')
})

it('preserves conversation history and starts another question with the same dataset', async () => {
  const first = descriptiveEnvelope(); await render(first)
  expect(state.conversation).toHaveLength(1)
  const navigate = vi.fn(); const view = createInvestigationResult(navigate); document.body.replaceChildren(view)
  view.querySelector('.report-actions button').click()
  expect(navigate).toHaveBeenCalledWith('comparison')
  expect(state.status).toBe(AppState.READY)
  expect(state.dataset.dataset_id).toBe('dataset-test')
  expect(state.conversation).toHaveLength(1)
})

it('keeps the empty response route usable', () => {
  const navigate = vi.fn(); const view = createInvestigationResult(navigate)
  expect(view.querySelector('h1').textContent).toBe('Nenhuma pergunta respondida')
  view.querySelector('button').click(); expect(navigate).toHaveBeenCalledWith('comparison')
})
