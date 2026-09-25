import './styles/tokens.css'
import './styles/base.css'
import './styles/layout.css'
import './styles/components.css'
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

content.append(topbar, intro, createUploadView())
page.append(createNavigation(), content)
app.replaceChildren(page)
