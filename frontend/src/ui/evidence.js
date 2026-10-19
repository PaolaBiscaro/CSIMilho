import { element, formatValue, table } from './dom.js'

const METRICS = {
  mean_gap: 'NDVI médio', initial_mean_gap: 'Condição inicial · NDVI',
  population_per_ha: 'População por hectare', application_compliance: 'Conformidade de aplicação',
}
const unit = (value) => value ?? 'unidade não documentada'

function addCounts(card, evidence) {
  const list = element('dl', 'evidence-counts')
  const items = [['Observações', evidence.observation_count]]
  if ('paired_dates' in evidence) items.push(['Datas pareadas', evidence.paired_dates])
  if ('sample_count' in evidence) items.push(['Amostras no dataset', evidence.sample_count])
  for (const [key, label] of [['target_rows', 'Alvo'], ['reference_rows', 'Referência']]) {
    if (evidence[key]) items.push([`${label} · linhas válidas`, evidence[key].valid], [`${label} · linhas descartadas`, evidence[key].discarded])
  }
  for (const [label, value] of items) {
    const item = element('div')
    item.append(element('dt', '', label), element('dd', '', formatValue(value)))
    list.append(item)
  }
  card.append(list)
}

function soilValues(card, evidence) {
  card.append(element('p', 'soil-summary', 'Escopo geral do dataset: sem vínculo documentado com talhão, coordenada, data ou profundidade. Conjunto 1 e Conjunto 2 não representam alvo e referência.'))
  if (evidence.measurement_group) {
    const group = evidence.measurement_group === 'group_1' ? 'Conjunto 1' : 'Conjunto 2'
    card.append(element('p', 'badge', group))
    if (!evidence.metrics.length) card.append(element('p', 'status-message', 'Nenhuma métrica descritiva disponível.'))
    else card.append(table(`Estatísticas de solo · ${group} · ${evidence.evidence_id}`,
      ['Métrica', 'Unidade', 'Válidas', 'Ausentes', 'Média', 'Mín.', 'Q1', 'Mediana', 'Q3', 'Máx.', 'Fontes'],
      evidence.metrics.map((item) => [item.name, unit(item.unit), formatValue(item.valid_n), formatValue(item.missing_n),
        ...['mean', 'min', 'q1', 'median', 'q3', 'max'].map((key) => formatValue(item[key])), item.source_files.join(', ')])))
  } else if (evidence.comparison === 'group_2_minus_group_1') {
    card.append(element('p', '', 'Conjunto 1 × Conjunto 2 · delta = Conjunto 2 − Conjunto 1.'))
    if (!evidence.metrics.length) card.append(element('p', 'status-message', 'Nenhuma métrica pareada disponível.'))
    for (const item of evidence.metrics) {
      const details = element('details', 'soil-details')
      details.append(element('summary', '', `${item.name} · ${formatValue(item.valid_n)} pares válidos · delta mediano ${formatValue(item.median_delta)} · ${unit(item.unit)}`),
        table(`Valores pareados · ${item.name} · ${unit(item.unit)} · ${evidence.evidence_id}`,
          ['Amostra', 'Conjunto 1', 'Conjunto 2', 'Delta 2 − 1'],
          item.pairs.map((pair) => [pair.sample_id, formatValue(pair.group_1), formatValue(pair.group_2), formatValue(pair.delta)])),
        element('p', 'chart-source', `Fonte: ${item.source_files.join(', ')}`))
      if (!item.pairs.length) details.append(element('p', 'status-message', 'Não há pares válidos para esta métrica.'))
      card.append(details)
    }
  }
}

export function createEvidencePanel(evidence, fields = []) {
  const panel = element('section', 'evidence-panel')
  panel.append(element('h2', '', 'Evidências'), element('p', 'card-description',
    'Valores retornados pelas ferramentas analíticas. Dados ausentes aparecem como Indisponível; nenhum valor é recalculado nesta tela.'))
  if (!evidence.length) {
    panel.append(element('p', 'status-message', 'Nenhuma evidência disponível nesta investigação.'))
    return panel
  }
  const fieldLabel = (id) => {
    if (id == null) return 'Indisponível'
    const field = fields.find((item) => item.field_id === id)
    return field?.label ? `${field.label} (${id})` : id
  }
  for (const item of evidence) {
    const card = element('article', 'dashboard-card evidence-card')
    card.dataset.evidenceId = item.evidence_id
    card.append(element('h3', '', item.evidence_id))
    if (item.scope === 'dataset') soilValues(card, item)
    else {
      card.append(element('p', 'card-description', `Alvo: ${fieldLabel(item.target_field_id)} · Referência: ${fieldLabel(item.reference_field_id)}`),
        table(`Valores consolidados · ${item.evidence_id}`, ['Métrica', 'Alvo', 'Referência', 'Diferença', 'Unidade'],
          [[METRICS[item.metric] ?? item.metric ?? 'Indisponível', formatValue(item.target_value), formatValue(item.reference_value),
            formatValue(item.difference), unit(item.unit)]]))
      if (item.metric === 'application_compliance') card.append(element('p', 'chart-hint',
        'Alvo e referência em %. Diferença em pontos percentuais (alvo − referência).'))
      else card.append(element('p', 'chart-hint', 'Diferença: alvo − referência, conforme retornado pelo backend.'))
      if (Array.isArray(item.criteria)) {
        card.append(element('p', '', `Comparabilidade: ${formatValue(item.score)} de ${formatValue(item.max_score)} critérios atendidos.`),
          table(`Critérios de comparabilidade · ${item.evidence_id}`, ['Critério', 'Resultado', 'Detalhe'],
            item.criteria.map((criterion) => [criterion.label, criterion.satisfied == null ? 'Indisponível' : criterion.satisfied ? 'Atendido' : 'Não atendido', criterion.detail])))
      }
    }
    addCounts(card, item)
    card.append(element('p', 'chart-source', `Fonte: ${item.source_files.join(', ')}`))
    for (const warning of item.warnings ?? []) card.append(element('p', 'chart-hint', warning))
    panel.append(card)
  }
  return panel
}
