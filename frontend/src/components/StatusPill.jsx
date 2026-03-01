function StatusPill({ label, tone = 'neutral' }) {
  return <span className={`status-pill tone-${tone}`}>{label}</span>
}

export default StatusPill
