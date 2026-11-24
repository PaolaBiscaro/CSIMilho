import { state, startNewComparison } from '../state.js'
import { requestChatReport } from '../api.js'
import { element, formatValue, table } from './dom.js'
import { createEvidencePanel } from './evidence.js'
import { createInvestigationNdviPanel, createInvestigationSoilPanel } from './investigation-charts.js'

const CONFIDENCE = { low: 'baixa', moderate: 'moderada', high: 'alta' }
const STATUS = { conclusive: 'Conclusão sustentada', indicative: 'Sinal indicativo', inconclusive: 'Resultado inconclusivo', not_analyzable: 'Não foi possível analisar' }

function gapsPanel(items, title = 'O que não pôde ser respondido') {
  if (!items?.length) return null
  const section = element('section', 'dashboard-card unanswered-card')
  section.append(element('span', 'card-kicker', 'Limites da resposta'), element('h2', '', title))
  for (const item of items) {
    const card = element('article', 'answer-gap')
    card.append(element('h3', '', item.question_part ?? item.title), element('p', '', item.explanation),
      element('p', 'gap-requirement', `Para responder: ${item.requirement}`))
    section.append(card)
  }
  return section
}

function historyPanel() {
  if (state.conversation.length < 2) return null
  const details = element('details', 'conversation-history')
  details.append(element('summary', '', `Perguntas anteriores (${state.conversation.length - 1})`))
  const list = element('ol', 'conversation-history__list')
  state.conversation.slice(0, -1).forEach((turn) => {
    const item = element('li')
    const question = turn.response?.report?.question ?? 'Pergunta anterior'
    const answer = turn.response?.report?.executive_answer?.answer ?? turn.response?.answer ?? 'Resposta registrada.'
    item.append(element('strong', '', question), element('p', '', answer)); list.append(item)
  })
  details.append(list)
  return details
}

function catalogView(response) {
  const panel = element('div', 'result-panel investigation-answer')
  const answer = element('section', 'dashboard-card executive-answer')
  answer.append(element('span', 'eyebrow answer-label', 'Resposta'),
    element('h1', '', response.kind === 'data_catalog' ? 'Dados disponíveis' : 'O que o FarmLab consegue analisar'),
    element('p', 'report-summary', response.answer))
  panel.append(answer)
  const grid = element('section', 'report-card-list catalog-grid')
  ;(response.assets ?? response.capabilities ?? []).forEach((item) => {
    const card = element('article', 'report-card')
    card.append(element('h2', '', item.name ?? item.title), element('p', '', item.description))
    if ('record_count' in item) card.append(element('p', 'catalog-meta', `${formatValue(item.record_count)} registros válidos`))
    if (item.availability) {
      const labels = { available_now: 'Disponível agora', needs_data: 'Precisa de dados', needs_tooling: 'Precisa de ferramenta' }
      card.append(element('span', `badge availability--${item.availability}`, labels[item.availability] ?? item.availability))
    }
    if (item.limitation) card.append(element('p', 'confidence-explanation', item.limitation))
    grid.append(card)
  })
  panel.append(grid)
  const gaps = gapsPanel(response.gaps); if (gaps) panel.append(gaps)
  return panel
}

function descriptiveView(response) {
  const panel = element('div', 'result-panel investigation-answer')
  const answer = element('section', 'dashboard-card executive-answer')
  answer.append(element('span', 'eyebrow answer-label', 'Resposta'), element('h1', '', 'O que os dados mostram'),
    element('p', 'report-summary', response.answer))
  panel.append(answer)
  if (response.insights?.length) {
    const grid = element('section', 'report-card-list insight-grid')
    response.insights.forEach((item) => {
      const card = element('article', 'report-card insight-card')
      card.append(element('h2', '', item.title), element('p', '', item.explanation)); grid.append(card)
    })
    panel.append(grid)
  }
  const gaps = gapsPanel(response.gaps); if (gaps) panel.append(gaps)
  return panel
}

