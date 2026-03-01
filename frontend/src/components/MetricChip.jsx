function asText(value, fallback = 'n/a') {
  if (value === null || value === undefined) return fallback
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return fallback
    }
  }
  return fallback
}

function MetricChip({ label, value }) {
  return (
    <div className="metric-chip">
      <span className="metric-chip-label">{label}</span>
      <strong className="metric-chip-value">{asText(value)}</strong>
    </div>
  )
}

export default MetricChip
