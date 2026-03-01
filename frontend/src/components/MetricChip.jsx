function MetricChip({ label, value }) {
  return (
    <div className="metric-chip">
      <span className="metric-chip-label">{label}</span>
      <strong className="metric-chip-value">{value}</strong>
    </div>
  )
}

export default MetricChip
