import { element } from './dom.js'

function relatedEvidence(ids, evidenceById) {
  const section = element('div', 'related-evidence')
  section.append(element('p', 'card-kicker', 'Evidências relacionadas'))
  const list = element('ul', 'related-evidence__list')
  for (const id of ids) {
    // The API adapter rejects missing or ambiguous references before COMPLETED.
    const evidence = evidenceById.get(id)
    const item = element('li')
    const details = element('details', 'evidence-reference')
    details.dataset.evidenceId = id
    details.append(element('summary', '', id),
      element('p', '', evidence.method),
      element('p', 'chart-source', `Fonte: ${evidence.source_files.join(', ')}`))
    if (evidence.scope === 'dataset') details.append(element('p', 'chart-hint', 'Escopo geral do dataset; sem vínculo documentado com os talhões selecionados.'))
    item.append(details)
    list.append(item)
  }
  section.append(list)
  return section
}

export function createReportCards(report, evidence) {
  const evidenceById = new Map(evidence.map((item) => [item.evidence_id, item]))
  return [
    { key: 'findings', title: 'Achados', label: 'Achado', heading: 'title', body: 'explanation', empty: 'Nenhum achado foi incluído neste relatório.' },
    { key: 'recommendations', title: 'Recomendações', label: 'Recomendação', heading: 'action', body: 'reason', empty: 'Nenhuma recomendação foi incluída neste relatório.' },
  ].map(({ key, title, label, heading, body, empty }) => {
    const section = element('section', 'report-section')
    section.dataset.section = key
    section.setAttribute('aria-labelledby', `report-${key}-title`)
    const headingNode = element('h2', '', title)
    headingNode.id = `report-${key}-title`
    section.append(headingNode)
    const items = report[key]
    if (!items.length) {
      section.append(element('p', 'status-message', empty))
      return section
    }
    const list = element('ol', 'report-card-list')
    items.forEach((item, index) => {
      const row = element('li')
      const card = element('article', 'dashboard-card report-card')
      card.append(element('span', 'eyebrow', `${label} ${index + 1}`), element('h3', '', item[heading]))
      if (key === 'recommendations') card.append(element('strong', 'recommendation-reason-label', 'Justificativa'))
      card.append(element('p', 'report-card__text', item[body]), relatedEvidence(item.evidence_ids, evidenceById))
      row.append(card)
      list.append(row)
    })
    section.append(list)
    return section
  })
}
