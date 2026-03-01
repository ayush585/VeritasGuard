import { PHASES, resolvePhaseState } from '../lib/stageMap'
import { prettyMs } from '../lib/formatters'
import StatusPill from './StatusPill'

function stateTone(state) {
  if (state === 'done') return 'success'
  if (state === 'active') return 'active'
  if (state === 'degraded') return 'warning'
  if (state === 'skipped') return 'danger'
  return 'neutral'
}

function PipelinePanel({ stage, result }) {
  const timings = result?.latency_ms_by_stage || {}

  return (
    <section className="panel">
      <div className="panel-head compact">
        <h3>Agent Orchestration Pipeline</h3>
        <p>Impact-first verification flow across language, retrieval, consensus, and verdict stages.</p>
      </div>

      <div className="pipeline-list" role="list" aria-label="Pipeline stages">
        {PHASES.map((phase) => {
          const state = resolvePhaseState(phase, stage, result)
          const latency = phase.stages.reduce((sum, key) => sum + Number(timings[key] || 0), 0)
          return (
            <div
              key={phase.key}
              className={`pipeline-item state-${state}`}
              role="listitem"
            >
              <div className="pipeline-marker" aria-hidden="true" />
              <div className="pipeline-content">
                <div className="pipeline-top">
                  <h4>{phase.label}</h4>
                  <StatusPill label={state} tone={stateTone(state)} />
                </div>
                <p>{phase.agents.join(' • ')}</p>
              </div>
              <div className="pipeline-metric">{prettyMs(latency)}</div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default PipelinePanel
