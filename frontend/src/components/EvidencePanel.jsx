import { domainFromUrl, sourceLabel, summarizeWarnings } from '../lib/formatters'
import StatusPill from './StatusPill'

function EvidencePanel({ result }) {
  const sources = Array.isArray(result?.top_sources) ? result.top_sources : []
  const warnings = summarizeWarnings(result?.warnings || [])
  const provider = sourceLabel(result?.search_provider)
  const isFallbackOnly = result?.search_provider === 'local_known_hoax_references'

  return (
    <section className="panel evidence-panel">
      <div className="panel-head compact">
        <h3>Evidence & Provenance</h3>
        <div className="head-pills">
          <StatusPill label={provider} tone="neutral" />
          <StatusPill label={result?.evidence_completeness || 'low'} tone={result?.evidence_completeness === 'high' ? 'success' : 'warning'} />
        </div>
      </div>

      {isFallbackOnly && (
        <p className="helper-note">Web evidence retrieval was limited; local verified references were used.</p>
      )}

      {sources.length > 0 ? (
        <ul className="source-list">
          {sources.map((source, idx) => (
            <li key={`${source.url}-${idx}`}>
              <a href={source.url} target="_blank" rel="noreferrer">
                <strong>{source.title || 'Source'}</strong>
                <span>{domainFromUrl(source.url)}</span>
              </a>
            </li>
          ))}
        </ul>
      ) : (
        <p className="helper-note">No source links available for this run.</p>
      )}

      {warnings.length > 0 && (
        <div className="warning-box">
          <h4>Degraded Signals</h4>
          <ul>
            {warnings.slice(0, 3).map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

export default EvidencePanel
