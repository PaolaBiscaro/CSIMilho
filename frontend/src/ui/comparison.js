import { requestChat, runDiagnostic } from '../api.js'
import { AppState, recoverAfterInvestigationError, resetAfterError, runInvestigation, state } from '../state.js'
import { control, element } from './dom.js'
import { createInvestigationProgress } from './progress.js'

export function allowedPair(dataset, target, reference) {
  return dataset.valid_pairs.some((pair) => pair.target_field_id === target && pair.reference_field_id === reference)
}

export function defaultQuestion(target, reference) {
  return `O que as análises de solo indicam sobre o contexto da área e quais sinais aparecem na execução de correção e no vigor dos talhões ${target} e ${reference}?`
}

export function defaultSingleQuestion(field) {
  return `Analise a trajetória temporal do NDVI do talhão ${field}, identifique mudanças bruscas e indique o que merece verificação.`
}

const ANALYSES = {
  compare_ndvi: 'Trajetória NDVI', check_initial_condition: 'Condição inicial',
  compare_population: 'População de plantas', application_compliance: 'Conformidade de aplicação',
  summarize_soil_analysis: 'Resumo do solo', compare_soil_measurement_groups: 'Conjunto 1 × Conjunto 2',
}

export function createComparisonView(onNavigate, {
  dataset = state.dataset, diagnose = runDiagnostic, investigate = requestChat,
  onBusyChange = () => {},
} = {}) {
  if (!dataset?.dataset_id) {
    const empty = element('section', 'page-view')
    empty.dataset.page = 'comparison'
    const card = element('section', 'dashboard-card empty-state')
    card.append(element('h1', '', 'Importe os dados para comparar'),
      element('p', '', 'A comparação será liberada depois que os sete arquivos CSV forem validados.'))
    const back = element('button', 'button button--primary', 'Importar arquivos')
    back.type = 'button'
    back.addEventListener('click', () => onNavigate('data'))
    card.append(back)
    empty.append(card)
    empty.dispose = () => {}
    return empty
  }
  const source = dataset
  const view = element('section', 'page-view')
  view.dataset.page = 'comparison'
  const notice = element('aside', 'preview-notice')
  notice.append(element('strong', '', 'Investigação do pacote importado'),
    element('span', '', 'Escolha analisar um talhão ou comparar dois talhões e envie sua pergunta.'))
  const heading = element('div', 'page-heading')
  const copy = element('div')
  copy.append(element('span', 'eyebrow', '02 · Perguntar aos dados'), element('h1', '', 'Converse com seus dados'),
    element('p', 'page-heading__description', 'Peça uma descrição, consulte o que está disponível ou faça uma investigação completa.'))
  const score = element('div', 'score-orbit')
  const scoreValue = element('strong', '', '—')
  score.append(scoreValue, element('span', '', '/5'), element('small', '', 'critérios atendidos'))
  heading.append(copy, score)
  const grid = element('div', 'dashboard-grid comparison-grid')
  const form = element('form', 'dashboard-card comparison-form')
  form.append(element('h2', '', 'Escopo e período'))
  const fields = element('div', 'form-grid')
  const mode = control('Tipo de análise', 'analysis_mode', [['comparison', 'Comparar dois talhões'], ['single_field', 'Analisar um talhão']])
  const answerMode = control('Tipo de resposta', 'requested_mode', [['auto', 'Decidir pela pergunta'], ['descriptive', 'Resposta descritiva'], ['investigative', 'Relatório investigativo']])
  const allOptions = source.fields.map((field) => [field.field_id, field.label])
  const eligibleIds = new Set(source.valid_pairs.flatMap((pair) => [pair.target_field_id, pair.reference_field_id]))
  const pairOptions = allOptions.filter(([fieldId]) => eligibleIds.has(fieldId))
  const target = control('Talhão analisado', 'target', pairOptions)
  const reference = control('Talhão de referência', 'reference', pairOptions)
  const firstPair = source.valid_pairs[0]
  if (firstPair) {
    target.select.value = firstPair.target_field_id
    reference.select.value = firstPair.reference_field_id
  }
  const period = control('Período', 'period', [['full_season', 'Safra completa']])
  fields.append(mode.label, answerMode.label, target.label, reference.label, period.label)
  const swap = element('button', 'button button--ghost', 'Trocar talhões')
  swap.type = 'button'
  const questionLabel = element('label', 'control-field')
  const question = element('textarea')
  question.name = 'question'
  question.rows = 4
  question.required = true
  question.minLength = 10
  question.maxLength = 500
  const questionTitle = element('span', '', 'Pergunta para os dados')
  questionTitle.id = 'question-label'
  question.setAttribute('aria-labelledby', 'question-label')
  questionLabel.append(questionTitle, question)
  const status = element('p', 'status-message')
  status.id = 'comparison-status'
  status.setAttribute('role', 'status')
  status.setAttribute('aria-atomic', 'true')
  const questionHint = element('small', '', 'Use entre 10 e 500 caracteres. Você também pode perguntar quais dados ou análises estão disponíveis. Investigações geram um relatório completo.')
  questionHint.id = 'question-hint'
  question.setAttribute('aria-describedby', 'question-hint comparison-status')
  questionLabel.append(questionHint)
  const executeLabel = 'Enviar pergunta'
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
  const criteriaTitle = element('h2', '', 'Qualidade do par')
  criteriaCard.append(criteriaTitle, criteria,
    element('h3', '', 'Análises disponíveis'), analyses, warnings)
  grid.append(form, criteriaCard)
  view.append(notice, heading, progress, grid)
  let controller
  let investigationController
  let revision = 0
  let allowed = false
  let validatedSelection = null
  let busy = false
  let disposed = false
  const isSingle = () => mode.select.value === 'single_field'
  const selection = () => [target.select.value, reference.select.value]
  const selectionKey = () => JSON.stringify([mode.select.value, ...selection(), period.select.value])

  function renderBusy(value, keepProgress = false) {
    busy = value
    form.setAttribute('aria-busy', String(value))
    for (const node of [mode.select, answerMode.select, target.select, reference.select, period.select, question, swap, back]) node.disabled = value
    execute.disabled = value || !allowed || state.status !== AppState.READY
    execute.textContent = value ? 'Analisando…' : executeLabel
    progress.hidden = !value && !keepProgress
    onBusyChange(value)
    if (value) {
      progress.start()
      progress.focus()
    } else progress.complete()
  }

  async function update() {
    if (disposed || busy || state.status === AppState.ERROR) return
    const current = ++revision
    status.setAttribute('role', 'status')
    controller?.abort()
    controller = new AbortController()
    const [targetId, referenceId] = selection()
    const targetLabel = source.fields.find((f) => f.field_id === targetId)?.label ?? targetId
    const referenceLabel = source.fields.find((f) => f.field_id === referenceId)?.label ?? referenceId
    question.value = isSingle() ? defaultSingleQuestion(targetLabel) : defaultQuestion(targetLabel, referenceLabel)
    allowed = false
    validatedSelection = null
    execute.disabled = true
    scoreValue.textContent = '—'
    criteria.replaceChildren()
    analyses.replaceChildren()
    warnings.textContent = ''
    reference.label.hidden = isSingle()
    swap.hidden = isSingle()
    score.hidden = isSingle()
    criteriaTitle.textContent = isSingle() ? 'Análise do talhão' : 'Qualidade do par'
    if (isSingle()) {
      allowed = Boolean(targetId)
      validatedSelection = selectionKey()
      execute.disabled = !allowed || state.status !== AppState.READY
      ;['Trajetória temporal e mudanças bruscas de NDVI', 'População de plantas', 'Aplicações registradas', 'Contexto do solo no pacote'].forEach((name) => analyses.append(element('li', '', name)))
      criteria.append(element('li', '', 'A investigação usará somente os registros do talhão selecionado.'))
      warnings.textContent = 'Se faltarem datas, métricas ou ferramentas adequadas, o relatório explicará a lacuna.'
      status.textContent = 'Pronto para investigar a trajetória e os registros deste talhão.'
      return
    }
    if (!allowedPair(source, targetId, referenceId)) {
      status.textContent = 'Par não permitido. Escolha talhões com mesma finalidade e manejos distintos entre os pares disponíveis.'
      return
    }
    status.textContent = 'Verificando comparabilidade…'
    try {
      const result = await diagnose('validate_comparison', {
        dataset_id: source.dataset_id, target_field_id: targetId, reference_field_id: referenceId, period: period.select.value,
      }, { signal: controller.signal })
      if (current !== revision) return
      allowed = result.allowed
      validatedSelection = selectionKey()
      execute.disabled = !allowed || state.status !== AppState.READY
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
  mode.select.addEventListener('change', () => {
    const priorTarget = target.select.value
    const nextOptions = isSingle() ? allOptions : pairOptions
    target.select.replaceChildren(...nextOptions.map(([value, label]) => Object.assign(element('option', '', label), { value })))
    if (nextOptions.some(([value]) => value === priorTarget)) target.select.value = priorTarget
    if (!isSingle() && firstPair) {
      target.select.value = firstPair.target_field_id
      reference.select.value = firstPair.reference_field_id
    }
    update()
  })
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
    if (disposed || busy || !allowed || validatedSelection !== selectionKey() || (!isSingle() && !allowedPair(source, ...selection()))) return
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
      dataset_id: source.dataset_id, message: text, requested_mode: answerMode.select.value,
      target_field_id: target.select.value, reference_field_id: isSingle() ? null : reference.select.value,
      prior_turn_id: state.conversation.at(-1)?.turn_id ?? null,
    }
    investigationController = new AbortController()
    progress.setCancelHandler(() => investigationController?.abort())
    const operation = runInvestigation(() => investigate(payload, {
      onProgress: (event) => progress.add(event), signal: investigationController.signal,
    }))
    status.textContent = ''
    renderBusy(true)
    try {
      await operation
    } catch (error) {
      if (disposed) return
      const canRetry = error?.status !== 404 && recoverAfterInvestigationError()
      const message = error?.name === 'AbortError' ? 'A solicitação foi cancelada. O pacote continua disponível.'
        : error instanceof Error ? error.message : 'Não foi possível concluir a solicitação.'
      renderBusy(false, true)
      progress.fail(message)
      status.setAttribute('role', 'alert')
      status.textContent = message
      restart.hidden = canRetry
      if (canRetry) execute.focus()
      else {
        restart.hidden = false
        restart.focus()
      }
      return
    }
    if (disposed) return
    renderBusy(false)
    onNavigate('investigation')
  })
  view.dispose = () => { disposed = true; revision++; controller?.abort(); investigationController?.abort(); progress.dispose?.() }
  if (state.status === AppState.ERROR) {
    status.setAttribute('role', 'alert')
    status.textContent = state.error instanceof Error ? state.error.message : 'Não foi possível concluir a investigação.'
    restart.hidden = false
  } else {
    update()
  }
  return view
}
