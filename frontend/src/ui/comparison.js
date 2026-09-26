import comparisonMarkup from './comparison.html?raw'

export function createComparisonView() {
  const view = document.createElement('section')
  view.className = 'prototype-view'
  view.innerHTML = comparisonMarkup
  const notice = document.createElement('p')
  // notice.className = 'prototype-notice'
  // notice.textContent = 'Demonstração estática · As seleções são ilustrativas. A investigação mostra o exemplo fixo Grão 4.0 × Grão Convencional do protótipo.'
  view.prepend(notice)
  const target = view.querySelector('#target')
  const reference = view.querySelector('#reference')
  const update = () => {
    view.querySelector('#comparisonName').textContent = `${target.value} × ${reference.value}`
  }
  target.addEventListener('change', update)
  reference.addEventListener('change', update)
  view.querySelector('#runAnalysis').addEventListener('click', () => {
    window.location.hash = 'investigation'
  })
  return view
}
