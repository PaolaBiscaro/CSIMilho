export const NAV_ITEMS = Object.freeze([
  { id: 'data', label: 'Dados' },
  { id: 'comparison', label: 'Comparação' },
  { id: 'investigation', label: 'Investigação' },
])

export function createNavigation(currentPage = 'data', onNavigate = () => {}) {
  const header = document.createElement('header')
  header.className = 'app-header'

  const brand = document.createElement('button')
  brand.className = 'brand'
  brand.type = 'button'
  brand.setAttribute('aria-label', 'FarmLab Investigator — abrir Dados')
  brand.addEventListener('click', () => onNavigate('data'))

  const brandMark = document.createElement('span')
  brandMark.className = 'brand__mark'
  brandMark.setAttribute('aria-hidden', 'true')
  brandMark.textContent = 'FL'

  const brandText = document.createElement('span')
  brandText.className = 'brand__text'
  const brandName = document.createElement('strong')
  brandName.textContent = 'FarmLab'
  const brandProduct = document.createElement('small')
  brandProduct.textContent = 'Investigator'
  brandText.append(brandName, brandProduct)
  brand.append(brandMark, brandText)

  const navigation = document.createElement('nav')
  navigation.className = 'app-nav'
  navigation.setAttribute('aria-label', 'Áreas da aplicação')

  for (const item of NAV_ITEMS) {
    const button = document.createElement('button')
    const isCurrent = item.id === currentPage
    button.className = `nav-pill${isCurrent ? ' nav-pill--active' : ''}`
    button.type = 'button'
    button.textContent = item.label
    button.dataset.page = item.id
    if (isCurrent) button.setAttribute('aria-current', 'page')
    button.addEventListener('click', () => onNavigate(item.id))
    navigation.append(button)
  }

  const session = document.createElement('div')
  session.className = 'header-session'
  const dot = document.createElement('span')
  dot.className = 'header-session__dot'
  dot.setAttribute('aria-hidden', 'true')
  const copy = document.createElement('span')
  copy.textContent = 'Sessão local'
  session.append(dot, copy)

  header.append(brand, navigation, session)
  return header
}
