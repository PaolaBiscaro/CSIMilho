const STEPS = [
  { id: 'data', number: '01', label: 'Dados', description: 'Importar e validar' },
  { id: 'comparison', number: '02', label: 'Comparação', description: 'Escolher talhões' },
  { id: 'investigation', number: '03', label: 'Investigação', description: 'Examinar resultados' },
]

export function createNavigation(currentStep = 'data') {
  const sidebar = document.createElement('aside')
  sidebar.className = 'sidebar'
  sidebar.setAttribute('aria-label', 'Etapas da investigação')

  const brand = document.createElement('div')
  brand.className = 'brand'

  const brandMark = document.createElement('span')
  brandMark.className = 'brand__mark'
  brandMark.setAttribute('aria-hidden', 'true')
  brandMark.textContent = 'FL'

  const brandText = document.createElement('div')
  const brandName = document.createElement('strong')
  brandName.textContent = 'FarmLab'
  const brandProduct = document.createElement('span')
  brandProduct.textContent = 'Investigator'
  brandText.append(brandName, brandProduct)
  brand.append(brandMark, brandText)

  const navigation = document.createElement('ol')
  navigation.className = 'step-list'

  for (const step of STEPS) {
    const item = document.createElement('li')
    const isCurrent = step.id === currentStep
    item.className = `step${isCurrent ? ' step--current' : ''}`
    if (isCurrent) item.setAttribute('aria-current', 'step')

    const number = document.createElement('span')
    number.className = 'step__number'
    number.textContent = step.number

    const text = document.createElement('span')
    const label = document.createElement('strong')
    label.textContent = step.label
    const description = document.createElement('small')
    description.textContent = step.description
    text.append(label, description)
    const link = document.createElement('a')
    link.className = 'step__link'
    link.href = '#' + step.id
    link.dataset.step = step.id
    link.append(number, text)
    item.append(link)
    navigation.append(item)
  }

  const note = document.createElement('p')
  note.className = 'sidebar__note'
  note.textContent = 'Dados locais e temporários. Nenhum CSV é enviado ao Gemini.'

  sidebar.append(brand, navigation, note)
  return sidebar
}

