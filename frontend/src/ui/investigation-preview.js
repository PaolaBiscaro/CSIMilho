import { INVESTIGATION_PREVIEW, INVESTIGATION_TABS, PREVIEW_NOTICE } from '../mocks/preview-data.js'

const SVG_NS = 'http://www.w3.org/2000/svg'

function element(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function svgElement(tag, attributes = {}) {
  const node = document.createElementNS(SVG_NS, tag)
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value))
  return node
}

function previewNotice() {
  const notice = element('aside', 'preview-notice')
  notice.setAttribute('role', 'note')
  notice.append(
    element('strong', '', PREVIEW_NOTICE.label),
    element('span', '', PREVIEW_NOTICE.detail),
  )
  return notice
}

function metricCard(item, compact = false) {
  const card = element('article', compact ? 'metric-card metric-card--compact' : 'metric-card')
  if (item.tone) card.dataset.tone = item.tone
  card.append(
    element('span', 'metric-card__label', item.label),
    element('strong', 'metric-card__value', item.value),
    element('small', 'metric-card__detail', item.detail),
  )
  return card
}

function sourceLine(text = 'Fonte mockada: soil_analysis.csv') {
  const source = element('small', 'chart-source', text)
  source.setAttribute('aria-label', text)
  return source
}

function overviewPanel(onOpenSoil) {
  const panel = element('div', 'overview-dashboard')
  const summary = element('article', 'dashboard-card summary-card')
  summary.append(
    element('span', 'card-kicker', INVESTIGATION_PREVIEW.strength),
    element('h2', '', INVESTIGATION_PREVIEW.title),
    element('p', 'summary-copy', INVESTIGATION_PREVIEW.summary),
  )

  const soilSpotlight = element('aside', 'dashboard-card soil-spotlight')
  const visual = element('div', 'soil-spotlight__visual')
  visual.setAttribute('aria-label', 'Completude demonstrativa de 94%')
  visual.append(element('strong', '', '94%'), element('span', '', 'completude'))
  const copy = element('div')
  copy.append(
    element('span', 'card-kicker', 'Foco do projeto'),
    element('h2', '', 'Leitura de solo em destaque'),
    element('p', 'card-description', 'Distribuição, comparação pareada e composição de textura em uma área analítica própria.'),
  )
  const openSoil = element('button', 'button button--primary', 'Explorar prévia de solo')
  openSoil.type = 'button'
  openSoil.addEventListener('click', onOpenSoil)
  copy.append(openSoil)
  soilSpotlight.append(visual, copy)

  const signals = element('div', 'overview-signal-grid')
  for (const item of [
    { label: 'Solo', value: '3 visuais', detail: 'distribuição, pares e textura' },
    { label: 'NDVI', value: '33 datas', detail: 'duas séries pareadas' },
    { label: 'Rastreabilidade', value: '3 fontes', detail: 'evidências demonstrativas' },
  ]) signals.append(metricCard(item, true))

  panel.append(summary, soilSpotlight, signals)
  return panel
}

function rangeRow(label, values, className) {
  const [min, q1, median, q3, max] = values.plot
  const row = element('div', 'range-row')
  const track = element('div', 'range-track')
  track.setAttribute('role', 'img')
  track.setAttribute('aria-label', `${label}: mínimo ${values.min}; Q1 ${values.q1}; mediana ${values.median}; Q3 ${values.q3}; máximo ${values.max}`)
  track.title = track.getAttribute('aria-label')

  const whisker = element('span', `range-whisker ${className}`)
  whisker.style.left = `${min}%`
  whisker.style.width = `${max - min}%`
  const box = element('span', `range-box ${className}`)
  box.style.left = `${q1}%`
  box.style.width = `${q3 - q1}%`
  const medianLine = element('span', 'range-median')
  medianLine.style.left = `${median}%`
  const minDot = element('span', `range-dot ${className}`)
  minDot.style.left = `${min}%`
  const maxDot = element('span', `range-dot ${className}`)
  maxDot.style.left = `${max}%`
  track.append(whisker, box, medianLine, minDot, maxDot)
  row.append(element('strong', '', label), track, element('small', '', `${values.min} — ${values.max}`))
  return row
}

