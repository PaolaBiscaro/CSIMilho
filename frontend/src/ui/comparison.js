import { requestInvestigation, runDiagnostic } from '../api.js'
import preview from '../mocks/analytics-preview.json'
import { AppState, resetAfterError, runInvestigation, state } from '../state.js'
import { control, element } from './dom.js'
import { createInvestigationProgress } from './progress.js'

export function allowedPair(dataset, target, reference) {
  return dataset.valid_pairs.some((pair) => pair.target_field_id === target && pair.reference_field_id === reference)
}

export function defaultQuestion(target, reference) {
  return `O que as análises de solo indicam sobre o contexto da área e quais sinais aparecem na execução de correção e no vigor dos talhões ${target} e ${reference}?`
}

const ANALYSES = {
  compare_ndvi: 'Trajetória NDVI', check_initial_condition: 'Condição inicial',
  compare_population: 'População de plantas', application_compliance: 'Conformidade de aplicação',
  summarize_soil_analysis: 'Resumo do solo', compare_soil_measurement_groups: 'Conjunto 1 × Conjunto 2',
}

export function createComparisonView(onNavigate, {
  dataset = state.dataset, diagnose = runDiagnostic, investigate = requestInvestigation,
  onPreview = () => {}, onBusyChange = () => {},
} = {}) {
  const mock = !dataset
  const source = dataset ?? preview.dataset
  const view = element('section', 'page-view')
  view.dataset.page = 'comparison'
  const notice = element('aside', 'preview-notice')
  notice.append(element('strong', '', mock ? 'Prévia · dados demonstrativos locais' : 'Comparação do pacote importado'),
    element('span', '', mock ? 'Dados fictícios para explorar a comparação e os gráficos.' : 'Confira os critérios e envie sua pergunta para investigar o pacote importado.'))
  const heading = element('div', 'page-heading')
  const copy = element('div')
  copy.append(element('span', 'eyebrow', '02 · Comparar'), element('h1', '', 'Configure a comparação'),
    element('p', 'page-heading__description', 'Mesmo propósito, manejos distintos e cinco critérios explícitos de comparabilidade.'))
  const score = element('div', 'score-orbit')
  const scoreValue = element('strong', '', '—')
  score.append(scoreValue, element('span', '', '/5'), element('small', '', 'critérios atendidos'))
  heading.append(copy, score)
  const grid = element('div', 'dashboard-grid comparison-grid')
  const form = element('form', 'dashboard-card comparison-form')
  form.append(element('h2', '', 'Talhões e período'))
  const fields = element('div', 'form-grid')
  const eligibleIds = new Set(source.valid_pairs.flatMap((pair) => [pair.target_field_id, pair.reference_field_id]))
  const options = source.fields.filter((field) => eligibleIds.has(field.field_id)).map((field) => [field.field_id, field.label])
  const target = control('Talhão analisado', 'target', options)
  const reference = control('Talhão de referência', 'reference', options)
  const firstPair = source.valid_pairs[0]
  if (firstPair) {
    target.select.value = firstPair.target_field_id
    reference.select.value = firstPair.reference_field_id
  }
  const period = control('Período', 'period', [['full_season', 'Safra completa']])
  fields.append(target.label, reference.label, period.label)
  const swap = element('button', 'button button--ghost', 'Trocar talhões')
  swap.type = 'button'
  const questionLabel = element('label', 'control-field')
  const question = element('textarea')
  question.name = 'question'
  question.rows = 4
  question.required = true
  question.minLength = 10
  question.maxLength = 500
  const questionTitle = element('span', '', 'Pergunta para a investigação')
  questionTitle.id = 'question-label'
  question.setAttribute('aria-labelledby', 'question-label')
  questionLabel.append(questionTitle, question)
  const status = element('p', 'status-message')
  status.id = 'comparison-status'
  status.setAttribute('role', 'status')
  status.setAttribute('aria-atomic', 'true')
  const questionHint = element('small', '', 'Use entre 10 e 500 caracteres. Os dados permitem comparações observacionais, sem comprovar causalidade.')
  questionHint.id = 'question-hint'
  question.setAttribute('aria-describedby', 'question-hint comparison-status')
  questionLabel.append(questionHint)
  const executeLabel = mock ? 'Ver gráficos demonstrativos' : 'Executar investigação'
  const execute = element('button', 'button button--primary', executeLabel)
  execute.type = 'submit'
  execute.disabled = true
  const back = element('button', 'button button--secondary', 'Voltar aos dados')
  back.type = 'button'
  back.addEventListener('click', () => onNavigate('data'))
  const restart = element('button', 'button button--secondary', 'Reiniciar pacote')
  restart.type = 'button'
  restart.hidden = true
  restart.addEventListener('click', () => {
    if (busy) return
    resetAfterError()
    onNavigate('data')
  })
  const progress = createInvestigationProgress()
  const actions = element('div', 'card-actions')
  actions.append(back, execute, restart)
  form.append(fields, swap, questionLabel, status, actions)
  const criteriaCard = element('aside', 'dashboard-card criteria-card')
  const criteria = element('ul', 'criteria-list')
  const analyses = element('ul', 'detail-list')
  const warnings = element('div', 'chart-hint')
  criteriaCard.append(element('h2', '', 'Qualidade do par'), criteria,
    element('h3', '', 'Análises disponíveis'), analyses, warnings)
  grid.append(form, criteriaCard)
  view.append(notice, heading, progress, grid)
  let controller
  let revision = 0
  let allowed = false
  let validatedSelection = null
  let busy = false
  let disposed = false
  const selection = () => [target.select.value, reference.select.value]
  const selectionKey = () => JSON.stringify([...selection(), period.select.value])

  function renderBusy(value) {
    busy = value
    form.setAttribute('aria-busy', String(value))
    for (const node of [target.select, reference.select, period.select, question, swap, back]) node.disabled = value
    execute.disabled = value || !allowed || (!mock && state.status !== AppState.READY)
    execute.textContent = value ? 'Investigando…' : executeLabel
    progress.hidden = !value
    onBusyChange(value)
    if (value) progress.focus()
  }

  async function update() {
    if (disposed || busy || (!mock && state.status === AppState.ERROR)) return
    const current = ++revision
    status.setAttribute('role', 'status')
    controller?.abort()
    controller = new AbortController()
    const [targetId, referenceId] = selection()
    question.value = defaultQuestion(source.fields.find((f) => f.field_id === targetId)?.label ?? '', source.fields.find((f) => f.field_id === referenceId)?.label ?? '')
    allowed = false
    validatedSelection = null
    execute.disabled = true
    scoreValue.textContent = '—'
    criteria.replaceChildren()
    analyses.replaceChildren()
    warnings.textContent = ''
    if (!allowedPair(source, targetId, referenceId)) {
      status.textContent = 'Par não permitido. Escolha talhões com mesma finalidade e manejos distintos entre os pares disponíveis.'
      return
    }
    status.textContent = 'Verificando comparabilidade…'
    try {
      const result = mock ? preview.comparisons[`${targetId}:${referenceId}`].validation : await diagnose('validate_comparison', {
        dataset_id: source.dataset_id, target_field_id: targetId, reference_field_id: referenceId, period: period.select.value,
      }, { signal: controller.signal })
      if (current !== revision) return
      allowed = result.allowed
      validatedSelection = selectionKey()
      execute.disabled = !allowed || (!mock && state.status !== AppState.READY)
      scoreValue.textContent = String(result.score)
      for (const item of result.criteria) {
        const li = element('li')
        li.append(element('span', '', item.label), element('strong', '', item.satisfied === null ? 'Indisponível' : item.satisfied ? 'Atendido' : 'Não atendido'))
        li.append(element('p', 'criterion-detail', item.detail))
        criteria.append(li)
      }
      result.available_analyses.forEach((name) => analyses.append(element('li', '', ANALYSES[name] ?? name)))
      warnings.textContent = result.warnings.join(' ')
      status.textContent = allowed ? `${result.paired_dates} datas pareadas · Operações comuns: ${result.common_operations.join(', ') || 'nenhuma'}.` : 'Comparação bloqueada pelos critérios de cultura ou finalidade.'
    } catch (error) {
      if (current === revision && error.name !== 'AbortError') {
        status.setAttribute('role', 'alert')
        status.textContent = error.message
      }
    }
  }
  target.select.addEventListener('change', update)
  reference.select.addEventListener('change', update)
  period.select.addEventListener('change', update)
  swap.addEventListener('click', () => {
    const value = target.select.value
    target.select.value = reference.select.value
    reference.select.value = value
    update()
  })
  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    if (disposed || busy || !allowed || validatedSelection !== selectionKey() || !allowedPair(source, ...selection())) return
    if (mock) {
      onPreview(selection().join(':'))
      onNavigate('investigation')
      return
    }
    if (state.status !== AppState.READY || state.dataset?.dataset_id !== source.dataset_id) return
    const text = question.value.trim()
    if (text.length < 10 || text.length > 500) {
      question.setAttribute('aria-invalid', 'true')
      status.setAttribute('role', 'alert')
      status.textContent = 'Escreva uma pergunta entre 10 e 500 caracteres.'
      question.focus()
      return
    }
    question.removeAttribute('aria-invalid')
    const payload = {
      dataset_id: source.dataset_id, target_field_id: target.select.value,
      reference_field_id: reference.select.value, period: period.select.value, question: text,
    }
    const operation = runInvestigation(() => investigate(payload))
    status.textContent = ''
    renderBusy(true)
    try {
      await operation
    } catch (error) {
      if (disposed) return
      renderBusy(false)
      status.setAttribute('role', 'alert')
      status.textContent = error instanceof Error ? error.message : 'Não foi possível concluir a investigação.'
      restart.hidden = false
      restart.focus()
      return
    }
    if (disposed) return
    renderBusy(false)
    onNavigate('investigation')
  })
  view.dispose = () => { disposed = true; revision++; controller?.abort() }
  if (!mock && state.status === AppState.ERROR) {
    status.setAttribute('role', 'alert')
    status.textContent = state.error instanceof Error ? state.error.message : 'Não foi possível concluir a investigação.'
    restart.hidden = false
  } else {
    update()
  }
  return view
}
