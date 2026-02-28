# VeritasGuard - Claude Code Context

**PROJECT:** Multi-lingual Misinformation Verification System  
**TIMELINE:** 48 hours (Feb 28-Mar 1, 2026)  
**HACKATHON:** Mistral AI Worldwide Hackathon  
**BUILDER:** Solo, India-based  
**GOAL:** Win main prize ($25K) or Agent Skills award (robot)  

---

## CRITICAL SUCCESS FACTORS

**You win if:**
1. 8 agents verify misinformation in ANY Indian language
2. Demo works: Hindi text → 8 seconds → "FALSE" verdict in Hindi
3. Judges see: "This couldn't be built without Mistral"
4. Someone says: "This will save lives"

**You lose if:**
- Agents don't coordinate properly
- Demo freezes or crashes
- Can't handle Hindi/Tamil input
- Looks like generic fact-checker

---

## WHAT MISTRAL JUDGES WANT TO SEE

**MUST showcase:**
- ✅ Multi-agent coordination (their core product)
- ✅ Multi-lingual (competitive advantage vs OpenAI)
- ✅ Vision API (Pixtral for image OCR)
- ✅ Reasoning (claim verification)
- ✅ Agent handoffs (architecture demo)

**Bonus points:**
- Web search integration
- Real-time processing
- Production-ready code
- Clean architecture

---

## TECH STACK (NON-NEGOTIABLE)

### Backend
```
FastAPI==0.109.0
uvicorn==0.27.0
mistralai==1.0.0
pydantic==2.6.0
sqlalchemy==2.0.25
python-multipart==0.0.6
pillow==10.2.0
requests==2.31.0
langdetect==1.0.9
pytesseract==0.3.10
```

### Frontend
```
react@18.2.0
vite@5.0.11
axios@1.6.5
```

### External APIs
- Mistral AI (agents, vision, translation)
- Google Custom Search (optional, for source verification)
- ElevenLabs (optional stretch goal for audio)

---

## FILE STRUCTURE

```
veritasguard/
├── server/
│   ├── main.py                 # FastAPI app, API endpoints
│   ├── orchestrator.py         # Coordinates all 8 agents
│   ├── database.py             # SQLite setup, known hoaxes
│   ├── agents/
│   │   ├── base_agent.py       # Abstract base class
│   │   ├── language_detection.py
│   │   ├── translation.py
│   │   ├── claim_extraction.py
│   │   ├── source_verification.py
│   │   ├── media_forensics.py
│   │   ├── context_history.py
│   │   ├── expert_validation.py
│   │   └── verdict.py
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   ├── utils/
│   │   └── mistral_client.py   # Mistral API wrapper
│   └── data/
│       └── known_hoaxes.json   # Seed data
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── VerificationForm.jsx
│   │   │   ├── AgentProgress.jsx
│   │   │   └── ResultDisplay.jsx
│   │   └── utils/
│   │       └── api.js
│   └── package.json
│
├── demo/
│   ├── hindi_samples.txt
│   ├── tamil_samples.txt
│   └── fake_images/
│
├── .env
├── README.md
└── requirements.txt
```

---

## AGENT ARCHITECTURE

### Base Agent Pattern

**ALL agents must inherit from this:**

```python
from abc import ABC, abstractmethod
from mistralai import Mistral
import os

class BaseAgent(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.mistral = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        self.agent_id = self._create_agent()
    
    def _create_agent(self):
        agent = self.mistral.beta.agents.create(
            model="mistral-large-latest",
            name=self.name,
            description=self.description,
            instructions=self.get_instructions()
        )
        return agent.id
    
    @abstractmethod
    def get_instructions(self) -> str:
        """Return system prompt"""
        pass
    
    @abstractmethod
    async def process(self, data: dict) -> dict:
        """Process input, return result"""
        pass
    
    async def _query(self, prompt: str) -> str:
        response = self.mistral.beta.conversations.start(
            agent_id=self.agent_id,
            inputs=prompt
        )
        
        content = []
        for event in response.events:
            if event.type == "message.output":
                content.append(str(event.content))
        return "\n".join(content)
```

---

## THE 8 AGENTS (PRIORITY ORDER)

### 1. Language Detection Agent (P0 - CRITICAL)

**Purpose:** Detect language of input text

**Implementation:**
```python
from langdetect import detect

class LanguageDetectionAgent(BaseAgent):
    def get_instructions(self) -> str:
        return "Identify language: Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, English"
    
    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        
        try:
            lang_code = detect(text)
        except:
            lang_code = "unknown"
        
        lang_map = {
            "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
            "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati",
            "en": "English"
        }
        
        return {
            "language": lang_map.get(lang_code, "Unknown"),
            "code": lang_code,
            "agent": self.name
        }
```

