import { element } from './dom.js'

export function createInvestigationProgress() {
  const panel = element('section', 'investigation-progress')
  panel.hidden = true
  panel.tabIndex = -1
  panel.setAttribute('aria-label', 'Processamento da investigação')
  const heading = element('h2', '', 'Analisando sua pergunta')
  const status = element('p', 'status-message', 'Preparando a investigação…')
  status.setAttribute('role', 'status')
  const progress = element('progress')
  progress.setAttribute('aria-label', 'Investigação em andamento')
  const elapsed = element('span', 'investigation-elapsed', '0 s')
  const cancel = element('button', 'button button--secondary', 'Cancelar')
  cancel.type = 'button'
  const summary = element('div', 'investigation-progress__summary')
  summary.append(status, elapsed, cancel)
  const details = element('details', 'investigation-log')
  const detailsTitle = element('summary', '', 'Ver atividades executadas')
  const activity = element('ol', 'investigation-activity')
  activity.setAttribute('aria-label', 'Atividades executadas pelo orquestrador')
  activity.setAttribute('aria-live', 'polite')

  function append(message, stage) {
    if (activity.lastElementChild?.dataset.message === message) return
    const item = element('li', `investigation-activity__item investigation-activity__item--${stage}`)
    item.dataset.message = message
    item.append(element('span', 'investigation-activity__marker'), element('span', '', message))
    activity.append(item)
    while (activity.children.length > 12) activity.firstElementChild.remove()
  }

  let startedAt = 0
  let timer = null
  let cancelHandler = null
  const stopTimer = () => { if (timer) clearInterval(timer); timer = null }
  panel.start = () => {
    stopTimer()
    startedAt = Date.now()
    elapsed.textContent = '0 s'
    cancel.disabled = false
    panel.classList.remove('investigation-progress--failed')
    progress.removeAttribute('value')
    progress.removeAttribute('max')
    progress.setAttribute('aria-label', 'Investigação em andamento')
    timer = setInterval(() => { elapsed.textContent = `${Math.floor((Date.now() - startedAt) / 1000)} s` }, 1000)
    activity.replaceChildren()
    heading.textContent = 'Analisando sua pergunta'
    status.setAttribute('role', 'status')
    // Keep the operational trace visible while the request is running. A long
    // Gemini synthesis must not look like a frozen button or an idle screen.
    details.open = true
    status.textContent = 'A investigação está em andamento. Você pode acompanhar as atividades.'
    append('Solicitação enviada ao orquestrador', 'started')
  }
  panel.add = (event) => {
    if (!event || typeof event.message !== 'string' || typeof event.stage !== 'string') return
    status.textContent = event.stage === 'completed' ? 'Investigação concluída.' : event.message
    append(event.message, event.stage)
  }
  panel.complete = () => {
    stopTimer()
    cancel.disabled = true
    progress.max = 1
    progress.value = 1
    progress.setAttribute('aria-label', 'Processamento encerrado')
  }
  panel.fail = (message) => {
    stopTimer()
    cancel.disabled = true
    panel.classList.add('investigation-progress--failed')
    progress.max = 1
    progress.value = 1
    progress.setAttribute('aria-label', 'Processamento encerrado com erro')
    heading.textContent = 'Não foi possível gerar o relatório'
    status.textContent = message
    status.setAttribute('role', 'alert')
    details.open = true
    append(message, 'failed')
  }
  panel.setCancelHandler = (handler) => { cancelHandler = handler }
  panel.dispose = stopTimer
  cancel.addEventListener('click', () => { cancel.disabled = true; cancelHandler?.() })
  details.append(detailsTitle, activity)
  panel.append(heading, summary, progress, details)
  return panel
}