function distributionCard(metric) {
  const card = element('article', 'dashboard-card soil-chart-card')
  const head = element('div', 'card-heading-row')
  const copy = element('div')
  copy.append(
    element('span', 'card-kicker', 'Distribuição'),
    element('h3', '', metric.label),
  )
  const badge = element('span', 'data-count', `${metric.valid} válidas`)
  head.append(copy, badge)

  const axis = element('div', 'range-axis')
  axis.append(element('span', '', 'mín.'), element('span', '', 'Q1'), element('span', '', 'mediana'), element('span', '', 'Q3'), element('span', '', 'máx.'))
  const chart = element('div', 'range-chart')
  chart.append(
    rangeRow('Conjunto 1', metric.group1, 'range-tone--primary'),
    rangeRow('Conjunto 2', metric.group2, 'range-tone--soft'),
  )
  const hint = element('p', 'chart-hint', 'Passe o cursor ou toque nas faixas para conferir os cinco números.')
  card.append(head, element('p', 'chart-unit', metric.unit), axis, chart, hint, sourceLine())
  return card
}

function comparisonCard(metric) {
  const card = element('article', 'dashboard-card soil-chart-card comparison-bars-card')
  const copy = element('div')
  copy.append(
    element('span', 'card-kicker', 'Comparação pareada'),
    element('h3', '', `${metric.label} · Conjunto 1 × 2`),
    element('p', 'chart-unit', `${metric.valid} pares válidos · ${metric.unit}`),
  )
  card.append(copy)

  const bars = element('div', 'comparison-bars')
  const series = [
    ['Conjunto 1', metric.comparison.group1, metric.comparison.widths[0], 'comparison-bar--primary'],
    ['Conjunto 2', metric.comparison.group2, metric.comparison.widths[1], 'comparison-bar--soft'],
  ]
  for (const [label, value, width, className] of series) {
    const row = element('div', 'comparison-bar-row')
    const labelRow = element('div', 'comparison-bar-label')
    labelRow.append(element('span', '', label), element('strong', '', value))
    const track = element('div', 'comparison-bar-track')
    const bar = element('span', `comparison-bar ${className}`)
    bar.style.width = `${width}%`
    bar.title = `${label}: ${value}`
    track.append(bar)
    row.append(labelRow, track)
    bars.append(row)
  }
  const delta = element('div', 'delta-callout')
  delta.append(element('span', '', 'Delta mediano'), element('strong', '', metric.comparison.delta), element('small', '', 'Conjunto 2 − Conjunto 1'))
  card.append(bars, delta, sourceLine())
  return card
}

function distributionTable(metric) {
  const wrapper = element('div', 'accessible-table-wrap')
  const table = element('table', 'accessible-table')
  const caption = element('caption', '', `Resumo acessível da distribuição de ${metric.label}`)
  const head = document.createElement('thead')
  const headRow = document.createElement('tr')
  for (const label of ['Grupo', 'Mínimo', 'Q1', 'Mediana', 'Q3', 'Máximo']) headRow.append(element('th', '', label))
  head.append(headRow)
  const body = document.createElement('tbody')
  for (const [label, values] of [['Conjunto 1', metric.group1], ['Conjunto 2', metric.group2]]) {
    const row = document.createElement('tr')
    row.append(element('th', '', label))
    for (const key of ['min', 'q1', 'median', 'q3', 'max']) row.append(element('td', '', values[key]))
    body.append(row)
  }
  table.append(caption, head, body)
  wrapper.append(table)
  return wrapper
}

