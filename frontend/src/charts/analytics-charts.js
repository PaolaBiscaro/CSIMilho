import Chart from 'chart.js/auto'
import { element, formatDate, formatValue } from '../ui/dom.js'

export function chartColors() {
  const styles = getComputedStyle(document.documentElement)
  return ['--brown-700', '--brown-200', '--brown-500', '--brown-900'].map((token) => styles.getPropertyValue(token).trim())
}

const unitLabel = (unit) => unit ?? 'unidade não documentada'

function options(unit) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: { position: 'bottom' },
      tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${formatValue(context.parsed.y)} · ${unitLabel(unit)}` } },
    },
    scales: { y: { title: { display: true, text: unitLabel(unit) } } },
  }
}

export function ndviConfig(evidence, labels, colors) {
  if (!evidence?.series?.length) return null
  return {
    type: 'line',
    data: {
      labels: evidence.series.map((point) => point.date),
      datasets: [
        { label: labels.target, data: evidence.series.map((point) => point.target_ndvi), borderColor: colors[0], backgroundColor: colors[0], tension: 0, pointRadius: 4 },
        { label: labels.reference, data: evidence.series.map((point) => point.reference_ndvi), borderColor: colors[2], backgroundColor: colors[2], borderDash: [6, 4], tension: 0, pointRadius: 4 },
      ],
    },
    options: {
      ...options(evidence.unit), spanGaps: false,
      scales: { ...options(evidence.unit).scales, x: { ticks: { callback(value) { return formatDate(this.getLabelForValue(value)) } } } },
      plugins: { ...options(evidence.unit).plugins, tooltip: { callbacks: {
        ...options(evidence.unit).plugins.tooltip.callbacks,
        title: (items) => formatDate(evidence.series[items[0]?.dataIndex]?.date),
        afterBody: (items) => `Gap alvo − referência: ${formatValue(evidence.series[items[0]?.dataIndex]?.gap)}`,
      } } },
    },
  }
}

const STAT_LABELS = ['Mínimo', 'Q1', 'Mediana', 'Q3', 'Máximo']

// Draw the five-number summary already calculated by Python. No observations are inferred.
const fiveNumberSummary = {
  id: 'fiveNumberSummary',
  beforeDatasetsDraw(chart) {
    const points = chart.data.datasets[0].data
    const pixels = points.map((point) => chart.scales.x.getPixelForValue(point.x))
    const [min, q1, median, q3, max] = pixels
    const y = chart.scales.y.getPixelForValue(1)
    const { ctx } = chart
    ctx.save()
    ctx.strokeStyle = chart.data.datasets[0].borderColor
    ctx.fillStyle = chart.data.datasets[0].backgroundColor
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(min, y)
    ctx.lineTo(max, y)
    for (const x of [min, max]) { ctx.moveTo(x, y - 15); ctx.lineTo(x, y + 15) }
    ctx.stroke()
    ctx.fillRect(q1, y - 28, q3 - q1, 56)
    ctx.strokeRect(q1, y - 28, q3 - q1, 56)
    ctx.beginPath()
    ctx.moveTo(median, y - 28)
    ctx.lineTo(median, y + 28)
    ctx.stroke()
    ctx.restore()
  },
}

export function distributionConfig(metric, colors) {
  if (!metric?.valid_n) return null
  const values = [metric.min, metric.q1, metric.median, metric.q3, metric.max]
  if (!values.every((value) => typeof value === 'number' && Number.isFinite(value))) return null
  return {
    type: 'scatter',
    plugins: [fiveNumberSummary],
    data: { datasets: [{ label: metric.name, data: values.map((x) => ({ x, y: 1 })), borderColor: colors[0], backgroundColor: colors[1], pointRadius: 5, pointHoverRadius: 8 }] },
    options: {
      ...options(metric.unit),
      scales: { x: { title: { display: true, text: unitLabel(metric.unit) }, grace: '15%' }, y: { display: false, min: 0, max: 2 } },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (context) => `${STAT_LABELS[context.dataIndex]}: ${formatValue(context.parsed.x)} · ${unitLabel(metric.unit)}` } } },
    },
  }
}

export function pairedSoilConfig(metric, colors) {
  if (!metric?.pairs?.length) return null
  return {
    type: 'bar',
    data: {
      labels: metric.pairs.map((pair) => `Amostra ${pair.sample_id}`),
      datasets: [
        { label: 'Conjunto 1', data: metric.pairs.map((pair) => pair.group_1), backgroundColor: colors[0] },
        { label: 'Conjunto 2', data: metric.pairs.map((pair) => pair.group_2), backgroundColor: colors[2] },
      ],
    },
    options: {
      ...options(metric.unit),
      plugins: {
        ...options(metric.unit).plugins,
        tooltip: { callbacks: {
          ...options(metric.unit).plugins.tooltip.callbacks,
          afterBody: (items) => `Delta 2 − 1: ${formatValue(metric.pairs[items[0].dataIndex].delta)}`,
        } },
      },
    },
  }
}

export function textureConfig(texture, colors) {
  if (!texture?.samples?.length) return null
  return {
    type: 'bar',
    data: {
      labels: texture.samples.map((sample) => `Amostra ${sample.sample_id}`),
      datasets: [['sand', 'Areia', colors[1]], ['silt', 'Silte', colors[2]], ['clay', 'Argila', colors[0]]].map(([key, label, backgroundColor]) => ({
        label, backgroundColor, data: texture.samples.map((sample) => sample[key]),
      })),
    },
    options: { ...options(texture.unit), scales: { x: { stacked: true }, y: { stacked: true, min: 0, max: 100, title: { display: true, text: '%' } } } },
  }
}

export function createChartController(host, ChartClass = Chart) {
  let instance = null
  return {
    update(config, description) {
      this.destroy()
      host.replaceChildren()
      if (!config) {
        host.append(element('p', 'empty-chart', 'Não há observações suficientes para este gráfico.'))
        return
      }
      const canvas = element('canvas')
      canvas.setAttribute('role', 'img')
      canvas.setAttribute('aria-label', description)
      host.append(canvas)
      instance = new ChartClass(canvas, config)
    },
    destroy() {
      instance?.destroy()
      instance = null
    },
  }
}