---

### 2. Translation Agent (P0 - CRITICAL)

**Purpose:** Translate to English for analysis

**Mistral Prompt:**
```python
def get_instructions(self) -> str:
    return """Translate text from Hindi, Tamil, Telugu, Bengali, Marathi, 
    Gujarati to English. Preserve meaning exactly. Handle code-mixing 
    (Hinglish). Return ONLY translation."""

async def process(self, data: dict) -> dict:
    text = data.get("text", "")
    source_lang = data.get("source_language", "")
    
    if source_lang == "English":
        return {"english_text": text, "original": text}
    
    prompt = f"Translate this {source_lang} to English:\n\n{text}"
    english = await self._query(prompt)
    
    return {
        "english_text": english.strip(),
        "original_text": text,
        "agent": self.name
    }
```

---

### 3. Claim Extraction Agent (P0 - CRITICAL)

**Purpose:** Extract verifiable claims

**Mistral Prompt:**
```python
def get_instructions(self) -> str:
    return """Extract factual claims that can be verified. 
    Ignore opinions. Return JSON array."""

async def process(self, data: dict) -> dict:
    text = data.get("english_text", "")
    
    prompt = f"""Extract claims from this text.
    
Text: {text}

Return JSON:
{{"claims": ["claim1", "claim2"], "primary": "main claim"}}
"""
    
    response = await self._query(prompt)
    
    # Parse JSON
    import json, re
    clean = response.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0]
    
    try:
        data = json.loads(clean.strip())
        claims = data.get("claims", [text])
        primary = data.get("primary", claims[0] if claims else text)
    except:
        claims = [text]
        primary = text
    
    return {
        "claims": claims,
        "primary_claim": primary,
        "agent": self.name
    }
```

---

### 4. Source Verification Agent (P1 - IMPORTANT)

**Purpose:** Web search to verify claim

**Implementation:**
```python
import requests

def _web_search(self, query: str) -> list:
    """Google Custom Search API"""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    cx = os.environ.get("GOOGLE_SEARCH_ENGINE_ID", "")
    
    if not api_key:
        return []
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": 5}
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        items = resp.json().get("items", [])
        return [{"title": i["title"], "snippet": i["snippet"]} for i in items]
    except:
        return []

async def process(self, data: dict) -> dict:
    claim = data.get("primary_claim", "")
    results = self._web_search(claim)
    
    if not results:
        return {"verdict": "UNVERIFIABLE", "reason": "No search results"}
    
    # Analyze with Mistral
    prompt = f"""Based on these search results, is this claim TRUE or FALSE?

Claim: {claim}

Results:
{self._format_results(results)}

Return JSON: {{"verdict": "TRUE/FALSE/MISLEADING", "confidence": 0.0-1.0, "reasoning": "..."}}
"""
    
    response = await self._query(prompt)
    # Parse JSON...
    
    return parsed_verdict
```

---

### 5. Media Forensics Agent (P1 - IMPORTANT)

**Purpose:** OCR from images, detect manipulation

**For Images:**
```python
import pytesseract
from PIL import Image
import base64

async def process(self, data: dict) -> dict:
    if data.get("type") != "image":
        return {"applicable": False}
    
    image_path = data.get("image_path")
    
    # OCR
    img = Image.open(image_path)
    text_eng = pytesseract.image_to_string(img, lang='eng')
    text_hin = pytesseract.image_to_string(img, lang='hin')
    extracted = text_eng if len(text_eng) > len(text_hin) else text_hin
    
    # Vision analysis with Mistral
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    
    vision_prompt = """Analyze this image:
1. Does it have overlaid text?
2. Signs of manipulation?
3. Content description?

Return JSON: {"has_overlay": bool, "manipulation_signs": [], "description": ""}
"""
    
    # Use Mistral vision model
    vision_response = self.mistral.chat.complete(
        model="pixtral-large-latest",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": vision_prompt},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"}
            ]
        }]
    )
    
    analysis = vision_response.choices[0].message.content
    
    return {
        "extracted_text": extracted,
        "vision_analysis": analysis,
        "agent": self.name
    }
```

---

### 6. Context & History Agent (P2 - NICE TO HAVE)

**Purpose:** Match against known hoaxes

