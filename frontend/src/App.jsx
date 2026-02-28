import { useState, useRef, useEffect } from 'react'
import { submitText, submitImage, getResult } from './utils/api'

const STAGES = [
  { key: 'language_detection', label: 'Detecting Language' },
  { key: 'translation', label: 'Translating' },
  { key: 'claim_extraction', label: 'Extracting Claims' },
  { key: 'verification', label: 'Verifying Sources' },
  { key: 'verdict', label: 'Synthesizing Verdict' },
]

const VERDICT_COLORS = {
  TRUE: '#22c55e',
  MOSTLY_TRUE: '#84cc16',
  PARTIALLY_TRUE: '#eab308',
  UNVERIFIABLE: '#a3a3a3',
  MOSTLY_FALSE: '#f97316',
  FALSE: '#ef4444',
}

function App() {
  const [input, setInput] = useState('')
  const [mode, setMode] = useState('text')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [stage, setStage] = useState(null)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const startPolling = (vid) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await getResult(vid)
        setStage(res.stage || null)
        if (res.status === 'completed' || res.status === 'error') {
          clearInterval(pollRef.current)
          pollRef.current = null
          setResult(res)
          setLoading(false)
        }
      } catch {
        // keep polling
      }
    }, 1000)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setResult(null)
    setLoading(true)
    setStage('language_detection')

    try {
      let data
      if (mode === 'text') {
        if (!input.trim()) return setLoading(false)
        data = await submitText(input)
      } else {
        if (!file) return setLoading(false)
        data = await submitImage(file)
      }
      startPolling(data.verification_id)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setLoading(false)
    }
  }

  const verdictColor = result?.verdict ? VERDICT_COLORS[result.verdict] || '#a3a3a3' : null

  return (
    <div className="app">
      <header>
        <h1>VeritasGuard</h1>
        <p className="subtitle">Multi-lingual Misinformation Verification</p>
      </header>

      <main>
        <form onSubmit={handleSubmit}>
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
              placeholder="Paste a claim to verify... (Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, or English)"
              rows={4}
              disabled={loading}
            />
          ) : (
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files[0])}
              disabled={loading}
            />
          )}

          <button type="submit" className="submit" disabled={loading}>
            {loading ? 'Verifying...' : 'Verify'}
          </button>
        </form>

        {loading && (
          <div className="progress">
            <h3>Agent Pipeline</h3>
            <div className="stages">
              {STAGES.map((s) => {
                const stageIdx = STAGES.findIndex((x) => x.key === stage)
                const thisIdx = STAGES.findIndex((x) => x.key === s.key)
                let status = 'pending'
                if (thisIdx < stageIdx) status = 'done'
                else if (thisIdx === stageIdx) status = 'active'
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

        {error && <div className="error">{error}</div>}

        {result && result.status === 'completed' && (
          <div className="result">
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

            <details className="raw">
              <summary>Raw Agent Data</summary>
              <pre>{JSON.stringify(result, null, 2)}</pre>
            </details>
          </div>
        )}

        {result && result.status === 'error' && (
          <div className="error">Error: {result.error}</div>
        )}
      </main>

      <footer>
        <p>Built for the Mistral AI Worldwide Hackathon</p>
      </footer>
    </div>
  )
}

export default App
