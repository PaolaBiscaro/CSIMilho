import { COMPARISON_PREVIEW, PREVIEW_FIELDS, PREVIEW_NOTICE } from '../mocks/preview-data.js'

function element(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function fieldOptions(selectedId) {
  return PREVIEW_FIELDS.map((field) => {
    const option = element('option', '', field.label)
    option.value = field.id
    option.selected = field.id === selectedId
    return option
  })
}

function metricCard(label, value, detail) {
  const card = element('article', 'metric-card')
  card.append(
    element('span', 'metric-card__label', label),
    element('strong', 'metric-card__value', String(value)),
    element('small', 'metric-card__detail', detail),
  )
  return card
}

function previewNotice() {
  const notice = element('aside', 'preview-notice')
  notice.setAttribute('role', 'note')
  notice.append(
    element('strong', '', PREVIEW_NOTICE.label),
    element('span', '', PREVIEW_NOTICE.detail),
  )
  return notice
}

export function createComparisonPreview(onNavigate) {
  const view = element('section', 'page-view')
  view.dataset.page = 'comparison'

  const heading = element('div', 'page-heading')
  const headingCopy = element('div')
  headingCopy.append(
    element('span', 'eyebrow', '02 · Comparar'),
    element('h1', '', 'Configure a comparação'),
    element('p', 'page-heading__description', 'Escolha o recorte e as análises que formarão o dashboard. Nenhum cálculo é executado nesta prévia.'),
  )
  const score = element('div', 'score-orbit')
  score.setAttribute('aria-label', `Comparabilidade demonstrativa: ${COMPARISON_PREVIEW.score} de 100`)
  score.append(
    element('strong', '', String(COMPARISON_PREVIEW.score)),
    element('span', '', '/100'),
    element('small', '', 'comparabilidade'),
  )
  heading.append(headingCopy, score)

  const metrics = element('div', 'metric-grid metric-grid--four')
  metrics.append(
    metricCard('Datas pareadas', COMPARISON_PREVIEW.pairedDates, 'NDVI demonstrativo'),
    metricCard('Operações comuns', COMPARISON_PREVIEW.operations, 'Plantio e calagem'),
    metricCard('Amostras de solo', COMPARISON_PREVIEW.soilSamples, 'Escopo do dataset'),
    metricCard('Período', '2024/25', 'Safra selecionada'),
  )

  const workspace = element('div', 'dashboard-grid comparison-grid')
  const formCard = element('form', 'dashboard-card comparison-form')
  formCard.append(
    element('span', 'card-kicker', '01 · Recorte'),
    element('h2', '', 'Talhões e período'),
  )

  const fields = element('div', 'form-grid')
  const targetLabel = element('label', 'control-field')
  targetLabel.append(element('span', '', 'Talhão analisado'))
  const target = document.createElement('select')
  target.name = 'target'
  target.append(...fieldOptions(COMPARISON_PREVIEW.targetId))
  targetLabel.append(target)

  const referenceLabel = element('label', 'control-field')
  referenceLabel.append(element('span', '', 'Talhão de referência'))
  const reference = document.createElement('select')
  reference.name = 'reference'
  reference.append(...fieldOptions(COMPARISON_PREVIEW.referenceId))
  referenceLabel.append(reference)

  const periodLabel = element('label', 'control-field')
  periodLabel.append(element('span', '', 'Período'))
  const period = document.createElement('select')
  period.name = 'period'
  period.append(...COMPARISON_PREVIEW.periods.map((item) => {
    const option = element('option', '', item)
    option.value = item
    return option
  }))
  periodLabel.append(period)
  fields.append(targetLabel, referenceLabel, periodLabel)

  const swap = element('button', 'button button--ghost swap-button', 'Trocar talhões')
  swap.type = 'button'
  swap.addEventListener('click', () => {
    const targetValue = target.value
    target.value = reference.value
    reference.value = targetValue
    updateQuestion()
  })

  const analysisSection = element('fieldset', 'analysis-selector')
  analysisSection.append(element('legend', '', 'Análises para o painel'))
  const analysisGrid = element('div', 'analysis-selector__grid')
  for (const analysis of COMPARISON_PREVIEW.availableAnalyses) {
    const option = element('button', `analysis-option${analysis.active ? ' analysis-option--active' : ''}`)
    option.type = 'button'
    option.dataset.analysis = analysis.id
    option.setAttribute('aria-pressed', String(analysis.active))
    option.append(
      element('strong', '', analysis.label),
      element('small', '', analysis.detail),
      element('span', 'analysis-option__state', analysis.active ? 'Incluída' : 'Opcional'),
    )
    option.addEventListener('click', () => {
      const active = option.getAttribute('aria-pressed') !== 'true'
      option.setAttribute('aria-pressed', String(active))
      option.classList.toggle('analysis-option--active', active)
      option.querySelector('.analysis-option__state').textContent = active ? 'Incluída' : 'Opcional'
    })
    analysisGrid.append(option)
  }
  analysisSection.append(analysisGrid)

  const questionLabel = element('label', 'control-field control-field--wide')
  questionLabel.append(element('span', '', 'Pergunta de investigação'))
  const question = document.createElement('textarea')
  question.name = 'question'
  question.rows = 5
  question.value = COMPARISON_PREVIEW.question
  questionLabel.append(question)

  function updateQuestion() {
    const targetName = PREVIEW_FIELDS.find((field) => field.id === target.value)?.label
    const referenceName = PREVIEW_FIELDS.find((field) => field.id === reference.value)?.label
    question.value = `O que as análises de solo indicam sobre o contexto da área e quais sinais aparecem na execução de correção e no vigor dos talhões ${targetName} e ${referenceName}?`
  }
  target.addEventListener('change', updateQuestion)
  reference.addEventListener('change', updateQuestion)

  const formActions = element('div', 'card-actions')
  const back = element('button', 'button button--secondary', 'Voltar aos dados')
  back.type = 'button'
  back.addEventListener('click', () => onNavigate('data'))
  const execute = element('button', 'button button--primary', 'Ver prévia da investigação')
  execute.type = 'submit'
  formActions.append(back, execute)
  formCard.append(fields, swap, analysisSection, questionLabel, formActions)
  formCard.addEventListener('submit', (event) => {
    event.preventDefault()
    onNavigate('investigation')
  })

  const criteriaCard = element('aside', 'dashboard-card criteria-card')
  criteriaCard.append(
    element('span', 'card-kicker', '02 · Qualidade do par'),
    element('h2', '', 'Critérios disponíveis'),
    element('p', 'card-description', 'Valores ilustrativos para antecipar o componente que receberá a validação real.'),
  )
  const criteriaList = element('ul', 'criteria-list')
  for (const criterion of COMPARISON_PREVIEW.criteria) {
    const item = element('li')
    item.append(
      element('span', '', criterion.label),
      element('strong', '', criterion.status),
    )
    criteriaList.append(item)
  }
  criteriaCard.append(criteriaList)

  const soilPriority = element('div', 'soil-priority-callout')
  soilPriority.append(
    element('span', 'card-kicker', 'Foco da prévia'),
    element('strong', '', 'Solo em primeiro plano'),
    element('p', '', 'A investigação abrirá distribuição, comparação pareada, textura e qualidade das 8 amostras mocadas.'),
  )
  criteriaCard.append(soilPriority)

  workspace.append(formCard, criteriaCard)
  view.append(previewNotice(), heading, metrics, workspace)
  return view
}
