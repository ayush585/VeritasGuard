import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'
import * as api from './utils/api'

vi.mock('./utils/api', async () => {
  const actual = await vi.importActual('./utils/api')
  return {
    ...actual,
    submitText: vi.fn(),
    submitImage: vi.fn(),
    getResult: vi.fn(),
    getResultDebug: vi.fn(),
    fetchResultAudio: vi.fn(),
  }
})

describe('VeritasGuard Frontend Rebuild', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.history.pushState({}, '', '/')
  })

  test('renders landing route with trust narrative and verify CTA', () => {
    render(<App />)
    expect(screen.getByText(/Multilingual trust firewall for viral claims/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Run Live Verification/i })).toBeInTheDocument()
  })

  test('navigates to command center and renders completed verdict', async () => {
    window.history.pushState({}, '', '/verify')
    api.submitText.mockResolvedValue({ verification_id: 'abc123' })
    api.getResult.mockResolvedValue({
      verification_id: 'abc123',
      status: 'completed',
      stage: 'done',
      verdict: 'FALSE',
      confidence: 0.92,
      summary: 'Claim is false.',
      native_summary: 'यह दावा झूठा है।',
      detected_language: 'hi',
      input_type: 'text',
      search_provider: 'local_known_hoax_references',
      search_results_count: 2,
      evidence_completeness: 'medium',
      top_sources: [
        { title: 'PIB Fact Check', url: 'https://pib.gov.in/factcheck' },
        { title: 'WHO Mythbusters', url: 'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters' },
      ],
      warnings: ['Source retrieval degraded; injected local curated references.'],
      agent_votes: [
        { agent: 'source_verification', stance: 'refutes', confidence: 0.8, reason: 'Multiple debunks found.' },
      ],
      consensus_breakdown: {
        weighted_refute: 0.81,
        weighted_support: 0.08,
        weighted_uncertain: 0.11,
        agent_agreement_score: 0.83,
        decision_rule: 'Weighted refute exceeds threshold.',
      },
      evidence_graph: {
        claim_nodes: [{ id: 'claim1', text: 'Microchips in vaccines' }],
        evidence_nodes: [{ id: 'ev1', text: 'PIB debunk' }],
        contradiction_edges: [{ from: 'claim1', to: 'ev1', relation: 'refutes' }],
        resolution: { path: 'Refute edge dominates.' },
      },
      audio_available: false,
      audio_status: 'disabled',
      audio_message: 'Audio disabled in this run.',
      trace_id: 'trace_abc123',
    })
    api.getResultDebug.mockResolvedValue({
      verification_id: 'abc123',
      trace_id: 'trace_abc123',
      stage_timings: { verification: 2.1 },
    })

    render(<App />)
    fireEvent.change(screen.getByPlaceholderText(/Paste suspicious text/i), {
      target: { value: 'The government is implanting microchips through vaccines' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Verify Claim/i }))

    await waitFor(() => {
      expect(screen.getByText(/Final Decision/i)).toBeInTheDocument()
      expect(screen.getByText('FALSE')).toBeInTheDocument()
      expect(screen.getByText(/PIB Fact Check/i)).toBeInTheDocument()
      expect(screen.getByText(/Consensus Logic/i)).toBeInTheDocument()
    })
  })

  test('opens debug drawer and renders payload', async () => {
    window.history.pushState({}, '', '/verify')
    api.submitText.mockResolvedValue({ verification_id: 'dbg1' })
    api.getResult.mockResolvedValue({
      verification_id: 'dbg1',
      status: 'completed',
      stage: 'done',
      verdict: 'UNVERIFIABLE',
      confidence: 0.2,
      summary: 'Insufficient evidence.',
      search_provider: 'none',
      search_results_count: 0,
      warnings: [],
      top_sources: [],
      agent_votes: [],
      consensus_breakdown: {},
      evidence_graph: {},
      audio_available: false,
      trace_id: 'trace_dbg1',
    })
    api.getResultDebug.mockResolvedValue({
      verification_id: 'dbg1',
      trace_id: 'trace_dbg1',
      warnings: [],
      stage_timings: { verdict: 1.0 },
    })

    render(<App />)
    fireEvent.change(screen.getByPlaceholderText(/Paste suspicious text/i), {
      target: { value: 'unknown claim' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Verify Claim/i }))

    await waitFor(() => expect(screen.getByRole('heading', { name: /Debug Trace/i })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /Open Debug Trace/i }))
    await waitFor(() => expect(screen.getByText(/"trace_id": "trace_dbg1"/i)).toBeInTheDocument())
  })
})
