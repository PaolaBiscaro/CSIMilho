import { createComparisonView } from './ui/comparison.js'
import { createInvestigationView } from './ui/investigation.js'
import './styles/tokens.css'
import './styles/base.css'
import './styles/layout.css'
import './styles/components.css'
import './styles/prototype.css'
import { createNavigation } from './ui/navigation.js'
import { createUploadView } from './ui/upload.js'

const app = document.querySelector('#app')

if (!app) {
  throw new Error('Elemento raiz da aplicação não encontrado.')
}

const page = document.createElement('div')
page.className = 'app-shell'

const content = document.createElement('main')
content.className = 'content'

const topbar = document.createElement('header')
topbar.className = 'topbar'

const status = document.createElement('span')
status.className = 'system-status'
status.textContent = 'Sessão local'

const phase = document.createElement('span')
phase.className = 'phase-label'
phase.textContent = 'Semana 1 · Importação'
topbar.append(status, phase)

const intro = document.createElement('section')
intro.className = 'page-intro'

const eyebrow = document.createElement('p')
eyebrow.className = 'eyebrow'
eyebrow.textContent = 'Preparar dados'

const title = document.createElement('h1')
title.textContent = 'Comece pelo pacote da safra'

const description = document.createElement('p')
description.className = 'page-intro__description'
description.textContent = 'Reúna os seis arquivos esperados. O FarmLab valida nomes, estrutura e relações antes de liberar a comparação.'

intro.append(eyebrow, title, description)

const dataView = document.createElement('div')
dataView.append(intro, createUploadView())
const views = { data: dataView, comparison: createComparisonView(), investigation: createInvestigationView() }
content.append(topbar, ...Object.values(views))
content.addEventListener('farmlab:continue', () => { window.location.hash = 'comparison' })
page.append(createNavigation(), content)
app.replaceChildren(page)

function showCurrentView() {
  const requested = window.location.hash.slice(1)
  const current = Object.hasOwn(views, requested) ? requested : 'data'
  Object.entries(views).forEach(([id, view]) => { view.hidden = id !== current })
  page.querySelectorAll('[data-step]').forEach(link => {
    const active = link.dataset.step === current
    link.closest('li').classList.toggle('step--current', active)
    link.closest('li').removeAttribute('aria-current')
    if (active) link.setAttribute('aria-current', 'page')
    else link.removeAttribute('aria-current')
  })
  phase.textContent = { data: 'Importação', comparison: 'Comparação', investigation: 'Investigação' }[current]
  window.scrollTo({ top: 0 })
}
window.addEventListener('hashchange', showCurrentView)
showCurrentView()

