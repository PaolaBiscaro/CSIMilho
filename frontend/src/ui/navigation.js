export const NAV_ITEMS = Object.freeze([
  { id: 'data', label: 'Dados' },
  { id: 'comparison', label: 'Comparação' },
  { id: 'investigation', label: 'Investigação' },
])

export function createNavigation(currentPage = 'data', onNavigate = () => {}, {
  busy = false, comparisonAvailable = false, investigationAvailable = false,
} = {}) {
  const header = document.createElement('header')
  header.className = 'app-header'

  const brand = document.createElement('button')
  brand.className = 'brand'
  brand.type = 'button'
  brand.disabled = busy
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
    const available = item.id === 'data' || (item.id === 'comparison' ? comparisonAvailable : investigationAvailable)
    button.disabled = busy || !available
    button.textContent = item.label
    button.dataset.page = item.id
    if (isCurrent) button.setAttribute('aria-current', 'page')
    button.addEventListener('click', () => onNavigate(item.id))
    navigation.append(button)
  }

  header.append(brand, navigation)
  return header
}
