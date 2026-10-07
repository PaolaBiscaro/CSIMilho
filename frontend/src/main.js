import './styles/tokens.css'
import './styles/base.css'
import './styles/layout.css'
import './styles/components.css'
import { createComparisonPreview } from './ui/comparison-preview.js'
import { createInvestigationPreview } from './ui/investigation-preview.js'
import { createNavigation } from './ui/navigation.js'
import { createUploadView } from './ui/upload.js'

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

  view.append(heading, metrics, createUploadView())
  return view
}

const shell = element('div', 'app-shell')
const headerSlot = element('div', 'header-slot')
const content = element('main', 'content')
let currentPage = 'data'

function navigate(pageId) {
  if (!views[pageId]) return
  currentPage = pageId
  headerSlot.replaceChildren(createNavigation(currentPage, navigate))
  content.replaceChildren(views[currentPage])
  const pageName = currentPage === 'data' ? 'Dados' : currentPage === 'comparison' ? 'Comparação' : 'Investigação'
  document.title = `${pageName} · FarmLab Investigator`
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const views = {
  data: createDataView(),
  comparison: createComparisonPreview(navigate),
  investigation: createInvestigationPreview(navigate),
}

shell.addEventListener('farmlab:continue', () => navigate('comparison'))
shell.append(headerSlot, content)
app.replaceChildren(shell)
navigate('data')
