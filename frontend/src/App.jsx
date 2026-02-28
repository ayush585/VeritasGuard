import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchResultAudio, getResult, submitImage, submitText } from './utils/api'

const STAGES = [
  { key: 'language_detection', label: 'Detecting Language' },
  { key: 'translation', label: 'Translating to English' },
  { key: 'claim_extraction', label: 'Extracting Claims' },
  { key: 'verification', label: 'Parallel Verification' },
  { key: 'verdict', label: 'Synthesizing Verdict' },
]

const VERDICT_COLORS = {
  TRUE: '#159947',
  MOSTLY_TRUE: '#52c468',
  PARTIALLY_TRUE: '#d1a114',
  UNVERIFIABLE: '#6f8291',
  MOSTLY_FALSE: '#f27a3f',
  FALSE: '#de3f3f',
}

function App() {
  const [input, setInput] = useState('')
  const [mode, setMode] = useState('text')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [stage, setStage] = useState(null)
  const [error, setError] = useState(null)
  const [audioLoading, setAudioLoading] = useState(false)
  const [audioError, setAudioError] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)

  const pollRef = useRef(null)
  const audioRef = useRef(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (audioUrl) URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  useEffect(() => {
    setAudioError(null)
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
    }
  }, [result?.verification_id])

  const stageIndex = useMemo(() => STAGES.findIndex((x) => x.key === stage), [stage])

  const startPolling = (verificationId) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await getResult(verificationId)
        setStage(res.stage || null)
        if (res.status === 'completed' || res.status === 'error') {
          clearInterval(pollRef.current)
          pollRef.current = null
          setResult(res)
          setLoading(false)
        }
      } catch {
        // Keep polling until timeout from backend flow.
      }
    }, 1000)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setResult(null)
    setLoading(true)
    setStage('language_detection')
    setAudioError(null)

    try {
      let data
      if (mode === 'text') {
        if (!input.trim()) {
          setLoading(false)
          return
        }
        data = await submitText(input)
      } else {
        if (!file) {
          setLoading(false)
          return
        }
        data = await submitImage(file)
      }
      startPolling(data.verification_id)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setLoading(false)
    }
  }

  const handlePlayAudio = async () => {
    if (!result?.verification_id || result?.audio_available === false) return
    setAudioError(null)
    setAudioLoading(true)

    try {
      if (!audioUrl) {
        const blob = await fetchResultAudio(result.verification_id)
        const url = URL.createObjectURL(blob)
        setAudioUrl(url)
        setTimeout(() => {
          if (audioRef.current) audioRef.current.play().catch(() => {})
        }, 40)
      } else if (audioRef.current) {
        await audioRef.current.play()
      }
    } catch (err) {
      setAudioError(err.response?.data?.detail || 'Unable to play audio.')
    } finally {
      setAudioLoading(false)
    }
  }

  const verdictColor = result?.verdict ? VERDICT_COLORS[result.verdict] || '#6f8291' : null

  return (
    <div className="app">
      <header>
        <h1>VeritasGuard</h1>
        <p className="subtitle">Mistral-first multilingual misinformation verification</p>
      </header>

      <main>
        <form onSubmit={handleSubmit} className="entry-card">
          <div className="mode-toggle">
            <button
              type="button"
              className={mode === 'text' ? 'active' : ''}
              onClick={() => setMode('text')}
            >
              Text
            </button>
            <button
              type="button"
              className={mode === 'image' ? 'active' : ''}
              onClick={() => setMode('image')}
            >
              Image
            </button>
          </div>

          {mode === 'text' ? (
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Paste a claim to verify (supports all scheduled Indian languages + English)"
              rows={4}
              disabled={loading}
            />
          ) : (
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={loading}
            />
          )}

          <button type="submit" className="submit" disabled={loading}>
            {loading ? 'Verifying…' : 'Verify'}
          </button>
        </form>

        {loading && (
          <div className="progress animated-card">
            <h3>Agent Pipeline</h3>
            <div className="stages">
              {STAGES.map((s, idx) => {
                let status = 'pending'
                if (idx < stageIndex) status = 'done'
                else if (idx === stageIndex) status = 'active'
                return (
                  <div key={s.key} className={`stage ${status}`}>
                    <span className="dot" />
                    <span>{s.label}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {error && <div className="error animated-card">{error}</div>}

        {result && result.status === 'completed' && (
          <div className="result animated-card">
            <div className="verdict-badge" style={{ background: verdictColor }}>
              {result.verdict}
            </div>

            <div className="confidence">
              <span>Confidence:</span>
              <div className="bar">
                <div
                  className="fill"
                  style={{
                    width: `${(result.confidence || 0) * 100}%`,
                    background: verdictColor,
                  }}
                />
              </div>
              <span>{Math.round((result.confidence || 0) * 100)}%</span>
            </div>

            {result.native_summary && result.detected_language !== 'en' && (
              <div className="summary native">
                <h4>Summary ({result.detected_language?.toUpperCase()})</h4>
                <p>{result.native_summary}</p>
              </div>
            )}

            <div className="summary">
              <h4>Summary (EN)</h4>
              <p>{result.summary}</p>
            </div>

            <div className="meta-grid">
              <div className="meta-item">
                <span className="label">Input Type</span>
                <span>{result.input_type || mode}</span>
              </div>
              <div className="meta-item">
                <span className="label">Search Provider</span>
                <span>{result.search_provider || 'n/a'}</span>
              </div>
              <div className="meta-item">
                <span className="label">Search Results</span>
                <span>{result.search_results_count ?? 0}</span>
              </div>
              <div className="meta-item">
                <span className="label">Audio</span>
                <span>{result.audio_status || 'n/a'}</span>
              </div>
            </div>

            <div className="audio-controls">
              <button
                type="button"
                className="audio-btn"
                disabled={audioLoading || !result.audio_available}
                onClick={handlePlayAudio}
              >
                {audioLoading ? 'Loading Audio…' : 'Play Verdict Audio'}
              </button>
              {audioUrl && <audio ref={audioRef} src={audioUrl} controls preload="none" />}
              {audioError && <p className="inline-error">{audioError}</p>}
              {!audioError && result.audio_message && <p className="audio-note">{result.audio_message}</p>}
            </div>

            {result.claims && result.claims.length > 0 && (
              <div className="claims">
                <h4>Extracted Claims</h4>
                <ul>
                  {result.claims.map((c, i) => (
                    <li key={i}>{typeof c === 'string' ? c : c.claim || JSON.stringify(c)}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.key_evidence && result.key_evidence.length > 0 && (
              <div className="evidence">
                <h4>Key Evidence</h4>
                <ul>
                  {result.key_evidence.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.warnings?.length > 0 && (
              <div className="warnings">
                <h4>Warnings</h4>
                <ul>
                  {result.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            <details className="raw">
              <summary>Raw Agent Data</summary>
              <pre>{JSON.stringify(result, null, 2)}</pre>
            </details>
          </div>
        )}

        {result && result.status === 'error' && <div className="error animated-card">Error: {result.error}</div>}
      </main>

      <footer>
        <p>Built for the Mistral AI Worldwide Hackathon</p>
      </footer>
    </div>
  )
}

export default App
