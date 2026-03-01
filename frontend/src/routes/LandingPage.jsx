import { useRef } from 'react'
import { useGsapContext, gsap } from '../hooks/useGsapContext'
import BrandLogo from '../components/BrandLogo'

function LandingPage({ navigate }) {
  const rootRef = useRef(null)

  useGsapContext(
    rootRef,
    () => {
      const tl = gsap.timeline({ defaults: { duration: 0.48, ease: 'power3.out' } })
      tl.from('.hero', { y: 18, opacity: 0 })
        .from('.impact-strip', { y: 16, opacity: 0 }, '-=0.26')
        .from('.pipeline-showcase', { y: 16, opacity: 0 }, '-=0.26')
        .from('.channel-cards .panel', { y: 14, opacity: 0, stagger: 0.08 }, '-=0.18')
    },
    []
  )

  return (
    <div className="page landing-page" ref={rootRef}>
      <header className="topbar">
        <BrandLogo title="VeritasGuard" subtitle="Public-interest verification infrastructure" />
        <button className="btn btn-primary" type="button" onClick={() => navigate('/verify')}>
          Run Live Verification
        </button>
      </header>

      <main className="landing-main">
        <section className="hero panel entering">
          <p className="eyebrow">Mistral-first misinformation defense</p>
          <h1>Multilingual trust firewall for viral claims</h1>
          <p>
            Forward suspicious text or image and get a verdict backed by source retrieval, consensus logic,
            and explainable evidence artifacts.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary" type="button" onClick={() => navigate('/verify')}>
              Verify Claim
            </button>
            <a className="btn btn-secondary" href="#pipeline">
              View 8-Agent Pipeline
            </a>
          </div>
        </section>

        <section className="impact-strip panel">
          <h2>From harmful virality to verified intervention</h2>
          <div className="impact-grid">
            <article>
              <h3>Before</h3>
              <p>Unverified forwards spread rapidly across language communities and trigger real harm.</p>
            </article>
            <article>
              <h3>Intervention</h3>
              <p>VeritasGuard orchestrates language, retrieval, context, and consensus in one flow.</p>
            </article>
            <article>
              <h3>After</h3>
              <p>Users and institutions receive evidence-backed verdicts with traceable reasoning.</p>
            </article>
          </div>
        </section>

        <section id="pipeline" className="pipeline-showcase panel">
          <h2>8-agent Mistral-centric verification engine</h2>
          <ol>
            <li>Language Detection</li>
            <li>Translation</li>
            <li>Claim Extraction</li>
            <li>Source Verification</li>
            <li>Context & History</li>
            <li>Expert Validation</li>
            <li>Media Forensics</li>
            <li>Verdict Synthesis</li>
          </ol>
        </section>

        <section className="channel-cards">
          <article className="panel">
            <h3>WhatsApp Channel</h3>
            <p>Production path for citizens: forward claim, receive multilingual verdict and top sources.</p>
          </article>
          <article className="panel">
            <h3>Command Center</h3>
            <p>Judge and institutional mode: evidence graph, agent votes, trace diagnostics, and debug bundle.</p>
          </article>
          <article className="panel">
            <h3>Institution API</h3>
            <p>Operational pathway for fact-check desks and high-risk misinformation monitoring units.</p>
          </article>
        </section>
      </main>
    </div>
  )
}

export default LandingPage
