import { element } from './dom.js'

const NEXT_STEP_STATUS = {
  continue_now: ['Pode continuar agora', 'next-step-status--ready'],
  needs_data: ['Depende de novos dados', 'next-step-status--data'],
  needs_tooling: ['Depende de nova ferramenta', 'next-step-status--tooling'],
}

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
    if (evidence.scope === 'dataset') details.append(element('p', 'chart-hint', 'Amostras do pacote importado, sem associação aos talhões selecionados.'))
    item.append(details)
    list.append(item)
  }
  section.append(list)
  return section
}

export function createReportCards(report, evidence, { showEvidence = true } = {}) {
  const evidenceById = new Map(evidence.map((item) => [item.evidence_id, item]))
  return [
    { key: 'findings', title: 'Principais insights', description: 'As leituras que sustentam a resposta, já interpretadas para a pergunta feita.', heading: 'title', body: 'explanation', empty: 'Os dados não sustentam uma conclusão adicional neste recorte.' },
    { key: 'recommendations', title: 'Próximos passos', description: 'Cada item informa se a investigação pode continuar agora ou se depende de novos dados ou ferramentas.', heading: 'action', body: 'reason', empty: 'Não há um próximo passo sustentado pelas evidências disponíveis.' },
  ].map(({ key, title, description, heading, body, empty }) => {
    const section = element('section', 'report-section')
    section.dataset.section = key
    section.setAttribute('aria-labelledby', `report-${key}-title`)
    const headingNode = element('h2', '', title)
    headingNode.id = `report-${key}-title`
    section.append(headingNode, element('p', 'report-section__description', description))
    const items = report[key]
    if (!items.length) {
      section.append(element('p', 'status-message', empty))
      return section
    }
    const list = element('ol', 'report-card-list')
    items.forEach((item) => {
      const row = element('li')
      const card = element('article', 'dashboard-card report-card')
      if (key === 'recommendations') {
        const [label, className] = NEXT_STEP_STATUS[item.availability] ?? NEXT_STEP_STATUS.continue_now
        card.append(element('span', `next-step-status ${className}`, label))
      }
      card.append(element('h3', '', item[heading]))
      if (key === 'recommendations') card.append(element('strong', 'recommendation-reason-label', 'Por que este é o próximo passo'))
      card.append(element('p', 'report-card__text', item[body]))
      if (key === 'recommendations' && item.suggested_question) {
        const question = element('div', 'suggested-question')
        question.append(element('span', 'card-kicker', 'Pergunta que já pode ser investigada'),
          element('p', '', item.suggested_question))
        card.append(question)
      }
      if (showEvidence) card.append(relatedEvidence(item.evidence_ids, evidenceById))
      row.append(card)
      list.append(row)
    })
    section.append(list)
    return section
  })
}
