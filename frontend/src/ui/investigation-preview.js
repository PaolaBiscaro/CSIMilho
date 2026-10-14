import preview from '../mocks/analytics-preview.json'
import { createNdviPanel, createSoilPanel } from './analytical-panels.js'
import { element, formatValue, table } from './dom.js'

const TABS = [['overview', 'Visão geral'], ['soil', 'Solo'], ['evidence', 'Evidências'], ['chart', 'Gráfico NDVI'], ['methods', 'Métodos'], ['limitations', 'Limitações']]

export function createInvestigationPreview(onNavigate, pairKey = '103144:103145') {
  const result = preview.comparisons[pairKey] ?? preview.comparisons['103144:103145']
  const target = preview.dataset.fields.find((field) => field.field_id === result.ndvi.target_field_id).label
  const reference = preview.dataset.fields.find((field) => field.field_id === result.ndvi.reference_field_id).label
  const view = element('section', 'page-view')
  view.dataset.page = 'investigation'
  const notice = element('aside', 'preview-notice')
  notice.append(element('strong', '', 'Prévia · dados demonstrativos locais'), element('span', '', 'Explore os gráficos com dados fictícios. A análise do pacote importado e a síntese por IA ainda não estão disponíveis nesta tela.'))
  const heading = element('div', 'page-heading')
  const copy = element('div')
  copy.append(element('span', 'eyebrow', '03 · Explorar'), element('h1', '', 'Painel analítico local'),
    element('p', 'page-heading__description', `${target} × ${reference} · demonstração com dados fictícios.`))
  const back = element('button', 'button button--secondary', 'Nova comparação')
  back.type = 'button'
  back.addEventListener('click', () => onNavigate('comparison'))
  const download = element('button', 'button button--ghost', 'Relatório indisponível na prévia')
  download.type = 'button'
  download.disabled = true
  const actions = element('div', 'heading-actions')
  actions.append(back, download)
  heading.append(copy, actions)
  const tabs = element('div', 'result-tabs')
  tabs.setAttribute('role', 'tablist')
  tabs.setAttribute('aria-label', 'Seções do painel analítico')
  const host = element('div', 'result-panel')
  host.setAttribute('role', 'tabpanel')
  host.id = 'analytical-panel'
  let activePanel
  const evidence = [result.ndvi, result.initial, result.population, result.application, preview.soil_summary, preview.soil_summary_2, preview.soil_groups]
  // A preview combines independent fixture calls; group-2 has the next ID in a shared investigation.
  const factories = {
    overview: () => {
      const panel = element('section', 'analytical-panel')
      panel.append(element('h2', '', 'Resumo demonstrativo'), element('p', '', 'Explore os valores locais e seus métodos. A síntese da investigação será integrada em uma etapa futura.'))
      const cards = element('div', 'metric-grid metric-grid--three')
      for (const [label, value, detail] of [
        ['Datas NDVI pareadas', result.ndvi.paired_dates, 'Somente datas presentes nos dois talhões'],
        ['Gap médio NDVI', formatValue(result.ndvi.mean_gap), 'Alvo menos referência'],
        ['Amostras de solo', preview.soil_summary.sample_count, 'Escopo geral do dataset'],
      ]) {
        const card = element('article', 'metric-card')
        card.append(element('span', 'metric-card__label', label), element('strong', 'metric-card__value', String(value)), element('small', 'metric-card__detail', detail))
        cards.append(card)
      }
      const explore = element('button', 'button button--primary', 'Explorar gráficos de solo')
      explore.type = 'button'
      explore.addEventListener('click', () => selectTab('soil'))
      panel.append(cards, explore)
      return panel
    },
    soil: () => createSoilPanel(preview.soil_summary, preview.soil_summary_2, preview.soil_groups),
    chart: () => createNdviPanel(result.ndvi, { target, reference }),
    evidence: () => table('Evidências da demonstração local', ['ID', 'Métrica', 'Alvo', 'Referência', 'Diferença', 'Unidade'],
      evidence.map((item) => [item.evidence_id, item.metric ?? 'Múltiplas métricas / regra', formatValue(item.target_value), formatValue(item.reference_value), formatValue(item.difference), item.unit ?? 'não documentada'])),
    methods: () => {
      const panel = element('section', 'dashboard-card')
      panel.append(element('h2', '', 'Métodos determinísticos'))
      for (const item of evidence) panel.append(element('h3', '', item.evidence_id), element('p', '', item.method), element('small', 'chart-source', `${item.source_files.join(', ')} · versão ${item.tool_version} · ${item.observation_count ?? '—'} observações`))
      return panel
    },
    limitations: () => {
      const panel = element('section', 'dashboard-card')
      panel.append(element('h2', '', 'Limitações'))
      const list = element('ul', 'detail-list')
      for (const text of [...preview.soil_summary.limitations, 'Diferenças observadas não comprovam causalidade ou produtividade.', 'Dados demonstrativos locais; baseline do pacote real ainda pendente.']) list.append(element('li', '', text))
      panel.append(list)
      return panel
    },
  }
  function selectTab(id) {
    activePanel?.dispose?.()
    for (const button of tabs.querySelectorAll('button')) {
      const selected = button.dataset.tab === id
      button.classList.toggle('result-tab--active', selected)
      button.setAttribute('aria-selected', String(selected))
      button.tabIndex = selected ? 0 : -1
    }
    activePanel = factories[id]()
    host.setAttribute('aria-labelledby', `analytical-tab-${id}`)
    host.replaceChildren(activePanel)
  }
  for (const [id, label] of TABS) {
    const button = element('button', 'result-tab', label)
    button.type = 'button'
    button.id = `analytical-tab-${id}`
    button.dataset.tab = id
    button.setAttribute('role', 'tab')
    button.setAttribute('aria-controls', host.id)
    button.addEventListener('click', () => selectTab(id))
    button.addEventListener('keydown', (event) => {
      const index = TABS.findIndex(([key]) => key === id)
      let next
      if (event.key === 'ArrowRight') next = (index + 1) % TABS.length
      if (event.key === 'ArrowLeft') next = (index + TABS.length - 1) % TABS.length
      if (event.key === 'Home') next = 0
      if (event.key === 'End') next = TABS.length - 1
      if (next !== undefined) {
        event.preventDefault()
        selectTab(TABS[next][0])
        tabs.children[next].focus()
      }
    })
    tabs.append(button)
  }
  view.append(notice, heading, tabs, host)
  view.dispose = () => activePanel?.dispose?.()
  selectTab('soil')
  return view
}
