import { useRef } from 'react'
import { prettyPercent } from '../lib/formatters'
import { useGsapContext, gsap } from '../hooks/useGsapContext'
import MetricChip from './MetricChip'
import StatusPill from './StatusPill'

const VERDICT_TONES = {
  TRUE: 'success',
  MOSTLY_TRUE: 'success',
  PARTIALLY_TRUE: 'warning',
  UNVERIFIABLE: 'neutral',
  MOSTLY_FALSE: 'danger',
  FALSE: 'danger',
}

function VerdictCard({ result, audioLoading, audioError, audioUrl, audioRef, onPlayAudio }) {
  const cardRef = useRef(null)
  const fillRef = useRef(null)

  if (!result) {
    return (
      <section className="panel verdict-empty">
        <h3>Verdict Output</h3>
        <p>Run a verification to see multilingual summary, confidence, and decision rationale.</p>
      </section>
    )
  }

  const tone = VERDICT_TONES[result.verdict] || 'neutral'
  const confidenceWidth = `${Math.max(3, Math.round((result.confidence || 0) * 100))}%`

  useGsapContext(
    cardRef,
    () => {
      gsap.fromTo(
        cardRef.current,
        { opacity: 0.75, y: 8 },
        { opacity: 1, y: 0, duration: 0.32, ease: 'power2.out', clearProps: 'transform' }
      )
      gsap.fromTo(fillRef.current, { width: '0%' }, { width: confidenceWidth, duration: 0.45, ease: 'power2.out' })
    },
    [result.verdict, result.confidence]
  )

  return (
    <section className="panel verdict-card entering" ref={cardRef}>
      <div className="verdict-head">
        <h3>Final Decision</h3>
        <StatusPill label={result.verdict || 'UNVERIFIABLE'} tone={tone} />
      </div>

      <div className="confidence-block" aria-label="Confidence score">
        <div className="confidence-top">
          <span>Confidence</span>
          <strong>{prettyPercent(result.confidence)}</strong>
        </div>
        <div className="confidence-track">
          <div ref={fillRef} className={`confidence-fill tone-${tone}`} style={{ width: confidenceWidth }} />
        </div>
      </div>

      {result.deterministic_override_applied && (
        <div className="override-banner" role="status">
          <strong>Deterministic safety override applied.</strong>
          <span>
            Reason: {result.override_reason || 'high-risk pattern'} | Match score: {result.override_match_score ?? '--'}
          </span>
        </div>
      )}

      {result.native_summary && result.detected_language !== 'en' && (
        <article className="summary-block native">
          <h4>Summary ({String(result.detected_language || '').toUpperCase()})</h4>
          <p>{result.native_summary}</p>
        </article>
      )}

      <article className="summary-block">
        <h4>Summary (EN)</h4>
        <p>{result.summary || 'No summary returned.'}</p>
      </article>

      <div className="metric-grid">
        <MetricChip label="Input Type" value={result.input_type || 'text'} />
        <MetricChip label="Search Provider" value={result.search_provider || 'none'} />
        <MetricChip label="Evidence" value={result.evidence_completeness || 'low'} />
        <MetricChip label="Trace ID" value={result.trace_id || 'n/a'} />
      </div>

      <div className="audio-box">
        <button type="button" className="btn btn-secondary" onClick={onPlayAudio} disabled={!result.audio_available || audioLoading}>
          {audioLoading ? 'Loading Audio...' : 'Play Verdict Audio'}
        </button>
        {audioUrl && <audio ref={audioRef} src={audioUrl} controls preload="none" />}
        {audioError && <p className="inline-error">{audioError}</p>}
        {result.audio_message && <small>{result.audio_message}</small>}
      </div>
    </section>
  )
}

export default VerdictCard
