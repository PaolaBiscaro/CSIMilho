import { ApiError, getHealth, testGemini } from '../api.js'
import { element, formatValue } from './dom.js'

export function createPreflightPanel({ readHealth = getHealth, probeGemini = testGemini } = {}) {
  const panel = element('section', 'dashboard-card preflight-panel')
  panel.setAttribute('aria-labelledby', 'preflight-title')
  const title = element('h2', '', 'Antes de apresentar')
  title.id = 'preflight-title'
  const description = element('p', 'card-description', 'Confira a conexão antes de importar os arquivos. Configuração detectada não confirma acesso ao Gemini.')
  const metadata = element('dl', 'audit-metadata preflight-metadata')
  const values = {}
  for (const [key, label] of [['backend', 'Backend'], ['gemini', 'Gemini'], ['model', 'Modelo configurado'], ['version', 'Versão do backend']]) {
    const item = element('div')
    values[key] = element('dd', '', 'Não verificado')
    values[key].dataset.check = key
    item.append(element('dt', '', label), values[key])
    metadata.append(item)
  }
  const actions = element('div', 'card-actions')
  const refresh = element('button', 'button button--secondary', 'Atualizar status')
  const test = element('button', 'button button--primary', 'Testar Gemini')
  refresh.type = test.type = 'button'
  test.disabled = true
  const hint = element('p', 'card-description', 'Testar Gemini faz uma chamada curta ao modelo, sem enviar o pacote importado ou iniciar uma investigação.')
  hint.id = 'preflight-test-hint'
  test.setAttribute('aria-describedby', hint.id)
  const status = element('p', 'status-message')
  status.setAttribute('role', 'status')
  status.setAttribute('aria-atomic', 'true')
  status.tabIndex = -1
  const latency = element('p', 'chart-hint', 'Latência do teste: não medida.')
  latency.dataset.check = 'latency'
  actions.append(refresh, test)
  panel.append(title, description, metadata, hint, actions, status, latency)

  let active = false
  let busy = false
  let configured = false
  let revision = 0
  let controller

  async function run(kind, userInitiated = false) {
    if (!active || busy || (kind === 'probe' && !configured)) return
    busy = true
    const current = ++revision
    controller = new AbortController()
    refresh.disabled = test.disabled = true
    refresh.textContent = kind === 'health' ? 'Verificando…' : 'Atualizar status'
    test.textContent = kind === 'probe' ? 'Testando…' : 'Testar Gemini'
    status.setAttribute('role', 'status')
    status.textContent = kind === 'health' ? 'Verificando o backend e a configuração do Gemini…' : 'Aguardando a resposta do Gemini…'
    latency.textContent = 'Latência do teste: não medida.'
    if (kind === 'health') {
      configured = false
      values.backend.textContent = 'Verificando…'
      values.gemini.textContent = values.model.textContent = values.version.textContent = 'Não verificado'
    }
    try {
      const result = await (kind === 'health' ? readHealth : probeGemini)({ signal: controller.signal })
      if (!active || current !== revision) return
      values.backend.textContent = 'Conectado'
      values.model.textContent = result.model
      if (kind === 'health') {
        configured = result.gemini_configured
        values.gemini.textContent = configured ? 'Configurado · conexão não testada' : 'Não configurado'
        values.version.textContent = result.version
        status.textContent = configured ? 'Backend conectado. Use Testar Gemini para confirmar acesso ao modelo.'
          : 'Backend conectado. Configure a chave do Gemini no backend e atualize o status. O fallback local continua disponível.'
      } else {
        if (result.error_code === 'missing_api_key') configured = false
        values.gemini.textContent = result.success ? 'Conexão confirmada' : configured ? 'Configurado · teste falhou' : 'Não configurado'
        status.setAttribute('role', result.success ? 'status' : 'alert')
        status.textContent = result.message
        latency.textContent = `Latência do teste: ${formatValue(result.latency_ms)} ms · medida pelo backend.`
      }
    } catch (error) {
      if (!active || current !== revision) return
      configured = false
      values.backend.textContent = 'Conexão não confirmada'
      values.gemini.textContent = values.model.textContent = values.version.textContent = 'Não verificado'
      status.setAttribute('role', 'alert')
      status.textContent = error instanceof ApiError ? error.message : 'Não foi possível verificar a conexão. Atualize o status para tentar novamente.'
    } finally {
      if (active && current === revision) {
        busy = false
        refresh.disabled = false
        test.disabled = !configured
        refresh.textContent = 'Atualizar status'
        test.textContent = 'Testar Gemini'
        if (userInitiated && panel.isConnected) status.focus()
      }
    }
  }
  refresh.addEventListener('click', () => run('health', true))
  test.addEventListener('click', () => run('probe', true))
  panel.mount = () => {
    if (active) return
    active = true
    busy = false
    run('health')
  }
  panel.dispose = () => { active = false; revision++; controller?.abort() }
  return panel
}
