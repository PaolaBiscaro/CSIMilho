import fixture from './analytics-result.json'

export function investigationEnvelope() {
  const evidence = structuredClone(fixture.comparisons['103144:103145'].ndvi)
  return {
    turn_id: '11111111-1111-4111-8111-111111111111',
    intent: { intent: 'investigative_query', response_kind: 'investigation_report', reason: 'hypothesis_or_relationship_request', requires_tools: true, requires_report: true, uses_conversation_context: false },
    response: {
      kind: 'investigation_report', status: 'partial', evidence: [evidence],
      chart_data: { ndvi: evidence, field_ndvi: null, ndvi_tests: [], ndvi_changes: [], operation_ndvi: [], soil_summaries: [], soil_groups: [], soil_tests: [] },
      report: {
        question: 'Como o vigor dos dois talhões se comportou?', scope_summary: 'Comparação observacional dos talhões selecionados.',
        executive_answer: { status: 'indicative', headline: 'O vigor apresentou comportamento diferente', answer: 'A série pareada mostra um contraste persistente entre os talhões no período observado.', confidence: 'moderate', main_caveat: 'A diferença observada não demonstra a causa do comportamento.', evidence_ids: [evidence.evidence_id] },
        insights: [{ claim: 'O contraste de vigor se manteve no período analisado', analytical_method: 'Comparação pareada de NDVI', evidence_summary: 'As datas comuns foram comparadas pelo módulo analítico.', interpretation: 'O comportamento indica trajetórias distintas nos dois talhões.', uncertainty: 'A série não isola efeitos de manejo, clima ou solo.', evidence_ids: [evidence.evidence_id], chart_ids: ['chart-ndvi-comparison'] }],
        charts: [{ chart_id: 'chart-ndvi-comparison', title: 'Trajetória pareada de vigor', takeaway: 'Os talhões seguiram trajetórias distintas.', evidence_ids: [evidence.evidence_id] }],
        unanswered_parts: [{ gap_type: 'missing_data', question_part: 'Causa da diferença', explanation: 'Os dados não isolam a causa.', requirement: 'Desenho experimental com variáveis de controle.' }],
        limitations: [{ limitation_type: 'scientific_limit', title: 'Dados observacionais', explanation: 'Associação não comprova causalidade.', impact: 'A causa não pode ser afirmada.', requirement: 'Desenho experimental.' }],
        field_recommendations: [],
        technical_appendix: { hypotheses: [{ hypothesis_id: 'ndvi', question: 'Há diferença de vigor?', null_hypothesis: 'Não há diferença.', alternative_hypothesis: 'Há diferença.', method: 'Teste pareado', status: 'executed', sample_size: 3, statistic_name: 'W', statistic_value: 2, p_value: 0.25, effect_size_name: null, effect_size_value: null, evidence_ids: [evidence.evidence_id], source_files: ['ndvi_metadata.csv'], blocker: null }], methods_summary: ['Teste pareado'], source_files: ['ndvi_metadata.csv'] },
      },
    },
  }
}

export function descriptiveEnvelope() {
  return { turn_id: '22222222-2222-4222-8222-222222222222', intent: { response_kind: 'descriptive' }, response: { kind: 'descriptive', status: 'complete', answer: 'O pacote possui uma série temporal válida.', insights: [{ title: 'Série disponível', explanation: 'As observações válidas foram resumidas.', evidence_ids: ['EV-1'], chart_ids: [] }], gaps: [] } }
}
