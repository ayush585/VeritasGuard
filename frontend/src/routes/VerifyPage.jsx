import { useEffect, useReducer, useRef } from 'react'
import { fetchResultAudio, getResult, getResultDebug, submitImage, submitText } from '../utils/api'
import { useGsapContext, gsap } from '../hooks/useGsapContext'
import InputModule from '../components/InputModule'
import PipelinePanel from '../components/PipelinePanel'
import VerdictCard from '../components/VerdictCard'
import EvidencePanel from '../components/EvidencePanel'
import ConsensusPanel from '../components/ConsensusPanel'
import EvidenceGraphPanel from '../components/EvidenceGraphPanel'
import DebugDrawer from '../components/DebugDrawer'

const SAMPLE_CASES = [
  {
    key: 'hi_water',
    label: 'Hindi: communal water poisoning hoax',
    text: 'सावधान! मुस्लिम लोग पानी में जहर मिला रहे हैं, तुरंत शेयर करें।',
    mode: 'text',
  },
  {
    key: 'ta_garlic',
    label: 'Tamil: garlic prevents COVID',
    text: 'பூண்டு சாப்பிட்டால் கொரோனா வராது என்று கூறப்படுகிறது.',
    mode: 'text',
  },
  {
    key: 'en_microchip',
    label: 'English: vaccine microchip claim',
    text: 'The Indian government is secretly implanting microchips through COVID vaccines.',
    mode: 'text',
  },
  {
    key: 'bn_whatsapp_hack',
    label: 'Bengali: WhatsApp hack panic',
    text: 'WhatsApp মেসেজ খুললেই ফোন হ্যাক হয়ে যাবে, সবাইকে পাঠাও।',
    mode: 'text',
  },
  {
    key: 'mr_hot_water',
    label: 'Marathi: hot water COVID cure',
    text: 'दर १५ मिनिटांनी गरम पाणी पिल्याने कोरोना निघून जातो.',
    mode: 'text',
  },
  {
    key: 'te_5g',
    label: 'Telugu: 5G conspiracy',
    text: '5G టవర్ల వల్ల కరోనా వ్యాపిస్తుంది.',
    mode: 'text',
  },
]

const MAX_IMAGE_SIZE = 4 * 1024 * 1024

const initialState = {
  mode: 'text',
  input: '',
  file: null,
  loading: false,
  status: 'idle',
  stage: null,
  verificationId: null,
  result: null,
  error: null,
  inputError: null,
  debugPayload: null,
  loadingDebug: false,
  audioLoading: false,
  audioError: null,
  audioUrl: null,
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_MODE':
      return { ...state, mode: action.payload, inputError: null, error: null }
    case 'SET_INPUT':
      return { ...state, input: action.payload, inputError: null }
    case 'SET_FILE':
      return { ...state, file: action.payload, inputError: null }
    case 'SET_INPUT_ERROR':
      return { ...state, inputError: action.payload }
    case 'SUBMIT_START':
      return {
        ...state,
        loading: true,
        status: 'submitting',
        stage: 'language_detection',
        result: null,
        error: null,
        inputError: null,
        debugPayload: null,
        verificationId: null,
        audioError: null,
      }
    case 'SUBMIT_SUCCESS':
      return {
        ...state,
        verificationId: action.payload,
        status: 'polling',
      }
    case 'POLL_UPDATE':
      return { ...state, stage: action.payload.stage || state.stage }
    case 'COMPLETE':
      return {
        ...state,
        loading: false,
        status: action.payload.warnings?.length ? 'degraded' : 'completed',
        stage: action.payload.stage || 'done',
        result: action.payload,
      }
    case 'FAILED':
      return { ...state, loading: false, status: 'failed', error: action.payload, stage: 'error' }
    case 'SET_DEBUG_LOADING':
      return { ...state, loadingDebug: action.payload }
    case 'SET_DEBUG':
      return { ...state, debugPayload: action.payload, loadingDebug: false }
    case 'SET_AUDIO_LOADING':
      return { ...state, audioLoading: action.payload }
    case 'SET_AUDIO_ERROR':
      return { ...state, audioError: action.payload }
    case 'SET_AUDIO_URL':
      return { ...state, audioUrl: action.payload }
    default:
      return state
  }
}