function textureCard() {
  const texture = INVESTIGATION_PREVIEW.soil.texture
  const card = element('article', 'dashboard-card texture-card')
  const header = element('div', 'card-heading-row')
  const copy = element('div')
  copy.append(
    element('span', 'card-kicker', 'Composição de textura'),
    element('h3', '', 'Areia, silte e argila'),
    element('p', 'chart-unit', 'Percentual por amostra válida · soma de 100%'),
  )
  const donut = element('div', 'texture-donut')
  donut.style.setProperty('--sand', `${texture.average.sand}%`)
  donut.style.setProperty('--silt-end', `${texture.average.sand + texture.average.silt}%`)
  donut.setAttribute('role', 'img')
  donut.setAttribute('aria-label', `Média demonstrativa: ${texture.average.sand}% areia, ${texture.average.silt}% silte e ${texture.average.clay}% argila`)
  donut.append(element('strong', '', `${texture.average.clay}%`), element('span', '', 'argila'))
  header.append(copy, donut)

  const legend = element('div', 'chart-legend')
  for (const [className, label] of [['legend-sand', 'Areia'], ['legend-silt', 'Silte'], ['legend-clay', 'Argila']]) {
    const item = element('span', '')
    item.append(element('i', className), document.createTextNode(label))
    legend.append(item)
  }

  const stacks = element('div', 'texture-stacks')
  for (const sample of texture.samples) {
    const row = element('div', 'texture-row')
    const stack = element('div', 'texture-stack')
    for (const [key, className, label] of [
      ['sand', 'texture-segment--sand', 'areia'],
      ['silt', 'texture-segment--silt', 'silte'],
      ['clay', 'texture-segment--clay', 'argila'],
    ]) {
      const segment = element('span', `texture-segment ${className}`)
      segment.style.width = `${sample[key]}%`
      segment.title = `${sample.id} · ${label}: ${sample[key]}%`
      segment.setAttribute('aria-label', segment.title)
      stack.append(segment)
    }
    row.append(element('strong', '', sample.id), stack)
    stacks.append(row)
  }
  card.append(header, legend, stacks, sourceLine())
  return card
}

function soilPanel() {
  const soil = INVESTIGATION_PREVIEW.soil
  const panel = element('div', 'soil-dashboard')

  const intro = element('article', 'soil-intro-card')
  const introCopy = element('div')
  introCopy.append(
    element('span', 'card-kicker', 'Prioridade analítica'),
    element('h2', '', 'Painel de contexto do solo'),
    element('p', '', 'Distribuições, pares e textura no escopo geral do dataset. Dados mocados, sem associação a talhões.'),
  )
  const scope = element('div', 'scope-pill')
  scope.append(element('strong', '', 'Escopo'), element('span', '', 'Dataset geral'))
  intro.append(introCopy, scope)

  const quality = element('div', 'soil-quality-grid')
  quality.append(...soil.quality.map((item) => metricCard(item, true)))

  const toolbar = element('div', 'dashboard-card soil-toolbar')
  const toolbarCopy = element('div')
  toolbarCopy.append(element('span', 'card-kicker', 'Explorar indicadores'), element('h3', '', 'Escolha a família e a métrica'))
  const controls = element('div', 'soil-filter-group')
  const familyLabel = element('label', 'control-field')
  familyLabel.append(element('span', '', 'Família'))
  const familySelect = document.createElement('select')
  familySelect.name = 'soil-family'
  for (const family of soil.families) {
    const option = element('option', '', family.label)
    option.value = family.id
    familySelect.append(option)
  }
  familyLabel.append(familySelect)
  const metricLabel = element('label', 'control-field')
  metricLabel.append(element('span', '', 'Métrica'))
  const metricSelect = document.createElement('select')
  metricSelect.name = 'soil-metric'
  metricLabel.append(metricSelect)
  controls.append(familyLabel, metricLabel)
  toolbar.append(toolbarCopy, controls)

  const metricHost = element('div', 'soil-metric-grid')
  const tableHost = element('div')

  function visibleMetrics() {
    return familySelect.value === 'all'
      ? soil.metrics
      : soil.metrics.filter((metric) => metric.family === familySelect.value)
  }

  function renderMetricOptions() {
    const options = visibleMetrics()
    metricSelect.replaceChildren(...options.map((metric) => {
      const option = element('option', '', metric.label)
      option.value = metric.id
      return option
    }))
    renderMetric()
  }

  function renderMetric() {
    const metric = soil.metrics.find((item) => item.id === metricSelect.value) ?? visibleMetrics()[0]
    if (!metric) return
    metricHost.replaceChildren(distributionCard(metric), comparisonCard(metric))
    tableHost.replaceChildren(distributionTable(metric))
  }

  familySelect.addEventListener('change', renderMetricOptions)
  metricSelect.addEventListener('change', renderMetric)
  renderMetricOptions()

  panel.append(intro, quality, toolbar, metricHost, textureCard(), tableHost)
  return panel
}