**Implementation:**
```python
from database import SessionLocal, KnownHoax

async def process(self, data: dict) -> dict:
    claim = data.get("primary_claim", "")
    
    # Check database
    db = SessionLocal()
    hoaxes = db.query(KnownHoax).all()
    db.close()
    
    # Simple keyword matching
    for hoax in hoaxes:
        if any(word in claim.lower() for word in hoax.claim.lower().split()):
            return {
                "is_known_hoax": True,
                "matched_hoax": hoax.claim,
                "impact": hoax.impact,
                "agent": self.name
            }
    
    return {"is_known_hoax": False, "agent": self.name}
```

---

### 7. Expert Validation Agent (P2 - NICE TO HAVE)

**Purpose:** Check against authoritative sources

**Mistral Prompt:**
```python
def get_instructions(self) -> str:
    return """Check claims against WHO, government sites, research papers.
    Identify if medical/political/scientific claim."""

async def process(self, data: dict) -> dict:
    claim = data.get("primary_claim", "")
    
    prompt = f"""Is this claim supported by expert sources (WHO, CDC, govt)?

Claim: {claim}

Return JSON: {{"expert_supported": bool, "reasoning": "..."}}
"""
    
    response = await self._query(prompt)
    # Parse and return
```

---

### 8. Verdict Agent (P0 - CRITICAL)

**Purpose:** Synthesize all findings, translate back

**Mistral Prompt:**
```python
def get_instructions(self) -> str:
    return """Synthesize evidence into final verdict. 
    Provide clear explanation in simple language."""

async def process(self, data: dict) -> dict:
    claim = data.get("claim", {})
    verifications = data.get("verifications", [])
    original_lang = data.get("original_language", "English")
    
    # Compile evidence
    evidence = "\n".join([
        f"- {v.get('agent', 'Agent')}: {v.get('verdict', v.get('reasoning', 'N/A'))}"
        for v in verifications
    ])
    
    prompt = f"""Final verdict on this claim:

Claim: {claim.get('primary_claim')}

Evidence:
{evidence}

Return JSON:
{{
    "verdict": "TRUE/FALSE/MISLEADING/UNVERIFIABLE",
    "confidence": 0.0-1.0,
    "summary": "brief explanation",
    "recommendation": "what user should do"
}}
"""
    
    response = await self._query(prompt)
    verdict_data = self._parse_json(response)
    
    # Translate back to original language
    if original_lang != "English":
        translate_prompt = f"Translate to {original_lang}: {verdict_data['summary']}"
        translated = await self._query(translate_prompt)
        verdict_data["summary_native"] = translated.strip()
    
    return verdict_data
```

---

## ORCHESTRATOR

**Coordinates all agents:**

```python
import asyncio
from typing import Dict
import uuid

class VerificationOrchestrator:
    def __init__(self):
        self.agents = {
            "language": LanguageDetectionAgent(),
            "translation": TranslationAgent(),
            "claim": ClaimExtractionAgent(),
            "source": SourceVerificationAgent(),
            "media": MediaForensicsAgent(),
            "context": ContextHistoryAgent(),
            "expert": ExpertValidationAgent(),
            "verdict": VerdictAgent()
        }
        self.results = {}
    
    async def verify(self, input_data: dict) -> str:
        """Main verification pipeline"""
        vid = str(uuid.uuid4())
        self.results[vid] = {"status": "processing", "stages": {}}
        
        try:
            # Stage 1: Language
            lang_result = await self.agents["language"].process(input_data)
            self.results[vid]["stages"]["language"] = lang_result
            
            # Stage 2: Translation
            trans_input = {**input_data, "source_language": lang_result["language"]}
            trans_result = await self.agents["translation"].process(trans_input)
            self.results[vid]["stages"]["translation"] = trans_result
            
            # Stage 3: Claim
            claim_result = await self.agents["claim"].process(trans_result)
            self.results[vid]["stages"]["claim"] = claim_result
            
            # Stage 4: Parallel verification
            tasks = [
                self.agents["source"].process(claim_result),
                self.agents["media"].process(input_data),
                self.agents["context"].process(claim_result),
                self.agents["expert"].process(claim_result)
            ]
            parallel = await asyncio.gather(*tasks)
            self.results[vid]["stages"]["verifications"] = parallel
            
            # Stage 5: Verdict
            verdict_input = {
                "claim": claim_result,
                "verifications": parallel,
                "original_language": lang_result["language"]
            }
            verdict = await self.agents["verdict"].process(verdict_input)
            self.results[vid]["final_verdict"] = verdict
            self.results[vid]["status"] = "completed"
            
        except Exception as e:
            self.results[vid]["status"] = "error"
            self.results[vid]["error"] = str(e)
        
        return vid
    
    def get_result(self, vid: str) -> dict:
        return self.results.get(vid, {})
```

