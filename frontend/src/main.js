import './styles/tokens.css'
import './styles/base.css'
import './styles/layout.css'
import './styles/components.css'
import { createComparisonView } from './ui/comparison.js'
import { createNavigation } from './ui/navigation.js'
import { createUploadView } from './ui/upload.js'
import { createInvestigationResult } from './ui/results.js'
import { createGeminiTestControl } from './ui/preflight.js'
import { AppState, startNewComparison, state } from './state.js'

const app = document.querySelector('#app')

if (!app) {
  throw new Error('Elemento raiz da aplicação não encontrado.')
}

function element(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function createDataView() {
  const view = element('section', 'page-view')
  view.dataset.page = 'data'

  const heading = element('div', 'page-heading')
  const copy = element('div')
  copy.append(
    element('span', 'eyebrow', '01 · Preparar dados'),
    element('h1', '', 'Pacote da safra'),
    element('p', 'page-heading__description', 'Importe os sete arquivos, confira a qualidade e avance com o pacote validado.'),
  )
  const context = element('div', 'heading-context')
  const geminiControl = createGeminiTestControl()
  context.append(geminiControl)
  heading.append(copy, context)

  const metrics = element('div', 'metric-grid metric-grid--three')
  const items = [
    ['Arquivos necessários', '7', 'Nomes definidos para cada CSV'],
    ['Formato aceito', 'CSV', 'Um pacote por análise'],
    ['Limite do pacote', '100 MB', 'Soma dos arquivos enviados'],
  ]
  for (const [label, value, detail] of items) {
    const card = element('article', 'metric-card')
    card.append(
      element('span', 'metric-card__label', label),
      element('strong', 'metric-card__value', value),
      element('small', 'metric-card__detail', detail),
    )
    metrics.append(card)
  }

  view.append(heading, metrics, createUploadView())
  view.mount = () => geminiControl.mount()
  view.dispose = () => geminiControl.dispose()
  return view
}

const shell = element('div', 'app-shell')
const headerSlot = element('div', 'header-slot')
const content = element('main', 'content')
content.id = 'main-content'
content.tabIndex = -1
const skip = element('a', 'skip-link', 'Pular para o conteúdo')
skip.href = '#main-content'
skip.addEventListener('click', (event) => { event.preventDefault(); content.focus() })
let currentPage = 'data'
let activeView
let dataView = createDataView()

function renderNavigation(busy = state.status === AppState.INVESTIGATING) {
  headerSlot.replaceChildren(createNavigation(currentPage, navigate, {
    busy,
    comparisonAvailable: Boolean(state.dataset?.dataset_id),
    investigationAvailable: Boolean(state.investigation),
  }))
}

function navigate(pageId) {
  if (!['data', 'comparison', 'investigation'].includes(pageId)) return
  if (state.status === AppState.INVESTIGATING) return
  if (pageId === 'comparison' && !state.dataset?.dataset_id) return
  if (pageId === 'investigation' && !state.investigation) return
  if (pageId === 'comparison' && state.status === AppState.COMPLETED) startNewComparison()
  if (pageId === 'data' && state.status === AppState.EMPTY) dataView = createDataView()
  const moveFocus = Boolean(activeView)
  activeView?.dispose?.()
  currentPage = pageId
  activeView = pageId === 'data' ? dataView : pageId === 'comparison'
    ? createComparisonView(navigate, { onBusyChange: renderNavigation })
    : createInvestigationResult(navigate)
  renderNavigation()
  content.replaceChildren(activeView)
  activeView.mount?.()
  const pageName = currentPage === 'data' ? 'Dados' : currentPage === 'comparison' ? 'Perguntar aos dados' : 'Resposta'
  document.title = `${pageName} · FarmLab Investigator`
  if (moveFocus) {
    const title = activeView.querySelector('h1') ?? content
    title.tabIndex = -1
    title.focus({ preventScroll: true })
  }
  window.scrollTo({ top: 0, behavior: 'instant' })
}

shell.addEventListener('farmlab:continue', () => navigate('comparison'))
shell.append(skip, headerSlot, content)
app.replaceChildren(shell)
navigate('data')
