import { state, startNewComparison } from '../state.js'
import { element } from './dom.js'
import { createSoilOverview } from './soil-overview.js'
import { createReportCards } from './report-cards.js'
import { createEvidencePanel } from './evidence.js'
import { createInvestigationNdviPanel, createInvestigationSoilPanel } from './investigation-charts.js'
import { createLimitationsPanel, createMethodsPanel } from './audit-panels.js'
import { requestReport } from '../api.js'

const STRENGTH = { weak: 'Fraca', moderate: 'Moderada', strong: 'Forte' }

export function createInvestigationResult(onNavigate) {
  let disposed = false
  let downloadController
  let disposeCharts = () => {}
  const view = element('section', 'page-view investigation-result')
  view.dispose = () => { disposed = true; downloadController?.abort(); disposeCharts() }
  view.dataset.page = 'investigation'
  const card = element('section', 'dashboard-card')
  const result = state.investigation
  if (result) {
    const overview = result.report.overview
    card.append(element('span', 'eyebrow', 'Investigação concluída · Visão geral'),
      element('h1', '', overview.headline))
    const metadata = element('div', 'report-metadata')
    metadata.append(element('span', 'badge', result.generated_by === 'gemini' ? 'Resultado do Gemini' : 'Relatório local · fallback'),
      element('span', 'badge', `Força da evidência: ${STRENGTH[overview.evidence_strength] ?? 'Indisponível'}`))
    card.append(metadata)
    const fallback = result.warnings.find((warning) => warning.code === 'deterministic_fallback')
    if (result.generated_by === 'deterministic_fallback') card.append(element('p', 'report-notice',
      fallback?.message ?? 'Relatório produzido por templates locais a partir das evidências disponíveis.'))
    card.append(element('p', 'report-summary', overview.summary))
    const overviewPanel = element('div', 'result-panel investigation-overview')
    const soilOverview = createSoilOverview(result.evidence)
    const explore = element('button', 'button button--secondary', 'Explorar gráficos de solo')
    explore.type = 'button'
    explore.addEventListener('click', () => {
      selectTab('soil')
      tabs.querySelector('[data-tab="soil"]').focus()
    })
    soilOverview.querySelector('.soil-summary').after(explore)
    overviewPanel.append(card, soilOverview, ...createReportCards(result.report, result.evidence))
    const tabs = element('div', 'result-tabs')
    tabs.setAttribute('role', 'tablist')
    tabs.setAttribute('aria-label', 'Seções da investigação')
    const sections = [['overview', 'Visão geral'], ['soil', 'Solo'], ['evidence', 'Evidências'], ['chart', 'Gráfico NDVI'], ['methods', 'Métodos'], ['limitations', 'Limitações']]
    const panels = new Map(sections.map(([key]) => [key, key === 'overview' ? overviewPanel : element('div', 'result-panel')]))
    const host = element('div', 'investigation-panels')
    let activeChart = null
    let activeTab = null
    function selectTab(id) {
      if (activeTab === id) return
      activeChart?.dispose?.()
      activeChart = null
      if (activeTab === 'soil' || activeTab === 'chart') panels.get(activeTab).replaceChildren()
      if (id === 'evidence' && !panels.get(id).hasChildNodes()) panels.get(id).append(createEvidencePanel(result.evidence, state.dataset?.fields))
      if (id === 'methods' && !panels.get(id).hasChildNodes()) panels.get(id).append(createMethodsPanel(result))
      if (id === 'limitations' && !panels.get(id).hasChildNodes()) panels.get(id).append(createLimitationsPanel(result.report.limitations))
      for (const [key, panel] of panels) {
        panel.id = `investigation-panel-${key}`
        panel.setAttribute('role', 'tabpanel')
        panel.setAttribute('aria-labelledby', `investigation-tab-${key}`)
        panel.tabIndex = 0
        panel.hidden = key !== id
        if (!panel.parentNode) host.append(panel)
      }
      for (const button of tabs.children) {
        const selected = button.dataset.tab === id
        button.classList.toggle('result-tab--active', selected)
        button.setAttribute('aria-selected', String(selected))
        button.tabIndex = selected ? 0 : -1
      }
      if (id === 'soil' || id === 'chart') {
        activeChart = id === 'soil' ? createInvestigationSoilPanel(result.chart_data ?? {})
          : createInvestigationNdviPanel(result.chart_data ?? {}, state.dataset?.fields)
        panels.get(id).append(activeChart)
        activeChart.mount()
      }
      activeTab = id
    }
    sections.forEach(([id, label], index) => {
      const button = element('button', 'result-tab', label)
      button.type = 'button'
      button.id = `investigation-tab-${id}`
      button.dataset.tab = id
      button.setAttribute('role', 'tab')
      button.setAttribute('aria-controls', `investigation-panel-${id}`)
      button.addEventListener('click', () => selectTab(id))
      button.addEventListener('keydown', (event) => {
        const next = { ArrowRight: (index + 1) % sections.length, ArrowLeft: (index + sections.length - 1) % sections.length,
          Home: 0, End: sections.length - 1 }[event.key]
        if (next !== undefined) {
          event.preventDefault()
          selectTab(sections[next][0])
          tabs.children[next].focus()
        }
      })
      tabs.append(button)
    })
    view.append(tabs, host)
    disposeCharts = () => { activeChart?.dispose?.(); activeChart = null }
    selectTab('overview')
  } else {
    card.append(element('h1', '', 'Nenhuma investigação concluída'),
      element('p', '', 'Configure uma comparação para investigar o pacote importado.'))
    view.append(card)
  }
  const back = element('button', 'button button--primary', result ? 'Nova comparação' : 'Configurar comparação')
  back.type = 'button'
  back.dataset.action = 'new-comparison'
  back.addEventListener('click', () => {
    if (result && !startNewComparison()) return
    onNavigate('comparison')
  })
  const actions = element('div', 'card-actions')
  actions.append(back)
  if (result) {
    const download = element('button', 'button button--secondary', 'Baixar relatório HTML')
    download.type = 'button'
    download.dataset.action = 'download-report'
    const status = element('p', 'status-message')
    status.setAttribute('role', 'status')
    download.addEventListener('click', async () => {
      if (download.disabled || disposed) return
      download.disabled = true
      download.textContent = 'Baixando…'
      status.setAttribute('role', 'status')
      status.textContent = 'Preparando o download do relatório.'
      downloadController = new AbortController()
      try {
        const blob = await requestReport(result.investigation_id, { signal: downloadController.signal })
        if (disposed) return
        const url = URL.createObjectURL(blob)
        const link = element('a')
        link.href = url
        link.download = `farmlab-${encodeURIComponent(result.investigation_id)}.html`
        try {
          document.body.append(link)
          link.click()
          status.textContent = 'Download solicitado. O arquivo pode ser aberto offline.'
        } finally {
          link.remove()
          setTimeout(() => URL.revokeObjectURL(url), 1000)
        }
      } catch (error) {
        if (disposed) return
        status.setAttribute('role', 'alert')
        status.textContent = error instanceof Error ? error.message : 'Não foi possível baixar o relatório.'
      } finally {
        download.disabled = false
        download.textContent = 'Baixar relatório HTML'
      }
    })
    actions.append(download)
    view.append(status)
  }
  view.append(actions)
  return view
}
