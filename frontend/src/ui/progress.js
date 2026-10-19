import { element } from './dom.js'

export function createInvestigationProgress() {
  const panel = element('section', 'investigation-progress')
  panel.hidden = true
  panel.tabIndex = -1
  panel.setAttribute('aria-label', 'Processamento da investigação')
  const status = element('p', 'status-message', 'Investigação em andamento. Aguarde a conclusão.')
  status.setAttribute('role', 'status')
  const progress = element('progress')
  progress.setAttribute('aria-label', 'Investigação em andamento')
  // The synchronous endpoint does not stream stages. List the workflow without
  // timers, percentages or a fabricated current/completed stage.
  const stages = element('ol', 'detail-list')
  for (const text of ['Validar o recorte', 'Planejar a investigação', 'Executar ferramentas analíticas',
    'Validar evidências', 'Gerar a visão geral']) {
    stages.append(element('li', '', text))
  }
  panel.append(status, progress, element('p', '', 'Etapas da investigação:'), stages)
  return panel
}
