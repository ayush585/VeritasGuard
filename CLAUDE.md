# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VeritasGuard is a multi-lingual misinformation verification system built for the Mistral AI Worldwide Hackathon (48-hour build). It uses 8 coordinated AI agents to verify claims in Indian languages (Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, English) and return verdicts translated back to the original language.

## Tech Stack

- **Backend:** Python (FastAPI + uvicorn), Mistral AI SDK, SQLAlchemy (SQLite), langdetect, pytesseract, Pillow
- **Frontend:** React 18 + Vite, Axios
- **External APIs:** Mistral AI (agents, vision/Pixtral, translation), Google Custom Search (optional)

## Commands

```bash
# Backend
pip install -r requirements.txt
python server/main.py                    # Runs FastAPI on port 8000

# Frontend
cd frontend && npm install
cd frontend && npm run dev               # Vite dev server

# System dependency for OCR
# Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam
# Mac: brew install tesseract tesseract-lang
```

## Architecture

### Agent Pipeline (Orchestrator)

The system runs a sequential-then-parallel pipeline coordinated by `server/orchestrator.py`:

1. **Stage 1 (sequential):** Language Detection → Translation → Claim Extraction
2. **Stage 2 (parallel):** Source Verification, Media Forensics, Context/History, Expert Validation run concurrently via `asyncio.gather`
3. **Stage 3 (sequential):** Verdict agent synthesizes all findings, translates summary back to original language

### Base Agent Pattern

All 8 agents inherit from `server/agents/base_agent.py` (abstract base class). Each agent:
- Creates a Mistral agent on init via `mistral.beta.agents.create()`
- Implements `get_instructions()` (system prompt) and `process(data: dict) -> dict`
- Uses `_query(prompt)` to interact with its Mistral agent

### API Endpoints

- `POST /verify/text` — accepts form data with `text` field, returns `verification_id`
- `POST /verify/image` — accepts file upload, returns `verification_id`
- `GET /result/{vid}` — poll for verification result (status: processing/completed/error)

### Frontend Flow

React app submits text → polls `/result/{vid}` every 1 second → displays verdict with confidence and native-language summary.

## Environment Variables

```
MISTRAL_API_KEY=...          # Required
GOOGLE_API_KEY=...           # Optional (for source verification)
GOOGLE_SEARCH_ENGINE_ID=...  # Optional (for source verification)
```

## Key Implementation Notes

- Mistral often returns malformed JSON — use `parse_json_safe()` with markdown stripping and regex fallback
- Cache Mistral agent IDs; don't recreate agents on every request
- All agent calls must be async
- Media Forensics uses Pixtral (`pixtral-large-latest`) for vision analysis
- Language detection uses `langdetect` library with Unicode heuristic fallback
- Known hoaxes are seeded into SQLite via `server/database.py`

## Priority Order

P0 (must work): Language Detection, Translation, Claim Extraction, Verdict, basic web UI, end-to-end text flow
P1 (important): Source Verification (web search), Image OCR, Context/History
P2 (nice to have): Expert Validation, expanded language support, polished UI