function evidencePanel() {
  const panel = element('div', 'evidence-grid')
  for (const evidence of INVESTIGATION_PREVIEW.evidence) {
    const card = element('article', 'dashboard-card evidence-card')
    card.append(
      element('span', 'card-kicker', evidence.id),
      element('h2', '', evidence.label),
      element('strong', 'evidence-card__value', evidence.value),
      element('small', '', evidence.source),
    )
    panel.append(card)
  }
  return panel
}

function ndviChart() {
  const points = INVESTIGATION_PREVIEW.ndvi.points
  const chart = svgElement('svg', {
    class: 'ndvi-chart',
    viewBox: '0 0 720 250',
    role: 'img',
    'aria-label': 'Gráfico demonstrativo da trajetória NDVI pareada',
  })

  const defs = svgElement('defs')
  const gradient = svgElement('linearGradient', { id: 'ndvi-area', x1: '0', y1: '0', x2: '0', y2: '1' })
  gradient.append(svgElement('stop', { offset: '0%', 'stop-color': '#895129', 'stop-opacity': '0.22' }), svgElement('stop', { offset: '100%', 'stop-color': '#895129', 'stop-opacity': '0' }))
  defs.append(gradient)
  chart.append(defs)

  for (const [y, label] of [[45, '0,75'], [90, '0,65'], [135, '0,55'], [180, '0,45']]) {
    chart.append(svgElement('line', { x1: 48, y1: y, x2: 690, y2: y, class: 'ndvi-grid-line' }))
    const text = svgElement('text', { x: 4, y: y + 4, class: 'ndvi-axis-label' })
    text.textContent = label
    chart.append(text)
  }

  const targetPoints = points.map((point) => `${point.x},${point.targetY}`).join(' ')
  const referencePoints = points.map((point) => `${point.x},${point.referenceY}`).join(' ')
  const areaPath = `M ${points[0].x} 205 L ${targetPoints.replaceAll(',', ' ')} L ${points.at(-1).x} 205 Z`
  chart.append(svgElement('path', { d: areaPath, class: 'ndvi-area' }))
  chart.append(svgElement('polyline', { points: targetPoints, class: 'ndvi-series ndvi-series--target' }))
  chart.append(svgElement('polyline', { points: referencePoints, class: 'ndvi-series ndvi-series--reference' }))

  points.forEach((point, index) => {
    for (const [y, value, className, label] of [
      [point.targetY, point.target, 'ndvi-point ndvi-point--target', 'Grão 4.0'],
      [point.referenceY, point.reference, 'ndvi-point ndvi-point--reference', 'Grão Convencional'],
    ]) {
      const circle = svgElement('circle', { cx: point.x, cy: y, r: 5, class: className, tabindex: 0 })
      const title = svgElement('title')
      title.textContent = `${point.date} · ${label}: ${value}`
      circle.append(title)
      chart.append(circle)
    }
    if (index % 2 === 0 || index === points.length - 1) {
      const date = svgElement('text', { x: point.x, y: 228, class: 'ndvi-date-label', 'text-anchor': 'middle' })
      date.textContent = point.date
      chart.append(date)
    }
  })
  return chart
}

function ndviTable() {
  const wrapper = element('div', 'accessible-table-wrap')
  const table = element('table', 'accessible-table')
  const caption = element('caption', '', 'Valores demonstrativos da trajetória NDVI pareada')
  const head = document.createElement('thead')
  const headRow = document.createElement('tr')
  for (const label of ['Data', 'Grão 4.0', 'Grão Convencional']) headRow.append(element('th', '', label))
  head.append(headRow)
  const body = document.createElement('tbody')
  for (const point of INVESTIGATION_PREVIEW.ndvi.points) {
    const row = document.createElement('tr')
    row.append(element('th', '', point.date), element('td', '', point.target), element('td', '', point.reference))
    body.append(row)
  }
  table.append(caption, head, body)
  wrapper.append(table)
  return wrapper
}