function investigationView(response, fields) {
  const report = response.report; const executive = report.executive_answer
  const panel = element('div', 'result-panel investigation-answer')
  const question = element('section', 'investigation-question')
  question.append(element('span', 'card-kicker', 'Pergunta analisada'), element('p', '', report.question))
  const answer = element('section', 'dashboard-card executive-answer')
  answer.append(element('span', 'eyebrow answer-label', 'Resposta'), element('h1', '', executive.headline),
    element('p', 'report-summary', executive.answer))
  const metadata = element('div', 'report-metadata')
  metadata.append(element('span', 'badge', STATUS[executive.status] ?? executive.status),
    element('span', 'badge', `Confiança ${CONFIDENCE[executive.confidence] ?? executive.confidence}`))
  answer.append(metadata, element('p', 'confidence-explanation', executive.main_caveat))
  panel.append(question, answer)
  const chartData = response.chart_data ?? {}; let charts = []
  const hasCharts = chartData.ndvi || chartData.field_ndvi || (chartData.soil_summaries?.length ?? 0) || (chartData.soil_groups?.length ?? 0)
  const host = element('section', 'answer-visualizations')
  if (hasCharts) {
    const narrative = element('section', 'chart-narratives')
    ;(report.charts ?? []).forEach((item) => {
      const card = element('article', 'chart-narrative')
      card.append(element('h3', '', item.title), element('p', '', item.takeaway)); narrative.append(card)
    })
    if (narrative.childElementCount) panel.append(narrative)
    panel.append(host)
  }
  panel.mountCharts = () => {
    if (!hasCharts || charts.length) return
    if (chartData.ndvi || chartData.field_ndvi) charts.push(createInvestigationNdviPanel(chartData, fields))
    if ((chartData.soil_summaries?.length ?? 0) || (chartData.soil_groups?.length ?? 0)) charts.push(createInvestigationSoilPanel(chartData))
    host.replaceChildren(...charts); charts.forEach((chart) => chart.mount?.())
  }
  const gaps = gapsPanel(report.unanswered_parts); if (gaps) panel.append(gaps)
  panel.dispose = () => { charts.forEach((chart) => chart.dispose?.()); charts = []; host.replaceChildren() }
  return panel
}

function technicalView(response, fields) {
  const panel = element('div', 'result-panel investigation-technical'); const report = response.report
  const heading = element('section', 'technical-heading')
  heading.append(element('span', 'eyebrow', 'Rastreabilidade'), element('h2', '', 'Detalhes técnicos'),
    element('p', 'card-description', 'Testes, métodos, fontes, evidências e limites usados para chegar à resposta.'))
  panel.append(heading)
  const appendix = report.technical_appendix
  const inputs = (item) => [
    item.source_files?.length ? `Arquivos: ${item.source_files.join(', ')}` : 'Arquivos não disponíveis',
    item.sample_size == null ? null : `n = ${formatValue(item.sample_size)}`,
  ].filter(Boolean).join(' · ')
  const outputs = (item) => [
    item.statistic_name && item.statistic_value != null ? `${item.statistic_name} = ${formatValue(item.statistic_value)}` : null,
    item.effect_size_name && item.effect_size_value != null ? `${item.effect_size_name} = ${formatValue(item.effect_size_value)}` : null,
    item.evidence_ids?.length ? `Evidências: ${item.evidence_ids.join(', ')}` : null,
  ].filter(Boolean).join(' · ') || 'Nenhum resultado calculado'
  const pAssessment = (item) => {
    if (item.status !== 'executed') return 'Não calculado: método bloqueado'
    if (item.p_value == null) return 'Não se aplica a este método'
    if (item.sample_size != null && item.sample_size < 5) return 'Baixa sustentação: amostra muito pequena'
    return 'Interpretável no teste executado; não demonstra causalidade'
  }
  panel.append(table('Métodos executados', ['Pergunta técnica', 'Método', 'Inputs', 'Outputs', 'p-valor', 'Adequação do p-valor'],
    appendix.hypotheses.map((item) => [item.question, item.method, inputs(item), outputs(item),
      formatValue(item.p_value), pAssessment(item)])))
  if (response.evidence?.length) panel.append(createEvidencePanel(response.evidence, fields))
  for (const [title, items] of [['Métodos utilizados', appendix.methods_summary], ['Arquivos utilizados', appendix.source_files]]) {
    const card = element('section', 'dashboard-card'); const list = element('ul', 'detail-list')
    items.forEach((item) => list.append(element('li', '', item))); card.append(element('h3', '', title), list); panel.append(card)
  }
  if (report.limitations.length) {
    const card = element('section', 'dashboard-card'); const list = element('ul', 'detail-list')
    report.limitations.forEach((item) => list.append(element('li', '', `${item.title}: ${item.explanation}`)))
    card.append(element('h3', '', 'Limitações da análise'), list); panel.append(card)
  }
  return panel
}