---

## FASTAPI ENDPOINTS

```python
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="VeritasGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

orchestrator = VerificationOrchestrator()

@app.post("/verify/text")
async def verify_text(text: str = Form(...)):
    vid = await orchestrator.verify({"text": text, "type": "text"})
    return {"verification_id": vid}

@app.post("/verify/image")
async def verify_image(file: UploadFile = File(...)):
    import os
    os.makedirs("temp", exist_ok=True)
    path = f"temp/{file.filename}"
    
    with open(path, "wb") as f:
        f.write(await file.read())
    
    vid = await orchestrator.verify({"image_path": path, "type": "image"})
    return {"verification_id": vid}

@app.get("/result/{vid}")
async def get_result(vid: str):
    return orchestrator.get_result(vid)

@app.get("/")
async def root():
    return {"status": "VeritasGuard API Online"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## DATABASE SETUP

```python
from sqlalchemy import create_engine, Column, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class KnownHoax(Base):
    __tablename__ = "known_hoaxes"
    id = Column(String, primary_key=True)
    claim = Column(String)
    impact = Column(String)
    first_seen = Column(DateTime)

engine = create_engine('sqlite:///veritasguard.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# Seed data
def seed_hoaxes():
    db = SessionLocal()
    if db.query(KnownHoax).count() > 0:
        db.close()
        return
    
    hoaxes = [
        KnownHoax(
            id="h1",
            claim="Muslims poisoning water supply",
            impact="5 people lynched in 2018",
            first_seen=datetime(2018, 1, 1)
        ),
        KnownHoax(
            id="h2",
            claim="Doctors harvesting organs",
            impact="Mob attacks on hospitals",
            first_seen=datetime(2019, 3, 1)
        )
    ]
    
    for h in hoaxes:
        db.add(h)
    db.commit()
    db.close()

seed_hoaxes()
```

---

## REACT FRONTEND

### App.jsx

```jsx
import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('text', text);

      const { data } = await axios.post('http://localhost:8000/verify/text', formData);
      const vid = data.verification_id;

      // Poll for result
      const interval = setInterval(async () => {
        const res = await axios.get(`http://localhost:8000/result/${vid}`);
        
        if (res.data.status === 'completed') {
          setResult(res.data);
          setLoading(false);
          clearInterval(interval);
        }
      }, 1000);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const getVerdictColor = (v) => {
    if (v === 'FALSE') return '#ff4444';
    if (v === 'TRUE') return '#44ff44';
    return '#ffaa44';
  };

  return (
    <div className="app">
      <h1>🛡️ VeritasGuard</h1>
      <p>Multi-lingual Misinformation Verification</p>

      {!loading && !result && (
        <form onSubmit={handleSubmit}>
          <textarea
            placeholder="Paste suspicious message (any language)..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
          />
          <button type="submit">🔍 Verify</button>
        </form>
      )}

      {loading && (
        <div className="loading">
          <h2>Analyzing with 8 AI Agents...</h2>
          <div className="agents">
            {['Language', 'Translation', 'Claim', 'Source', 'Media', 'Context', 'Expert', 'Verdict'].map(a => (
              <div key={a} className="agent">{a} ⏳</div>
            ))}
          </div>
        </div>
      )}

      {result && (
        <div className="result" style={{ borderColor: getVerdictColor(result.final_verdict?.verdict) }}>
          <h2>{result.final_verdict?.verdict || 'UNKNOWN'}</h2>
          <p><strong>Confidence:</strong> {(result.final_verdict?.confidence * 100).toFixed(0)}%</p>
          <p>{result.final_verdict?.summary}</p>
          {result.final_verdict?.summary_native && (
            <p><em>{result.final_verdict.summary_native}</em></p>
          )}
          <button onClick={() => setResult(null)}>Verify Another</button>
        </div>
      )}
    </div>
  );
}

