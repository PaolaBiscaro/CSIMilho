// chart_data is a projection of evidence, never a second analytical source.
function sameValue(left, right) {
  if (left === right) return true
  if (left === null || right === null || typeof left !== 'object' || typeof right !== 'object') return false
  if (Array.isArray(left) !== Array.isArray(right)) return false
  const keys = Object.keys(left)
  return keys.length === Object.keys(right).length && keys.every((key) => Object.hasOwn(right, key) && sameValue(left[key], right[key]))
}

export function hasConsistentChartData(data, evidence) {
  const byId = new Map(evidence.map((item) => [item.evidence_id, item]))
  const matches = (item) => item != null && sameValue(item, byId.get(item.evidence_id))
  const summaries = data.soil_summaries ?? []
  const groups = data.soil_groups ?? []
  const validList = (items, predicate) => Array.isArray(items)
    && new Set(items.map((item) => item?.evidence_id)).size === items.length
    && items.every((item) => matches(item) && predicate(item))
  return (data.ndvi == null || (matches(data.ndvi) && Array.isArray(data.ndvi.series)))
    && validList(summaries, (item) => item.scope === 'dataset' && ['group_1', 'group_2'].includes(item.measurement_group)
      && Array.isArray(item.metrics) && Array.isArray(item.texture?.samples))
    && validList(groups, (item) => item.scope === 'dataset' && item.comparison === 'group_2_minus_group_1' && Array.isArray(item.metrics))
}