function tabbedInvestigation(response, fields) {
  const wrapper = element('div', 'investigation-report'); const tabs = element('div', 'result-tabs')
  tabs.setAttribute('role', 'tablist'); tabs.setAttribute('aria-label', 'Seções do relatório')
  const panels = { answer: investigationView(response, fields), technical: technicalView(response, fields) }
  const definitions = [['answer', 'Resposta'], ['technical', 'Rastreabilidade técnica']]; const host = element('div', 'investigation-panels')
  let active = null
  function select(id) {
    if (active === id) return
    if (active === 'answer') panels.answer.dispose?.()
    definitions.forEach(([key]) => {
      panels[key].hidden = key !== id
      const button = tabs.querySelector(`[data-tab="${key}"]`); button.setAttribute('aria-selected', String(key === id)); button.tabIndex = key === id ? 0 : -1
      button.classList.toggle('result-tab--active', key === id)
    })
    if (id === 'answer') panels.answer.mountCharts?.()
    active = id
  }
  definitions.forEach(([id, label], index) => {
    const button = element('button', 'result-tab', label); button.type = 'button'; button.dataset.tab = id; button.setAttribute('role', 'tab')
    button.addEventListener('click', () => select(id)); button.addEventListener('keydown', (event) => {
      const next = event.key === 'ArrowRight' ? (index + 1) % definitions.length : event.key === 'ArrowLeft' ? (index + definitions.length - 1) % definitions.length : null
      if (next !== null) { event.preventDefault(); select(definitions[next][0]); tabs.children[next].focus() }
    }); tabs.append(button); panels[id].setAttribute('role', 'tabpanel'); host.append(panels[id])
  })
  const technicalShortcut = element('button', 'button button--secondary technical-shortcut', 'Abrir rastreabilidade técnica')
  technicalShortcut.type = 'button'
  technicalShortcut.addEventListener('click', () => {
    select('technical')
    tabs.querySelector('[data-tab="technical"]')?.focus()
    tabs.scrollIntoView?.({ block: 'start', behavior: 'smooth' })
  })
  panels.answer.append(technicalShortcut)
  wrapper.append(tabs, host); wrapper.dispose = () => panels.answer.dispose?.(); select('answer'); return wrapper
}

export function createInvestigationResult(onNavigate) {
  const result = state.investigation; const view = element('section', 'page-view investigation-result'); view.dataset.page = 'investigation'
  let content
  if (!result) {
    content = element('section', 'dashboard-card empty-state')
    content.append(element('h1', '', 'Nenhuma pergunta respondida'), element('p', '', 'Envie uma pergunta sobre o pacote importado.'))
  } else if (result.response.kind === 'investigation_report') content = tabbedInvestigation(result.response, state.dataset?.fields ?? [])
  else if (result.response.kind === 'descriptive') content = descriptiveView(result.response)
  else if (['data_catalog', 'capability_catalog'].includes(result.response.kind)) content = catalogView(result.response)
  else {
    content = element('div', 'result-panel investigation-answer'); const card = element('section', 'dashboard-card executive-answer')
    card.append(element('span', 'eyebrow answer-label', 'Resposta'), element('h1', '', 'Esta pergunta não pode ser respondida'), element('p', 'report-summary', result.response.answer))
    content.append(card); const gaps = gapsPanel(result.response.gaps); if (gaps) content.append(gaps)
  }
  const history = historyPanel(); if (history) view.append(history); view.append(content)
  const actions = element('div', 'card-actions report-actions'); const again = element('button', 'button button--primary', 'Fazer outra pergunta')
  again.type = 'button'; again.addEventListener('click', () => { if (result && !startNewComparison()) return; onNavigate('comparison') }); actions.append(again)
  const status = element('p', 'status-message'); status.setAttribute('role', 'status'); let controller; let disposed = false
  if (result?.response.kind === 'investigation_report') {
    const download = element('button', 'button button--secondary', 'Baixar relatório HTML'); download.type = 'button'; download.dataset.action = 'download-report'
    download.addEventListener('click', async () => {
      if (download.disabled || disposed) return
      download.disabled = true; download.textContent = 'Preparando…'; controller = new AbortController()
      try {
        status.setAttribute('role', 'status')
        const blob = await requestChatReport(result.turn_id, { signal: controller.signal }); if (disposed) return
        const url = URL.createObjectURL(blob); const link = element('a')
        link.href = url; link.download = `farmlab-${result.turn_id}.html`; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000)
        status.textContent = 'Relatório baixado para consulta offline.'
      } catch (error) { if (!disposed) { status.setAttribute('role', 'alert'); status.textContent = error instanceof Error ? error.message : 'Não foi possível baixar o relatório.' } }
      finally { download.disabled = false; download.textContent = 'Baixar relatório HTML' }
    }); actions.append(download)
  }
  view.append(actions, status); view.dispose = () => { disposed = true; controller?.abort(); content?.dispose?.() }; return view
}