export default App;
```

---

## ENVIRONMENT VARIABLES

```bash
# .env
MISTRAL_API_KEY=your_mistral_key_here
GOOGLE_API_KEY=your_google_key_here  # Optional
GOOGLE_SEARCH_ENGINE_ID=your_cx_here  # Optional
```

---

## DEMO DATA

### Hindi Test Cases

```python
# demo/test_cases.py
DEMO_CASES = [
    {
        "text": "मुस्लिम लोग पानी में जहर मिला रहे हैं। शेयर करें।",
        "language": "Hindi",
        "expected": "FALSE",
        "note": "Known hoax - caused 5 deaths in 2018"
    },
    {
        "text": "இந்த மருத்துவர் உறுப்புகளை அறுவடை செய்கிறார்",
        "language": "Tamil", 
        "expected": "FALSE",
        "note": "Doctor organ harvesting hoax"
    }
]
```

---

## CRITICAL REMINDERS

### DO:
- ✅ Test with REAL Hindi/Tamil text immediately
- ✅ Handle JSON parsing errors gracefully (Mistral responses vary)
- ✅ Add try-except everywhere
- ✅ Cache Mistral agent IDs (don't recreate every time)
- ✅ Use async/await for all agent calls
- ✅ Keep prompts simple and clear
- ✅ Test the DEMO FLOW specifically

### DON'T:
- ❌ Over-engineer the UI (basic is fine)
- ❌ Spend time on fancy animations
- ❌ Build video analysis (too complex for 48h)
- ❌ Try to support ALL 22 languages (focus on Hindi/Tamil/English)
- ❌ Add user accounts or auth
- ❌ Deploy to cloud (local is fine)

---

## PRIORITY LEVELS

**P0 (MUST WORK FOR DEMO):**
- Language detection (Hindi, Tamil, English)
- Translation to/from English
- Claim extraction
- Verdict generation
- Basic web UI
- One complete text verification flow

**P1 (IMPORTANT):**
- Source verification (web search)
- Image OCR
- Context/history checking
- Better error handling

**P2 (NICE TO HAVE):**
- Expert validation
- All 22 languages
- Pretty UI animations
- Audio support (ElevenLabs)

**P3 (SKIP IF TIME TIGHT):**
- Video analysis
- User accounts
- Deployment
- Advanced caching

---

## SUCCESS METRICS

**Minimum Viable Demo:**
- [ ] Input Hindi text: "मुस्लिम लोग पानी में जहर मिला रहे हैं"
- [ ] System detects language: Hindi
- [ ] Translates to English
- [ ] Verifies claim (web search or knowledge)
- [ ] Returns verdict: FALSE
- [ ] Shows Hindi summary: "यह झूठी खबर है"
- [ ] Total time: < 15 seconds

**If that works, you can win.**

---

## COMMON ISSUES & FIXES

### Issue: Mistral returns malformed JSON

```python
def parse_json_safe(text: str) -> dict:
    import json, re
    # Remove markdown
    clean = text.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0]
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0]
    
    # Try parse
    try:
        return json.loads(clean.strip())
    except:
        # Fallback: regex extract
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    
    return {}
```

### Issue: pytesseract not installed

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam

# Mac
brew install tesseract tesseract-lang
```

### Issue: Language detection fails

```python
# Fallback to manual detection
def detect_language_fallback(text: str) -> str:
    # Simple heuristic
    if any(c in text for c in ['ा', 'े', 'ी']):
        return "Hindi"
    if any(c in text for c in ['ா', 'ி', 'ு']):
        return "Tamil"
    return "English"
```

---

## FINAL CHECKLIST

**Before Demo:**
- [ ] Test with 3 Hindi samples
- [ ] Test with 1 Tamil sample
- [ ] Test with 1 English sample
- [ ] Verify translation accuracy
- [ ] Check verdict makes sense
- [ ] Time the full flow (< 15 sec)
- [ ] Record backup video
- [ ] Prepare pitch (3 min)

**During Demo:**
- [ ] Show problem (misinformation kills)
- [ ] Show Hindi input
- [ ] Watch agents work
- [ ] Show verdict in Hindi
- [ ] Explain impact
- [ ] Thank judges

**If Demo Fails:**
- [ ] Play backup video
- [ ] Explain what it does
- [ ] Show code architecture
- [ ] Answer questions confidently

---

## BUILD ORDER (48 HOURS)

**Saturday 10am-2am (16 hours):**
1. Setup (1h): Environment, dependencies, project structure
2. Base Agent (1h): Abstract class working
3. Agents 1-3 (3h): Language, Translation, Claim - CRITICAL PATH
4. Orchestrator (2h): Basic pipeline connecting 3 agents
5. Agent 8 (2h): Verdict - CRITICAL PATH
6. FastAPI (2h): Basic endpoints working
7. Test (1h): End-to-end with Hindi text
8. Agents 4-7 (3h): Source, Media, Context, Expert
9. Integration (1h): All agents in orchestrator

**Sunday 9am-5pm (8 hours):**
1. Frontend (3h): React app with form + results
2. Testing (2h): All demo cases
3. Polish (1h): UI, error handling
4. Demo Prep (2h): Practice, video backup

---

**NOW BUILD. FOCUS ON P0 FIRST. DEMO OVER PERFECTION.**
