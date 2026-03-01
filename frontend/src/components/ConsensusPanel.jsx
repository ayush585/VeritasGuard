import { prettyPercent, titleCase } from '../lib/formatters'

function meterValue(value) {
  const num = Number(value || 0)
  if (Number.isNaN(num)) return 0
  return Math.max(0, Math.min(100, Math.round(num * 100)))
}

function ConsensusPanel({ result }) {
  const votes = Array.isArray(result?.agent_votes) ? result.agent_votes : []
  const consensus = result?.consensus_breakdown || {}

  return (
    <section className="panel consensus-panel">
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
                  <td>{vote.agent}</td>
                  <td>{titleCase(vote.stance)}</td>
                  <td>{prettyPercent(vote.confidence)}</td>
                  <td>{vote.reason || 'n/a'}</td>
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
            <div className="meter-fill tone-danger" style={{ width: `${meterValue(consensus.weighted_refute)}%` }} />
          </div>
          <strong>{prettyPercent(consensus.weighted_refute)}</strong>
        </label>
        <label>
          <span>Weighted Support</span>
          <div className="meter">
            <div className="meter-fill tone-success" style={{ width: `${meterValue(consensus.weighted_support)}%` }} />
          </div>
          <strong>{prettyPercent(consensus.weighted_support)}</strong>
        </label>
        <label>
          <span>Weighted Uncertain</span>
          <div className="meter">
            <div className="meter-fill tone-neutral" style={{ width: `${meterValue(consensus.weighted_uncertain)}%` }} />
          </div>
          <strong>{prettyPercent(consensus.weighted_uncertain)}</strong>
        </label>
      </div>

      <div className="consensus-footer">
        <span>Agent Agreement: {prettyPercent(consensus.agent_agreement_score)}</span>
        <small>{consensus.decision_rule || 'Decision rule not available.'}</small>
      </div>
    </section>
  )
}

export default ConsensusPanel