function chartPanel() {
  const panel = element('div', 'ndvi-dashboard')
  const summary = element('div', 'ndvi-summary-grid')
  for (const item of INVESTIGATION_PREVIEW.ndvi.summary) summary.append(metricCard({ ...item, detail: 'dado demonstrativo' }, true))

  const chartCard = element('article', 'dashboard-card chart-card chart-card--featured')
  const header = element('div', 'card-heading-row')
  const copy = element('div')
  copy.append(
    element('span', 'card-kicker', 'Série pareada'),
    element('h2', '', 'Trajetória NDVI'),
    element('p', 'card-description', 'Duas séries demonstrativas nas mesmas datas, com pontos navegáveis e tabela equivalente.'),
  )
  const legend = element('div', 'chart-legend')
  for (const [className, label] of [['legend-target', 'Grão 4.0'], ['legend-reference', 'Grão Convencional']]) {
    const item = element('span', '')
    item.append(element('i', className), document.createTextNode(label))
    legend.append(item)
  }
  header.append(copy, legend)
  chartCard.append(header, ndviChart(), sourceLine('Fonte mockada: ndvi_metadata.csv'))
  panel.append(summary, chartCard, ndviTable())
  return panel
}

function textListPanel(title, kicker, items) {
  const panel = element('article', 'dashboard-card')
  panel.append(element('span', 'card-kicker', kicker), element('h2', '', title))
  const list = element('ul', 'detail-list')
  for (const item of items) list.append(element('li', '', item))
  panel.append(list)
  return panel
}

export function createInvestigationPreview(onNavigate) {
  const view = element('section', 'page-view')
  view.dataset.page = 'investigation'

  const heading = element('div', 'page-heading')
  const headingCopy = element('div')
  headingCopy.append(
    element('span', 'eyebrow', '03 · Investigar'),
    element('h1', '', 'Investigação agrícola'),
    element('p', 'page-heading__description', 'Uma visão antecipada da organização do relatório, sem Gemini e sem evidências calculadas.'),
  )
  const actions = element('div', 'heading-actions')
  const newComparison = element('button', 'button button--secondary', 'Nova comparação')
  newComparison.type = 'button'
  newComparison.addEventListener('click', () => onNavigate('comparison'))
  const download = element('button', 'button button--ghost', 'Relatório indisponível na prévia')
  download.type = 'button'
  download.disabled = true
  actions.append(newComparison, download)
  heading.append(headingCopy, actions)

  const metrics = element('div', 'metric-grid metric-grid--four')
  metrics.append(...INVESTIGATION_PREVIEW.highlights.map((item) => metricCard(item)))

  const tabs = element('div', 'result-tabs')
  tabs.setAttribute('role', 'tablist')
  tabs.setAttribute('aria-label', 'Seções da investigação com dados mocados')
  const panelHost = element('div', 'result-panel')

  const panelFactories = {
    overview: () => overviewPanel(() => selectTab('soil')),
    soil: soilPanel,
    evidence: evidencePanel,
    chart: chartPanel,
    methods: () => textListPanel('Como a investigação será construída', 'Métodos previstos', [
      'Ferramentas determinísticas recebem apenas IDs e filtros normalizados.',
      'Cada número aponta para uma evidência e para seus arquivos-fonte.',
      'O Gemini organiza a síntese, mas não calcula métricas.',
      'O frontend formata contratos prontos; não reproduz cálculos analíticos.',
    ]),
    limitations: () => textListPanel('O que os dados não permitem concluir', 'Limitações obrigatórias', [
      'A prévia atual contém somente dados mocados e não representa uma análise real.',
      'As amostras de solo não pertencem a talhões específicos.',
      'Sem coordenada, data ou profundidade, não há mapa, tendência temporal ou perfil de camadas do solo.',
      'Unidades e faixas agronômicas não documentadas não podem ser inventadas.',
      'Diferenças observadas não comprovam causalidade ou produtividade.',
    ]),
  }

  function selectTab(tabId) {
    for (const button of tabs.querySelectorAll('button')) {
      const selected = button.dataset.tab === tabId
      button.classList.toggle('result-tab--active', selected)
      button.setAttribute('aria-selected', String(selected))
      button.tabIndex = selected ? 0 : -1
    }
    panelHost.replaceChildren(panelFactories[tabId]())
  }

  for (const tab of INVESTIGATION_TABS) {
    const button = element('button', 'result-tab', tab.label)
    button.type = 'button'
    button.dataset.tab = tab.id
    button.setAttribute('role', 'tab')
    button.addEventListener('click', () => selectTab(tab.id))
    tabs.append(button)
  }
  selectTab('overview')

  view.append(previewNotice(), heading, metrics, tabs, panelHost)
  return view
}
