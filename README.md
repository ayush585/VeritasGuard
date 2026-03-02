# VeritasGuard

**VeritasGuard is a Mistral-first multilingual misinformation firewall for WhatsApp and web verification.**

It verifies suspicious forwards quickly, explains verdicts clearly, and surfaces evidence with traceable reasoning artifacts.

## 1) Hero + Positioning

**One-line pitch:**  
WhatsApp forwards can trigger panic, violence, and public-health harm. VeritasGuard verifies them in local languages with evidence-backed verdicts.

**Positioning:**  
VeritasGuard is purpose-built for the Mistral ecosystem and designed to showcase Mistral-native strengths end-to-end: multilingual reasoning, orchestration, and explainable synthesis.

**Two product tracks:**
- Consumer: WhatsApp-first verification assistant
- Institutional: API + debug trace + consensus artifacts for fact-check and monitoring teams

## 2) Problem Statement (Why This Is Urgent)

Misinformation is not just a content-quality issue. It is a speed, language, and trust issue with real-world consequences. Harmful rumors often spread faster than verification can catch up, especially in non-English channels.

### India Urgency Signals
- India has one of the largest WhatsApp user bases globally (`500M+` scale context, externally reported estimate).
- High forward rates and low verification behavior create high-risk virality patterns.
- Elections, communal fault lines, and public-health misinformation make this a recurring high-stakes challenge.

### Representative Harmful Rumor Types
- "Water poisoning" rumors triggering communal panic
- "Doctors harvesting organs" rumors targeting healthcare systems
- "Child kidnappers in white vans" rumors triggering mob incidents
- "Fake cure" medical rumors delaying legitimate treatment

### Global Relevance
The underlying pattern is global, not local: similar misinformation-driven harms have been reported across Brazil, Myanmar, Mexico, parts of the Middle East, and African public-health contexts.

**Attribution note:**  
Figures and incident references in this section are externally reported estimates and should be interpreted as directional risk indicators.

## 3) Solution Statement (How VeritasGuard Responds)

VeritasGuard intercepts harmful virality by verifying claims in local languages quickly, then returning a verdict with confidence, rationale, and source evidence.

### Pipeline (Plain English)
Language detection -> Translation -> Claim extraction -> Multi-signal verification -> Verdict -> Back-translation

### Mistral-First Value in Each Step Cluster
- **Multilingual reasoning:** Mistral-first handling for mixed-language and regional-language claim understanding.
- **Tool-capable orchestration:** Retrieval and verification flow is designed around Mistral-compatible tool and fallback pathways.
- **Explainable synthesis:** Final verdict and rationale generation is optimized for clear, human-readable outputs.

### Output Contract (Trust by Design)
Every completed result targets:
- verdict class (`TRUE`, `FALSE`, `MISLEADING`, `UNVERIFIABLE`)
- confidence score
- concise "why" summary
- evidence links / source metadata
- warnings and degradation transparency when applicable

## 4) Expected Impact (Pilot Scope)

### Who Benefits Now
- Non-English speakers with limited fact-check access
- First-time smartphone users vulnerable to forwarded misinformation
- Communities exposed to high-velocity panic rumors

### Pilot-Level Measurable Outcomes
- Fast verification turnaround suitable for live user workflows
- Stable-profile reliability target for demo/pilot operations
- Explainability artifacts available for institutional review (`agent_votes`, consensus breakdown, debug trace)

### Institutional Impact Track
- Fact-check desks
- Public health misinformation response teams
- Election integrity monitoring groups

### Responsible Claim Framing
VeritasGuard is framed as **pilot-ready for a nationwide deployment pathway**, not full enterprise completion.

## 5) Why Mistral (Core Judge Section)

VeritasGuard is a **Mistral-first architecture**.  
The system is optimized for Mistral’s multilingual + tool-oriented ecosystem and designed to make technical novelty visible to judges.

### Mistral Ecosystem Mapping

