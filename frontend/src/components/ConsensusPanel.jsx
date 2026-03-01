import { useRef } from 'react'
import { prettyPercent, titleCase } from '../lib/formatters'
import { useGsapContext, gsap } from '../hooks/useGsapContext'

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

function meterValue(value) {
  const num = Number(value || 0)
  if (Number.isNaN(num)) return 0
  return Math.max(0, Math.min(100, Math.round(num * 100)))
}

function ConsensusPanel({ result }) {
  const scopeRef = useRef(null)
  const votes = Array.isArray(result?.agent_votes) ? result.agent_votes : []
  const consensus = result?.consensus_breakdown || {}

  useGsapContext(
    scopeRef,
    () => {
      gsap.fromTo(
        '.votes-table tbody tr',
        { opacity: 0, y: 6 },
        { opacity: 1, y: 0, stagger: 0.04, duration: 0.24, ease: 'power2.out', clearProps: 'transform' }
      )
      const fills = gsap.utils.toArray('.meter-fill')
      fills.forEach((node) => {
        const target = node.getAttribute('data-target') || '0%'
        gsap.fromTo(node, { width: '0%' }, { width: target, duration: 0.38, ease: 'power2.out' })
      })
    },
    [result?.verification_id, consensus.decision_rule]
  )

  return (
    <section className="panel consensus-panel" ref={scopeRef}>
      <div className="panel-head compact">
        <h3>Consensus Logic</h3>
        <p>Agent disagreement is resolved via weighted evidence synthesis.</p>
      </div>

      {votes.length > 0 ? (
        <div className="votes-table-wrap">
          <table className="votes-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Stance</th>
                <th>Confidence</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {votes.map((vote, idx) => (
                <tr key={`${vote.agent}-${idx}`}>
                  <td>{asText(vote.agent)}</td>
                  <td>{titleCase(asText(vote.stance, 'insufficient'))}</td>
                  <td>{prettyPercent(vote.confidence)}</td>
                  <td>{asText(vote.reason)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="helper-note">Consensus data will appear when agent votes are available.</p>
      )}

      <div className="meter-group">
        <label>
          <span>Weighted Refute</span>
          <div className="meter">
            <div
              className="meter-fill tone-danger"
              data-target={`${meterValue(consensus.weighted_refute)}%`}
              style={{ width: `${meterValue(consensus.weighted_refute)}%` }}
            />
          </div>
          <strong>{prettyPercent(consensus.weighted_refute)}</strong>
        </label>
        <label>
          <span>Weighted Support</span>
          <div className="meter">
            <div
              className="meter-fill tone-success"
              data-target={`${meterValue(consensus.weighted_support)}%`}
              style={{ width: `${meterValue(consensus.weighted_support)}%` }}
            />
          </div>
          <strong>{prettyPercent(consensus.weighted_support)}</strong>
        </label>
        <label>
          <span>Weighted Uncertain</span>
          <div className="meter">
            <div
              className="meter-fill tone-neutral"
              data-target={`${meterValue(consensus.weighted_uncertain)}%`}
              style={{ width: `${meterValue(consensus.weighted_uncertain)}%` }}
            />
          </div>
          <strong>{prettyPercent(consensus.weighted_uncertain)}</strong>
        </label>
      </div>

      <div className="consensus-footer">
        <span>Agent Agreement: {prettyPercent(consensus.agent_agreement_score)}</span>
        <small>{asText(consensus.decision_rule, 'Decision rule not available.')}</small>
      </div>
    </section>
  )
}

export default ConsensusPanel
