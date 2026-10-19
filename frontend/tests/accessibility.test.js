// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { table } from '../src/ui/dom.js'
import { createUploadView, EXPECTED_FILES } from '../src/ui/upload.js'
import { createComparisonView } from '../src/ui/comparison.js'
import { resetStateForTests } from '../src/state.js'

afterEach(() => { document.body.replaceChildren(); resetStateForTests(); vi.unstubAllGlobals() })

it('makes wide evidence tables named keyboard-scrollable regions with header associations', () => {
  const region = table('Estatísticas de solo', ['Métrica', 'Valor'], [['pH', '5,2']])
  document.body.append(region)
  region.focus()
  expect(document.activeElement).toBe(region)
  expect(region.getAttribute('role')).toBe('region')
  expect(region.getAttribute('aria-label')).toContain('Estatísticas de solo')
  expect(region.querySelector('thead th').scope).toBe('col')
  expect(region.querySelector('tbody th').scope).toBe('row')
})

it('exposes criteria details without hover and associates question instructions', () => {
  const view = createComparisonView(vi.fn())
  document.body.append(view)
  expect(view.querySelectorAll('.criterion-detail').length).toBeGreaterThan(0)
  expect(view.querySelector('.criteria-list li').hasAttribute('title')).toBe(false)
  const question = view.querySelector('textarea')
  expect(view.querySelector(`#${question.getAttribute('aria-labelledby')}`).textContent).toBe('Pergunta para a investigação')
  for (const id of question.getAttribute('aria-describedby').split(' ')) expect(view.querySelector(`#${id}`)).not.toBeNull()
  expect(view.querySelector('#question-hint').textContent).toContain('10 e 500')
  view.dispose()
})

it.each([true, false])('announces upload completion and moves focus to its outcome (success=%s)', async (success) => {
  const payload = { status: 'ready', quality_score: 100, fields: [], files: [], warnings: [], errors: [] }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: success, status: success ? 201 : 422,
    json: async () => success ? payload : { errors: [{ message: 'Pacote incompleto.' }] } }))
  const view = createUploadView()
  document.body.append(view)
  const input = view.querySelector('input')
  expect(input.getAttribute('aria-labelledby')).toBe('upload-label')
  expect(input.getAttribute('aria-describedby')).toContain('upload-hint')
  Object.defineProperty(input, 'files', { value: EXPECTED_FILES.map((name) => new File(['test'], name)), configurable: true })
  input.dispatchEvent(new Event('change'))
  view.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await vi.waitFor(() => {
    expect(document.activeElement).toBe(view.querySelector(success ? '.result-heading h2' : '#upload-status'))
  })
  expect(view.querySelector('#upload-status').getAttribute('role')).toBe(success ? 'status' : 'alert')
})
