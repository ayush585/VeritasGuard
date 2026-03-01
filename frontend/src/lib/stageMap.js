const ORCHESTRATOR_ORDER = ['language_detection', 'translation', 'claim_extraction', 'verification', 'verdict', 'done']

export const PHASES = [
  {
    key: 'detect_translate',
    label: 'Detect + Translate',
    stages: ['language_detection', 'translation'],
    agents: ['Language Detector', 'Translator'],
  },
  {
    key: 'claim_extraction',
    label: 'Claim Extraction',
    stages: ['claim_extraction'],
    agents: ['Claim Extractor'],
  },
  {
    key: 'retrieval_cluster',
    label: 'Evidence Retrieval Cluster',
    stages: ['verification'],
    agents: ['Source', 'Context', 'Expert', 'Media'],
  },
  {
    key: 'consensus',
    label: 'Consensus Resolution',
    stages: ['verification', 'verdict'],
    agents: ['Consensus Engine'],
  },
  {
    key: 'verdict',
    label: 'Verdict Synthesis',
    stages: ['verdict', 'done'],
    agents: ['Verdict Agent'],
  },
]

function stageIndex(stage) {
  const idx = ORCHESTRATOR_ORDER.indexOf(stage)
  return idx === -1 ? 0 : idx
}

export function resolvePhaseState(phase, currentStage, result) {
  const current = stageIndex(currentStage || 'language_detection')
  const phaseStart = Math.min(...phase.stages.map((s) => stageIndex(s)))
  const phaseEnd = Math.max(...phase.stages.map((s) => stageIndex(s)))
  const warnings = Array.isArray(result?.warnings) ? result.warnings : []
  const hasTimeoutWarning = warnings.some((w) => String(w).toLowerCase().includes('timed out'))

  if (result?.status === 'error') return 'skipped'
  if (result?.status === 'completed' && current >= phaseEnd) {
    if (phase.key === 'retrieval_cluster' && hasTimeoutWarning) return 'degraded'
    return 'done'
  }
  if (current > phaseEnd) return 'done'
  if (current >= phaseStart && current <= phaseEnd) return 'active'
  return 'pending'
}
