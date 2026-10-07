export const PREVIEW_NOTICE = Object.freeze({
  label: 'Prévia · dados mocados',
  detail: 'Conteúdo exclusivamente visual. Nenhum valor desta tela veio do backend ou do Gemini.',
})

export const PREVIEW_FIELDS = Object.freeze([
  { id: 'grain-digital', label: 'Grão 4.0', type: 'Digital' },
  { id: 'grain-conventional', label: 'Grão Convencional', type: 'Convencional' },
  { id: 'silage-digital', label: 'Silagem 4.0', type: 'Digital' },
  { id: 'silage-conventional', label: 'Silagem Convencional', type: 'Convencional' },
])

export const COMPARISON_PREVIEW = Object.freeze({
  period: 'Safra 2024/25',
  periods: ['Safra 2024/25', 'Período completo'],
  targetId: 'grain-digital',
  referenceId: 'grain-conventional',
  score: 82,
  pairedDates: 33,
  operations: 2,
  soilSamples: 8,
  question: 'O que as análises de solo indicam sobre o contexto da área e quais sinais aparecem na execução de correção e no vigor dos talhões Grão 4.0 e Grão Convencional?',
  criteria: [
    { label: 'Mesma finalidade', status: 'Atendido' },
    { label: 'Manejos distintos', status: 'Atendido' },
    { label: 'NDVI pareado', status: '33 datas' },
    { label: 'Operações em comum', status: '2 disponíveis' },
  ],
  availableAnalyses: [
    { id: 'soil', label: 'Solo', detail: '8 amostras · prioridade', active: true },
    { id: 'ndvi', label: 'NDVI', detail: '33 datas pareadas', active: true },
    { id: 'application', label: 'Aplicação', detail: '2 operações', active: true },
    { id: 'population', label: 'População', detail: 'mapa disponível', active: false },
  ],
})

export const INVESTIGATION_TABS = Object.freeze([
  { id: 'overview', label: 'Visão geral' },
  { id: 'soil', label: 'Solo' },
  { id: 'evidence', label: 'Evidências' },
  { id: 'chart', label: 'Gráfico NDVI' },
  { id: 'methods', label: 'Métodos' },
  { id: 'limitations', label: 'Limitações' },
])

const SOIL_METRICS = Object.freeze([
  {
    id: 'ph',
    family: 'acidity',
    label: 'pH CaCl₂',
    unit: 'unidade não documentada',
    valid: 8,
    group1: { min: '5,0', q1: '5,2', median: '5,5', q3: '5,8', max: '6,1', plot: [14, 29, 50, 71, 88] },
    group2: { min: '4,9', q1: '5,1', median: '5,4', q3: '5,7', max: '6,0', plot: [8, 24, 43, 65, 82] },
    comparison: { group1: '5,52', group2: '5,42', delta: '−0,10', widths: [88, 84] },
  },
  {
    id: 'organic-matter',
    family: 'fertility',
    label: 'Matéria orgânica',
    unit: 'unidade não documentada',
    valid: 8,
    group1: { min: '4,8', q1: '5,7', median: '6,4', q3: '7,1', max: '8,2', plot: [12, 34, 52, 70, 94] },
    group2: { min: '4,2', q1: '5,1', median: '5,9', q3: '6,6', max: '7,4', plot: [6, 24, 45, 63, 84] },
    comparison: { group1: '6,62', group2: '6,02', delta: '−0,60', widths: [88, 80] },
  },
  {
    id: 'ctc',
    family: 'bases',
    label: 'CTC',
    unit: 'unidade não documentada',
    valid: 8,
    group1: { min: '36,2', q1: '41,8', median: '45,1', q3: '49,6', max: '54,4', plot: [10, 34, 51, 73, 94] },
    group2: { min: '33,9', q1: '38,4', median: '41,0', q3: '45,3', max: '50,2', plot: [4, 25, 40, 61, 82] },
    comparison: { group1: '45,50', group2: '41,26', delta: '−4,24', widths: [91, 83] },
  },
  {
    id: 'base-saturation',
    family: 'bases',
    label: 'Saturação por bases',
    unit: 'unidade não documentada',
    valid: 7,
    group1: { min: '55,1', q1: '61,3', median: '67,0', q3: '72,6', max: '78,2', plot: [9, 32, 53, 74, 94] },
    group2: { min: '49,8', q1: '56,2', median: '61,0', q3: '66,4', max: '72,1', plot: [3, 25, 43, 63, 82] },
    comparison: { group1: '67,20', group2: '61,05', delta: '−6,15', widths: [90, 82] },
  },
])

