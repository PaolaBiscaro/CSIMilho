import investigationMarkup from './investigation.html?raw'

export function createInvestigationView() {
  const view = document.createElement('section')
  view.className = 'prototype-view'
  view.innerHTML = investigationMarkup
  const notice = document.createElement('p')
  notice.className = ''
  notice.textContent = ''
  view.prepend(notice)
  const tabs = [...view.querySelectorAll('[data-tab]')]
  const panels = [...view.querySelectorAll('.tab-panel')]
  view.querySelector('.tabs').setAttribute('role', 'tablist')
  function selectTab(selected) {
    tabs.forEach(tab => {
      const active = tab === selected
      tab.classList.toggle('active', active)
      tab.setAttribute('aria-selected', String(active))
      tab.tabIndex = active ? 0 : -1
    })
    panels.forEach(panel => {
      const active = panel.id === `tab-${selected.dataset.tab}`
      panel.classList.toggle('active', active)
      panel.hidden = !active
    })
  }
  tabs.forEach((tab, index) => {
    tab.id = `trigger-${tab.dataset.tab}`
    tab.setAttribute('role', 'tab')
    tab.setAttribute('aria-controls', `tab-${tab.dataset.tab}`)
    tab.addEventListener('click', () => selectTab(tab))
    tab.addEventListener('keydown', event => {
      let next
      if (event.key === 'ArrowRight') next = tabs[(index + 1) % tabs.length]
      if (event.key === 'ArrowLeft') next = tabs[(index + tabs.length - 1) % tabs.length]
      if (event.key === 'Home') next = tabs[0]
      if (event.key === 'End') next = tabs.at(-1)
      if (!next) return
      event.preventDefault()
      selectTab(next)
      next.focus()
    })
  })
  panels.forEach(panel => {
    panel.setAttribute('role', 'tabpanel')
    panel.setAttribute('aria-labelledby', panel.id.replace('tab-', 'trigger-'))
  })
  selectTab(tabs[0])
  view.querySelector('#newAnalysis').addEventListener('click', () => {
    window.location.hash = 'comparison'
  })
  view.querySelector('#downloadReport').addEventListener('click', () => {
    const copy = view.cloneNode(true)
    copy.querySelector('.tabs').remove()
    copy.querySelector('.result-actions').remove()
    copy.querySelectorAll('.tab-panel').forEach(panel => { panel.hidden = false })
    const report = `<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>FarmLab · Relatório demonstrativo</title><style>body{font:16px/1.6 system-ui;max-width:900px;margin:40px auto;padding:20px;color:#17342d}article{margin:24px 0}svg{max-width:100%}.method-row,.evidence{padding:12px 0;border-bottom:1px solid #ddd}.method-row>*{display:block}.prototype-notice{background:#effbd6;padding:16px}</style><body>${copy.innerHTML}</body></html>`
    const url = URL.createObjectURL(new Blob([report], { type: 'text/html;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'investigacao_farmlab_demonstracao.html'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  })
  return view
}
