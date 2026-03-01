/**
 * @typedef {Object} AgentVote
 * @property {string} agent
 * @property {'supports'|'refutes'|'mixed'|'insufficient'} stance
 * @property {number} confidence
 * @property {string} reason
 */

/**
 * @typedef {Object} SourceItem
 * @property {string} title
 * @property {string} url
 */

/**
 * @typedef {Object} VerificationResultShape
 * @property {string} verification_id
 * @property {'processing'|'completed'|'error'} status
 * @property {string} [stage]
 * @property {string} [detected_language]
 * @property {string} [verdict]
 * @property {number} [confidence]
 * @property {string} [summary]
 * @property {string} [native_summary]
 * @property {SourceItem[]} [top_sources]
 * @property {'high'|'medium'|'low'} [evidence_completeness]
 * @property {AgentVote[]} [agent_votes]
 * @property {Record<string, unknown>} [consensus_breakdown]
 * @property {Record<string, unknown>} [evidence_graph]
 * @property {Record<string, number>} [latency_ms_by_stage]
 * @property {string[]} [warnings]
 * @property {Record<string, string>} [agent_errors]
 * @property {string} [trace_id]
 */

export {}
