import { ApiError, uploadDataset } from '../api.js'
import { AppState, resetAfterError, setDataset, setError, state, transitionTo } from '../state.js'

export const EXPECTED_FILES = Object.freeze([
  'fields.csv',
  'service_orders.csv',
  'ndvi_metadata.csv',
  'LAYER_MAP_PLANTING.csv',
  'LAYER_MAP_FERTILIZATION.csv',
  'service_orders_fields.csv',
  'soil_analysis.csv',
])

export function summarizeSelection(files) {
  const counts = new Map(EXPECTED_FILES.map((name) => [name, 0]))
  const unexpected = []
  for (const file of files) {
    if (!counts.has(file.name)) unexpected.push(file.name)
    else counts.set(file.name, counts.get(file.name) + 1)
  }
  const statuses = EXPECTED_FILES.map((name) => ({
    name,
    status: counts.get(name) === 0 ? 'missing' : counts.get(name) === 1 ? 'received' : 'invalid',
  }))
  return {
    statuses,
    unexpected,
    canSubmit: unexpected.length === 0 && statuses.every((item) => item.status === 'received'),
  }
}

function element(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

export function createUploadView() {
  let selectedFiles = []
  let serverFiles = null

  const section = element('section', 'upload-grid')
  section.setAttribute('aria-label', 'Importação dos dados')

  const form = element('form', 'surface upload-panel')
  const header = element('div', 'panel-heading')
  header.append(
    element('span', 'badge', 'Pacote obrigatório'),
    element('h2', '', 'Selecione os sete CSVs'),
    element('p', 'panel-heading__description', 'Você pode escolher todos de uma vez ou adicionar os arquivos em etapas.'),
  )

  const picker = element('label', 'file-picker')
  const pickerTitle = element('strong', '', 'Escolher arquivos')
  const pickerHint = element('span', '', 'Somente os nomes previstos · limite total de 100 MB')
  const input = document.createElement('input')
  input.type = 'file'
  input.name = 'files'
  input.accept = '.csv,text/csv'
  input.multiple = true
  input.setAttribute('aria-describedby', 'upload-status')
  picker.append(pickerTitle, pickerHint, input)

  const actions = element('div', 'upload-actions')
  const clearButton = element('button', 'button button--secondary', 'Limpar seleção')
  clearButton.type = 'button'
  const submitButton = element('button', 'button button--primary', 'Validar pacote')
  submitButton.type = 'submit'
  submitButton.disabled = true
  actions.append(clearButton, submitButton)

  const statusMessage = element('p', 'status-message', 'Nenhum arquivo selecionado.')
  statusMessage.id = 'upload-status'
  statusMessage.setAttribute('role', 'status')
  statusMessage.setAttribute('aria-live', 'polite')
  form.append(header, picker, actions, statusMessage)

  const inventory = element('aside', 'surface inventory-panel')
  const inventoryTitle = element('h2', '', 'Arquivos esperados')
  const fileList = element('ul', 'file-list')
  inventory.append(inventoryTitle, fileList)

  const resultSection = element('section', 'surface validation-result')
  resultSection.hidden = true
  const resultHeader = element('div', 'result-heading')
  const resultTitle = element('h2', '', 'Resultado da validação')
  const quality = element('strong', 'quality-score')
  resultHeader.append(resultTitle, quality)
  const fieldList = element('ul', 'field-list')
  const soilSummary = element('div', 'soil-summary')
  const issueContainer = element('div', 'issue-groups')
  const continueButton = element('button', 'button button--primary continue-button', 'Continuar')
  continueButton.type = 'button'
  continueButton.disabled = true
  continueButton.addEventListener('click', () => {
    section.dispatchEvent(new CustomEvent('farmlab:continue', { bubbles: true }))
  })
  resultSection.append(resultHeader, soilSummary, fieldList, issueContainer, continueButton)

  function currentStatuses() {
    if (serverFiles) return serverFiles.map(({ name, status }) => ({ name, status }))
    return summarizeSelection(selectedFiles).statuses
  }

  function renderFiles() {
    fileList.replaceChildren()
    for (const item of currentStatuses()) {
      const row = element('li', 'file-row')
      const name = element('span', 'file-row__name', item.name)
      const status = element('span', `file-status file-status--${item.status}`, statusLabel(item.status))
      row.append(name, status)
      fileList.append(row)
    }
  }

  function renderResult(payload) {
    resultSection.hidden = false
    quality.textContent = `${payload.quality_score}/100`
    quality.setAttribute('aria-label', `Qualidade do pacote: ${payload.quality_score} de 100`)
    fieldList.replaceChildren()
    const soil = payload.soil ?? { sample_count: 0, scope: 'dataset', measurement_groups: [] }
    const groupLabels = soil.measurement_groups.map((group) => (
      group === 'group_1' ? 'Conjunto 1' : group === 'group_2' ? 'Conjunto 2' : group
    ))
    soilSummary.replaceChildren(
      element('strong', '', 'Solo no contexto geral'),
      element(
        'span',
        '',
        `${soil.sample_count} amostra(s) válida(s) · ${groupLabels.join(' e ') || 'nenhum conjunto disponível'}`,
      ),
      element('small', '', 'As amostras não são associadas a talhões, datas ou profundidades.'),
    )
    for (const field of payload.fields ?? []) {
      const item = element('li', 'field-card')
      item.append(
        element('strong', '', field.label),
        element('span', '', `${field.purpose} · ${field.management}`),
      )
      fieldList.append(item)
    }
    issueContainer.replaceChildren(
      createIssueGroup('Erros', payload.errors ?? [], 'error'),
      createIssueGroup('Avisos', payload.warnings ?? [], 'warning'),
    )
    continueButton.disabled = !['ready', 'ready_with_warnings'].includes(payload.status)
  }

  input.addEventListener('change', () => {
    if (state.status === AppState.ERROR) resetAfterError()
    selectedFiles.push(...Array.from(input.files ?? []))
    input.value = ''
    serverFiles = null
    const summary = summarizeSelection(selectedFiles)
    submitButton.disabled = !summary.canSubmit
    statusMessage.textContent = summary.unexpected.length
      ? `Arquivo não esperado: ${summary.unexpected.join(', ')}.`
      : summary.canSubmit
        ? 'Os sete arquivos foram recebidos e podem ser validados.'
        : `${selectedFiles.length} arquivo(s) selecionado(s). Complete o pacote.`
    renderFiles()
  })

  clearButton.addEventListener('click', () => {
    if (state.status === AppState.ERROR) resetAfterError()
    selectedFiles = []
    serverFiles = null
    submitButton.disabled = true
    resultSection.hidden = true
    continueButton.disabled = true
    statusMessage.textContent = 'Nenhum arquivo selecionado.'
    renderFiles()
  })

  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    const summary = summarizeSelection(selectedFiles)
    if (!summary.canSubmit || state.status !== AppState.EMPTY) return

    transitionTo(AppState.UPLOADING)
    setBusy(true)
    statusMessage.textContent = 'Enviando os arquivos…'
    try {
      transitionTo(AppState.VALIDATING)
      statusMessage.textContent = 'Validando estrutura e relações…'
      const payload = await uploadDataset(selectedFiles)
      setDataset(payload)
      transitionTo(AppState.READY)
      serverFiles = payload.files
      statusMessage.textContent = 'Pacote pronto para continuar.'
      renderFiles()
      renderResult(payload)
    } catch (error) {
      setError(error)
      transitionTo(AppState.ERROR)
      const payload = error instanceof ApiError ? error.payload : null
      if (payload) {
        serverFiles = payload.files
        renderFiles()
        renderResult(payload)
      }
      statusMessage.textContent = error instanceof Error ? error.message : 'Falha inesperada na validação.'
    } finally {
      setBusy(false)
    }
  })

  function setBusy(busy) {
    input.disabled = busy
    clearButton.disabled = busy
    submitButton.disabled = busy || !summarizeSelection(selectedFiles).canSubmit
    submitButton.textContent = busy ? 'Validando…' : 'Validar pacote'
  }

  renderFiles()
  section.append(form, inventory, resultSection)
  return section
}

function statusLabel(status) {
  return {
    missing: 'Ausente',
    received: 'Recebido',
    valid: 'Válido',
    invalid: 'Inválido',
  }[status] ?? status
}

function createIssueGroup(title, issues, variant) {
  const group = element('section', `issue-group issue-group--${variant}`)
  const heading = element('h3', '', `${title} (${issues.length})`)
  const list = element('ul')
  if (!issues.length) {
    list.append(element('li', '', variant === 'error' ? 'Nenhum erro impeditivo.' : 'Nenhum aviso.'))
  } else {
    for (const issue of issues) list.append(element('li', '', issue.message))
  }
  group.append(heading, list)
  return group
}
