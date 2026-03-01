import { useRef } from 'react'
import { useGsapContext, gsap } from '../hooks/useGsapContext'

function EvidenceGraphPanel({ result }) {
  const scopeRef = useRef(null)
  const graph = result?.evidence_graph || {}
  const claimNodes = Array.isArray(graph.claim_nodes) ? graph.claim_nodes : []
  const evidenceNodes = Array.isArray(graph.evidence_nodes) ? graph.evidence_nodes : []
  const edges = Array.isArray(graph.edges) ? graph.edges : []

  useGsapContext(
    scopeRef,
    () => {
      gsap.fromTo(
        '.graph-col',
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, stagger: 0.06, duration: 0.22, ease: 'power2.out', clearProps: 'transform' }
      )
    },
    [result?.verification_id]
  )

  return (
    <section className="panel graph-panel" ref={scopeRef}>
      <div className="panel-head compact">
        <h3>Evidence Graph</h3>
        <p>Claim-to-evidence contradiction/support map with decision path.</p>
      </div>

      {(claimNodes.length === 0 && evidenceNodes.length === 0) ? (
        <p className="helper-note">
          Graph data unavailable for this run. Deterministic fallback may have been used to preserve safety.
        </p>
      ) : (
        <div className="graph-layout">
          <div className="graph-col">
            <h4>Claim Nodes</h4>
            <ul>
              {claimNodes.map((node, idx) => (
                <li key={`${node.id || 'claim'}-${idx}`}>{node.text || node.id || 'Claim'}</li>
              ))}
            </ul>
          </div>
          <div className="graph-col">
            <h4>Evidence Nodes</h4>
            <ul>
              {evidenceNodes.slice(0, 6).map((node, idx) => (
                <li key={`${node.id || 'ev'}-${idx}`}>{node.text || node.id || 'Evidence'}</li>
              ))}
            </ul>
          </div>
          <div className="graph-col">
            <h4>Resolution</h4>
            <ul>
              {edges.slice(0, 8).map((edge, idx) => (
                <li key={`${edge.from || 'f'}-${edge.to || 't'}-${idx}`}>
                  {edge.from || 'Claim'} -> {edge.to || 'Evidence'} ({edge.type || 'link'})
                </li>
              ))}
            </ul>
            <p className="decision-path">{graph.resolution || graph.final_decision_path || 'Decision path unavailable.'}</p>
          </div>
        </div>
      )}
    </section>
  )
}

export default EvidenceGraphPanel
