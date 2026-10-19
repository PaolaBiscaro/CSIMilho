import './styles/tokens.css'
import './styles/base.css'
import './styles/layout.css'
import './styles/components.css'
import { createComparisonView } from './ui/comparison.js'
import { createInvestigationPreview } from './ui/investigation-preview.js'
import { createNavigation } from './ui/navigation.js'
import { createUploadView } from './ui/upload.js'
import { createInvestigationResult } from './ui/results.js'
import { createPreflightPanel } from './ui/preflight.js'
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
    element('p', 'page-heading__description', 'Importe os sete arquivos, confira a qualidade e avance com um dataset validado.'),
  )
  const context = element('div', 'heading-context')
  context.append(
    element('strong', '', 'Validação local'),
    element('span', '', 'Dados temporários · até 100 MB'),
  )
  heading.append(copy, context)

  const metrics = element('div', 'metric-grid metric-grid--three')
  const items = [
    ['Arquivos obrigatórios', '7', 'CSV com nomes controlados'],
    ['Escopo do solo', 'Dataset', 'Sem associação a talhões'],
    ['Persistência', 'Nenhuma', 'Sessão mantida em memória'],
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

  const preflight = createPreflightPanel()
  view.append(heading, preflight, metrics, createUploadView())
  view.mount = () => preflight.mount()
  view.dispose = () => preflight.dispose()
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
let previewPair = '103144:103145'
let dataView = createDataView()

function renderNavigation(busy = state.status === AppState.INVESTIGATING) {
  headerSlot.replaceChildren(createNavigation(currentPage, navigate, { busy }))
}

function navigate(pageId) {
  if (!['data', 'comparison', 'investigation'].includes(pageId)) return
  if (state.status === AppState.INVESTIGATING) return
  if (pageId === 'comparison' && state.status === AppState.COMPLETED) startNewComparison()
  if (pageId === 'data' && state.status === AppState.EMPTY) dataView = createDataView()
  const moveFocus = Boolean(activeView)
  activeView?.dispose?.()
  currentPage = pageId
  activeView = pageId === 'data' ? dataView : pageId === 'comparison'
    ? createComparisonView(navigate, { onPreview: (key) => { previewPair = key }, onBusyChange: renderNavigation })
    : state.dataset ? createInvestigationResult(navigate) : createInvestigationPreview(navigate, previewPair)
  renderNavigation()
  content.replaceChildren(activeView)
  activeView.mount?.()
  const pageName = currentPage === 'data' ? 'Dados' : currentPage === 'comparison' ? 'Comparação' : 'Investigação'
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
