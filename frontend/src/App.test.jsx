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
    fetchResultAudio: vi.fn(),
  }
})

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders completed verification payload from polling', async () => {
    api.submitText.mockResolvedValue({ verification_id: 'abc123' })
    api.getResult.mockResolvedValue({
      verification_id: 'abc123',
      status: 'completed',
      stage: 'done',
      verdict: 'FALSE',
      confidence: 0.82,
      summary: 'Claim is false.',
      native_summary: 'दावा गलत है।',
      detected_language: 'hi',
      claims: [{ claim: 'x' }],
      key_evidence: ['source mismatch'],
      search_provider: 'mistral_web_search',
      search_results_count: 3,
      audio_available: false,
      audio_status: 'disabled',
      audio_message: 'ElevenLabs credentials are not configured.',
    })

    render(<App />)
    fireEvent.change(screen.getByPlaceholderText(/Paste a claim to verify/i), {
      target: { value: 'some claim' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verify' }))

    await waitFor(() => {
      expect(screen.getByText('Summary (EN)')).toBeInTheDocument()
      expect(screen.getByText('Claim is false.')).toBeInTheDocument()
      expect(screen.getByText('mistral_web_search')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  test('loads and plays audio when available', async () => {
    api.submitText.mockResolvedValue({ verification_id: 'a1' })
    api.getResult.mockResolvedValue({
      verification_id: 'a1',
      status: 'completed',
      stage: 'done',
      verdict: 'TRUE',
      confidence: 0.91,
      summary: 'True claim.',
      native_summary: 'True claim.',
      detected_language: 'en',
      claims: [],
      key_evidence: [],
      search_provider: 'mistral_web_search',
      search_results_count: 2,
      audio_available: true,
      audio_status: 'ready',
      audio_message: 'Audio ready.',
    })
    api.fetchResultAudio.mockResolvedValue(new Blob(['audio'], { type: 'audio/mpeg' }))

    render(<App />)
    fireEvent.change(screen.getByPlaceholderText(/Paste a claim to verify/i), {
      target: { value: 'claim' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verify' }))

    await waitFor(() => expect(screen.getByRole('button', { name: /Play Verdict Audio/i })).toBeEnabled(), { timeout: 3000 })
    fireEvent.click(screen.getByRole('button', { name: /Play Verdict Audio/i }))

    await waitFor(() => expect(api.fetchResultAudio).toHaveBeenCalledWith('a1'), { timeout: 3000 })
  })
})