| VeritasGuard Feature | Mistral Capability Used | VeritasGuard Outcome | Judge-Visible Value |
|---|---|---|---|
| Language detection and multilingual reasoning | Mistral chat models with multilingual prompt handling | Local-language claims enter one unified pipeline | Demonstrates multilingual robustness in real user inputs |
| Claim extraction and structured synthesis | Mistral reasoning-oriented prompt patterns | Noisy forwards become analyzable claims | Shows reasoning quality beyond generic summarization |
| Source verification orchestration | Mistral tool-capable chat path + adapter fallback | Evidence path stays structured under partial failures | Shows robust orchestration, not single-shot prompting |
| OCR/vision compatibility path | Mistral adapter capability detection for OCR/vision path | Image flow can use Mistral-first OCR when available | Shows multimodal readiness within one architecture |
| Multi-agent execution | Mistral-first agent execution with fallback-safe adapter | Stable behavior across SDK capability differences | Shows production-minded reliability engineering |
| Final verdict synthesis | Mistral-based rationale generation | Clear verdict + confidence + explanation | Makes model reasoning legible to judges and users |

### Mistral Value Unlock
- Mistral-first orchestration keeps behavior consistent across stages.
- Adapter compatibility preserves resilience across capability differences.
- VeritasGuard is explicitly built to highlight Mistral ecosystem strengths end-to-end.

## 6) Technical Novelty (Judge-Visible)

VeritasGuard does not stop at a single LLM answer. It exposes decision structure:

- 8-agent orchestration pipeline
- weighted consensus from multiple verification signals
- agent vote artifacts (`supports`, `refutes`, `mixed`, `insufficient`)
- evidence graph and decision path
- deterministic override metadata for high-risk known-hoax matches
- graceful degradation with complete schema (no silent failure payloads)

## 7) System Architecture

Input (WhatsApp or Web) -> Orchestrator -> Agent Stages -> Consensus -> Verdict -> Response

### Pipeline Stages
1. Language detection
2. Translation (when needed)
3. Claim extraction
4. Parallel signals
- source verification
- context/history
- expert validation
- media forensics (when applicable)
5. Consensus and verdict synthesis
6. Native-language response formatting

### Reliability Controls
- per-stage budgets and timeout-aware degradation
- structured warning and agent error capture
- deterministic known-hoax safety override
- fallback references when retrieval degrades

## 8) Demo Experience (WhatsApp + Command Center)

### WhatsApp Two-Step Flow
1. User sends suspicious claim.
2. Immediate ack:
- "Analyzing your message now... Verification ID: ..."
3. Final async reply:
- verdict + confidence
- rationale
- provider and source count
- top sources

**Judge script line:**  
What user sees: rapid response in chat.  
Mistral capability exercised: multilingual reasoning + orchestration.  
Trust artifact produced: confidence + evidence + structured rationale.

### Web Command Center Flow
1. Open `/verify`
2. Submit text or image
3. Show:
- live stage progression
- verdict card
- evidence panel
- consensus panel
- evidence graph
- debug drawer

**Judge script line:**  
What user sees: transparent, stage-by-stage verification logic.  
Mistral capability exercised: synthesis and structured reasoning outputs.  
Trust artifact produced: `agent_votes`, consensus breakdown, decision path.

### Fallback Flow
If async final reply is delayed, send:
- `status <verification_id>`

Example:
- `status 356f6b23-7822-4f8f-a378-47c1abafb78e`

## 9) Quick Start + Environment

### Prerequisites
- Python 3.10+
- Node.js 18+
- ngrok
- Twilio Sandbox for WhatsApp demo

### Install

Backend:

```powershell
cd C:\Users\mukhe\Downloads\VeritasGuard
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Frontend:

```powershell
cd C:\Users\mukhe\Downloads\VeritasGuard\frontend
npm install
```

### Environment Variables

Create `.env` in project root (or copy from `.env.example`):

```env
MISTRAL_API_KEY=...
TAVILY_API_KEY=...
ENABLE_TAVILY_SEARCH_FALLBACK=true
ENABLE_GOOGLE_SEARCH_FALLBACK=false

TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
WHATSAPP_VALIDATE_SIGNATURE=true

DATABASE_URL=sqlite:///veritasguard.db
ADMIN_API_KEY=<long-random-secret>

CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### Run Locally

Terminal 1 (backend):

```powershell
cd C:\Users\mukhe\Downloads\VeritasGuard
.\.venv\Scripts\activate
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 (frontend):

```powershell
cd C:\Users\mukhe\Downloads\VeritasGuard\frontend
npm run dev
```

Terminal 3 (ngrok):

```powershell
C:\ngrok-v3-stable-windows-amd64\ngrok.exe http 8000
```

Frontend URL:
- `http://localhost:5173`

### Common Failure Fixes
- WhatsApp gets ack but no final verdict:
  - verify `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are set in runtime
- Twilio webhook not reaching backend:
  - confirm ngrok URL in Twilio Sandbox settings
  - endpoint must be `POST https://<ngrok-domain>/webhook/whatsapp`
- Frontend cannot call backend:
  - set `VITE_API_BASE_URL` to backend URL where needed

## 10) API and Security

### Public Endpoints
- `POST /verify/text`
- `POST /verify/image`
- `GET /result/{id}`
- `POST /webhook/whatsapp`
- `GET /healthz`
- `GET /readyz`

### Protected Endpoints (`X-Admin-Key`)
- `GET /result/{id}/debug`
- `GET /ops/runtime`

### Security Controls
- Twilio signature validation (enabled by default)
- admin key protection for debug/ops surfaces
- verify/webhook route throttling
- media MIME/type and payload guardrails

## 11) Validation

Frontend checks:

```powershell
cd frontend
npm run build
npx vitest run
```

Backend benchmark:

```powershell
cd C:\Users\mukhe\Downloads\VeritasGuard
.\.venv\Scripts\activate
$env:PYTHONIOENCODING="utf-8"
python -m demo.test_cases --profile stable --timeout 60
```

Health checks:

```powershell
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

Target:
- stable profile pass rate >= 90%
- zero timeouts for stage demo profile

## 12) Deployment (Railway)

Recommended service split:
- `veritasguard-api` (FastAPI backend)
- `veritasguard-frontend` (Vite frontend)
- Railway Postgres service

Critical notes:
- frontend root directory must be `frontend`
- backend start command:
  - `python -m uvicorn server.main:app --host 0.0.0.0 --port $PORT`
- backend must receive Postgres `DATABASE_URL`
- Twilio webhook must point to deployed API `/webhook/whatsapp`

See:
- `RAILWAY_DEPLOYMENT.md`

## 13) Roadmap

Near-term:
- production WhatsApp sender onboarding
- stronger retrieval quality scoring
- institutional operations dashboard

Scale/compliance:
- queue/worker architecture for higher throughput
- role-based access controls
- audit and policy controls for enterprise rollout

## 14) Built With

- FastAPI
- SQLAlchemy
- Mistral API (Mistral-first orchestration path)
- Tavily (retrieval fallback path)
- Twilio WhatsApp Sandbox
- React + Vite + GSAP
- Railway deployment stack

## 15) Impact Data Notes

Reported figures and incident references in this README are directional estimates derived from public reporting, policy discourse, and fact-check ecosystem narratives.

Reference placeholders (add final links before formal submission):
- India WhatsApp user scale and forwarding behavior: `[citation needed before final submission]`
- Misinformation-linked violence/public harm incidents: `[citation needed before final submission]`
- Regional language misinformation spread patterns: `[citation needed before final submission]`
- Global country examples listed in Problem Statement: `[citation needed before final submission]`

## 16) Disclaimer

VeritasGuard provides evidence-backed assistance, not legal or medical advice.  
High-stakes decisions should still be reviewed with domain experts and official authorities.