function VerifyPage({ navigate }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const pollRef = useRef(null)
  const audioRef = useRef(null)
  const rootRef = useRef(null)

  useGsapContext(
    rootRef,
    () => {
      gsap
        .timeline({ defaults: { duration: 0.38, ease: 'power2.out' } })
        .from('.command-left > .panel', { y: 12, opacity: 0 })
        .from('.command-center-col > .panel', { y: 10, opacity: 0, stagger: 0.08 }, '-=0.16')
        .from('.command-right > .panel', { y: 10, opacity: 0, stagger: 0.08 }, '-=0.16')
        .from('.debug-row > .panel', { y: 8, opacity: 0 }, '-=0.12')
    },
    []
  )

  useGsapContext(
    rootRef,
    () => {
      if (!state.result) return
      gsap.fromTo(
        '.verdict-card',
        { opacity: 0.75, y: 8 },
        { opacity: 1, y: 0, duration: 0.32, ease: 'power2.out', clearProps: 'transform' }
      )
      gsap.fromTo(
        '.source-list li',
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, stagger: 0.05, duration: 0.26, ease: 'power2.out', clearProps: 'transform' }
      )
      gsap.fromTo(
        '.votes-table tbody tr',
        { opacity: 0, y: 6 },
        { opacity: 1, y: 0, stagger: 0.04, duration: 0.22, ease: 'power1.out', clearProps: 'transform' }
      )
    },
    [state.result?.verification_id]
  )

  useEffect(
    () => () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (state.audioUrl) URL.revokeObjectURL(state.audioUrl)
    },
    [state.audioUrl]
  )

  const stopPolling = () => {
    if (!pollRef.current) return
    clearInterval(pollRef.current)
    pollRef.current = null
  }

  const loadDebugPayload = async (verificationId) => {
    dispatch({ type: 'SET_DEBUG_LOADING', payload: true })
    try {
      const payload = await getResultDebug(verificationId)
      dispatch({ type: 'SET_DEBUG', payload })
    } catch {
      dispatch({ type: 'SET_DEBUG_LOADING', payload: false })
    }
  }

  const pollOnce = async (verificationId) => {
    try {
      const result = await getResult(verificationId)
      dispatch({ type: 'POLL_UPDATE', payload: result })
      if (result.status === 'completed') {
        stopPolling()
        dispatch({ type: 'COMPLETE', payload: result })
        loadDebugPayload(verificationId)
      } else if (result.status === 'error') {
        stopPolling()
        dispatch({ type: 'FAILED', payload: result.error || 'Verification failed.' })
      }
    } catch {
      // transient polling errors are ignored; timeout guard handles terminal state.
    }
  }

  const startPolling = (verificationId) => {
    const startedAt = Date.now()
    pollOnce(verificationId)
    pollRef.current = setInterval(async () => {
      if (Date.now() - startedAt > 70000) {
        stopPolling()
        dispatch({ type: 'FAILED', payload: 'Verification timed out. Please retry with a shorter claim.' })
        return
      }
      await pollOnce(verificationId)
    }, 1000)
  }

  const handleSubmit = async () => {
    dispatch({ type: 'SET_AUDIO_ERROR', payload: null })
    if (state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl)
      dispatch({ type: 'SET_AUDIO_URL', payload: null })
    }

    if (state.mode === 'text') {
      if (!state.input.trim()) {
        dispatch({ type: 'SET_INPUT_ERROR', payload: 'Please enter a claim before running verification.' })
        return
      }
    } else {
      if (!state.file) {
        dispatch({ type: 'SET_INPUT_ERROR', payload: 'Please upload an image before running verification.' })
        return
      }
      if (!['image/png', 'image/jpeg', 'image/webp'].includes(state.file.type)) {
        dispatch({ type: 'SET_INPUT_ERROR', payload: 'Unsupported image type. Use PNG, JPG, or WEBP.' })
        return
      }
      if (state.file.size > MAX_IMAGE_SIZE) {
        dispatch({ type: 'SET_INPUT_ERROR', payload: 'Image is too large. Keep it below 4MB for live demo reliability.' })
        return
      }
    }

    dispatch({ type: 'SUBMIT_START' })
    stopPolling()

    try {
      let data
      if (state.mode === 'text') {
        data = await submitText(state.input.trim())
      } else {
        data = await submitImage(state.file)
      }
      const verificationId = data.verification_id
      dispatch({ type: 'SUBMIT_SUCCESS', payload: verificationId })
      startPolling(verificationId)
    } catch (error) {
      dispatch({
        type: 'FAILED',
        payload: error?.response?.data?.detail || error.message || 'Unable to start verification.',
      })
    }
  }

  const handleUseSample = (sampleKey) => {
    const sample = SAMPLE_CASES.find((item) => item.key === sampleKey)
    if (!sample) return
    dispatch({ type: 'SET_MODE', payload: sample.mode })
    dispatch({ type: 'SET_INPUT', payload: sample.text })
    dispatch({ type: 'SET_FILE', payload: null })
  }

  const handlePlayAudio = async () => {
    const result = state.result
    if (!result?.verification_id || result.audio_available === false) return
    dispatch({ type: 'SET_AUDIO_ERROR', payload: null })
    dispatch({ type: 'SET_AUDIO_LOADING', payload: true })
    try {
      if (!state.audioUrl) {
        const blob = await fetchResultAudio(result.verification_id)
        const url = URL.createObjectURL(blob)
        dispatch({ type: 'SET_AUDIO_URL', payload: url })
        setTimeout(() => audioRef.current?.play?.(), 40)
      } else {
        await audioRef.current?.play?.()
      }
    } catch (error) {
      dispatch({ type: 'SET_AUDIO_ERROR', payload: error?.response?.data?.detail || 'Unable to play verdict audio.' })
    } finally {
      dispatch({ type: 'SET_AUDIO_LOADING', payload: false })
    }
  }

  return (
    <div className="page verify-page" ref={rootRef}>
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true" />
          <div>
            <strong>VeritasGuard Command Center</strong>
            <span>Built to interrupt harmful virality before escalation</span>
          </div>
        </div>
        <button className="btn btn-secondary" type="button" onClick={() => navigate('/')}>
          Back to Narrative
        </button>
      </header>

      <main className="command-layout">
        <div className="command-left">
          <InputModule
            mode={state.mode}
            onModeChange={(mode) => dispatch({ type: 'SET_MODE', payload: mode })}
            input={state.input}
            onInputChange={(value) => dispatch({ type: 'SET_INPUT', payload: value })}
            file={state.file}
            onFileChange={(value) => dispatch({ type: 'SET_FILE', payload: value })}
            loading={state.loading}
            inputError={state.inputError}
            onSubmit={handleSubmit}
            sampleCases={SAMPLE_CASES}
            onUseSample={handleUseSample}
          />
        </div>

        <div className="command-center-col">
          <PipelinePanel stage={state.stage} result={state.result} />
          {state.error ? (
            <section className="panel error-panel">
              <h3>Verification Error</h3>
              <p>{state.error}</p>
            </section>
          ) : (
            <VerdictCard
              result={state.result}
              audioLoading={state.audioLoading}
              audioError={state.audioError}
              audioUrl={state.audioUrl}
              audioRef={audioRef}
              onPlayAudio={handlePlayAudio}
            />
          )}
        </div>

        <div className="command-right">
          <EvidencePanel result={state.result} />
          <ConsensusPanel result={state.result} />
          <EvidenceGraphPanel result={state.result} />
        </div>
      </main>

      <div className="debug-row">
        <DebugDrawer result={state.result} debugPayload={state.debugPayload} loadingDebug={state.loadingDebug} />
      </div>
    </div>
  )
}

export default VerifyPage
