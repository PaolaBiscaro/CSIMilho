export function element(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

export function control(labelText, name, options) {
  const label = element('label', 'control-field')
  const select = element('select')
  select.name = name
  for (const [value, text] of options) {
    const option = element('option', '', text)
    option.value = value
    select.append(option)
  }
  label.append(element('span', '', labelText), select)
  return { label, select }
}

export function formatValue(value) {
  return value === null || value === undefined ? 'Indisponível' : new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 4 }).format(value)
}

export function table(caption, headers, rows) {
  const wrap = element('div', 'accessible-table-wrap')
  const result = element('table', 'accessible-table')
  const head = element('thead')
  const heading = element('tr')
  for (const text of headers) {
    const th = element('th', '', text)
    th.scope = 'col'
    heading.append(th)
  }
  head.append(heading)
  const body = element('tbody')
  for (const values of rows) {
    const row = element('tr')
    values.forEach((text, index) => {
      const cell = element(index === 0 ? 'th' : 'td', '', String(text))
      if (index === 0) cell.scope = 'row'
      row.append(cell)
    })
    body.append(row)
  }
  result.append(element('caption', '', caption), head, body)
  wrap.append(result)
  return wrap
}
