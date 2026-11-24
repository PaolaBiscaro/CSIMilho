import { testGemini } from '../api.js'
import { element } from './dom.js'

export function createGeminiTestControl({ probeGemini = testGemini } = {}) {
  const control = element('div', 'gemini-test-control')
  const button = element('button', 'button button--ghost', 'Testar conexão com o Gemini')
  button.type = 'button'
  const status = element('p', 'gemini-test-control__status')
  status.setAttribute('role', 'status')
  status.setAttribute('aria-live', 'polite')
  control.append(button, status)

  let disposed = false
  let controller

  button.addEventListener('click', async () => {
    if (button.disabled || disposed) return
    button.disabled = true
    button.textContent = 'Testando…'
    status.setAttribute('role', 'status')
    status.textContent = 'Verificando conexão…'
    controller = new AbortController()
    try {
      const result = await probeGemini({ signal: controller.signal })
      if (disposed) return
      const fullyAvailable = result.success
        && result.available_key_count === result.configured_key_count
      status.setAttribute('role', fullyAvailable ? 'status' : 'alert')
      status.textContent = result.message
    } catch (error) {
      if (disposed || error?.name === 'AbortError') return
      status.setAttribute('role', 'alert')
      status.textContent = error instanceof Error ? error.message : 'Não foi possível testar a conexão.'
    } finally {
      if (!disposed) {
        button.disabled = false
        button.textContent = 'Testar conexão com o Gemini'
      }
    }
  })

  control.dispose = () => {
    disposed = true
    controller?.abort()
  }
  control.mount = () => { disposed = false }
  return control
}