export const INVESTIGATION_PREVIEW = Object.freeze({
  title: 'Sinais de vigor e execução no contexto geral da área',
  strength: 'Evidência moderada',
  summary: 'Esta é uma composição demonstrativa. Em uma investigação real, o texto será produzido somente depois que as ferramentas determinísticas calcularem e validarem as evidências.',
  highlights: [
    { label: 'Gap médio de NDVI', value: '−0,025', detail: 'alvo − referência' },
    { label: 'População estimada', value: '61,3 mil/ha', detail: 'talhão analisado' },
    { label: 'Conformidade', value: '58,0%', detail: 'aplicação ilustrativa' },
    { label: 'Amostras de solo', value: '8', detail: 'escopo geral' },
  ],
  soil: {
    quality: [
      { label: 'Amostras válidas', value: '8', detail: 'de 8 recebidas', tone: 'primary' },
      { label: 'Completude', value: '94%', detail: 'valores disponíveis', tone: 'success' },
      { label: 'Pares válidos', value: '8', detail: 'Conjunto 1 × 2', tone: 'primary' },
      { label: 'Alertas', value: '2', detail: 'unidade e escopo', tone: 'warning' },
    ],
    families: [
      { id: 'all', label: 'Todas as famílias' },
      { id: 'acidity', label: 'Acidez' },
      { id: 'fertility', label: 'Fertilidade' },
      { id: 'bases', label: 'Bases' },
    ],
    metrics: SOIL_METRICS,
    texture: {
      average: { sand: 35, silt: 24, clay: 41 },
      samples: [
        { id: 'A01', sand: 42, silt: 23, clay: 35 },
        { id: 'A02', sand: 36, silt: 25, clay: 39 },
        { id: 'A03', sand: 31, silt: 26, clay: 43 },
        { id: 'A04', sand: 28, silt: 22, clay: 50 },
      ],
    },
  },
  ndvi: {
    summary: [
      { label: 'Datas pareadas', value: '33' },
      { label: 'Média do alvo', value: '0,612' },
      { label: 'Média da referência', value: '0,637' },
      { label: 'Gap', value: '−0,025' },
    ],
    points: [
      { date: '10 set', target: '0,42', reference: '0,44', x: 54, targetY: 174, referenceY: 166 },
      { date: '24 set', target: '0,49', reference: '0,51', x: 142, targetY: 146, referenceY: 138 },
      { date: '08 out', target: '0,47', reference: '0,50', x: 230, targetY: 154, referenceY: 142 },
      { date: '22 out', target: '0,61', reference: '0,64', x: 318, targetY: 99, referenceY: 87 },
      { date: '05 nov', target: '0,58', reference: '0,61', x: 406, targetY: 111, referenceY: 99 },
      { date: '19 nov', target: '0,69', reference: '0,71', x: 494, targetY: 67, referenceY: 59 },
      { date: '03 dez', target: '0,65', reference: '0,68', x: 582, targetY: 83, referenceY: 71 },
      { date: '17 dez', target: '0,73', reference: '0,75', x: 670, targetY: 51, referenceY: 43 },
    ],
  },
  evidence: [
    { id: 'EV-NDVI-001', label: 'NDVI pareado', source: 'ndvi_metadata.csv', value: '33 observações' },
    { id: 'EV-APP-001', label: 'Execução de calagem', source: 'LAYER_MAP_FERTILIZATION.csv', value: '58,0% × 97,4%' },
    { id: 'EV-SOIL-001', label: 'Contexto de solo', source: 'soil_analysis.csv', value: '8 amostras' },
  ],
})
