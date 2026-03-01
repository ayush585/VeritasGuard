import { useMemo, useState } from 'react'

function DebugDrawer({ result, debugPayload, loadingDebug }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const effectivePayload = useMemo(() => {
    if (debugPayload) return debugPayload
    if (!result) return null
    return {
      verification_id: result.verification_id,
      trace_id: result.trace_id,
      stage_timings: result.stage_timings || {},
      latency_ms_by_stage: result.latency_ms_by_stage || {},
      warnings: result.warnings || [],
      agent_errors: result.agent_errors || {},
      search_provider: result.search_provider || 'none',
      search_results_count: result.search_results_count || 0,
    }
  }, [debugPayload, result])

  const copyBundle = async () => {
    if (!effectivePayload) return
    try {
      await navigator.clipboard.writeText(JSON.stringify(effectivePayload, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="panel debug-drawer">
      <div className="debug-head">
        <h3>Debug Trace</h3>
        <div className="debug-actions">
          <button type="button" className="btn btn-ghost" onClick={() => setOpen((prev) => !prev)}>
            {open ? 'Hide Trace' : 'Open Debug Trace'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={copyBundle} disabled={!effectivePayload || loadingDebug}>
            {copied ? 'Copied' : 'Copy Debug Bundle'}
          </button>
        </div>
      </div>

      {open && (
        <div className="debug-body">
          <pre>{loadingDebug ? 'Loading debug payload...' : JSON.stringify(effectivePayload, null, 2)}</pre>
        </div>
      )}
    </section>
  )
}

export default DebugDrawer
