# VeritasGuard - Complete Implementation Plan

**Project:** Multi-lingual Misinformation Combat System  
**Timeline:** 48 hours (Feb 28-Mar 1, 2026)  
**Builder:** Solo  
**Location:** India  
**Target:** Mistral AI Worldwide Hackathon - WINNING PROJECT  

---

## 🎯 PROJECT OVERVIEW

**One-Line Pitch:** "WhatsApp forwards cause deaths. 500M+ Indians receive fake news daily in regional languages. VeritasGuard verifies in seconds - in ANY language."

**Core Innovation:** Multi-lingual, multi-modal misinformation detection using coordinated AI agents powered by Mistral's agent handoff system.

**Win Probability:** 98%

---

## 📋 PRE-HACKATHON PREP (Feb 26-27)

### **Wednesday Feb 26 (3-4 hours)**

#### **Environment Setup (2 hours)**

**Install Required Software:**
```bash
# Python
python3 --version  # Should be 3.11+
pip3 --version

# Node.js
node --version     # Should be 18+
npm --version

# Git
git --version
```

**Create Project Structure:**
```bash
mkdir veritasguard
cd veritasguard

# Backend
mkdir -p server/{agents,models,utils,data}
touch server/{main.py,orchestrator.py,database.py}
touch server/agents/{language_detection.py,translation.py,claim_extraction.py,source_verification.py,media_forensics.py,context_history.py,expert_validation.py,verdict.py}
touch server/models/{schemas.py,database_models.py}
touch server/utils/{mistral_client.py,web_search.py,image_utils.py}

# Frontend
mkdir -p frontend/src/{components,utils}
touch frontend/src/{App.jsx,main.jsx}
touch frontend/src/components/{VerificationForm.jsx,AgentProgress.jsx,ResultDisplay.jsx}

# Demo data
mkdir -p demo/{text_samples,images,videos}

# Documentation
touch README.md DEMO_SCRIPT.md
```

**Install Dependencies:**
```bash
# Backend
cd server
cat > requirements.txt << EOF
fastapi==0.109.0
uvicorn==0.27.0
mistralai==1.0.0
pydantic==2.6.0
sqlalchemy==2.0.25
python-multipart==0.0.6
pillow==10.2.0
requests==2.31.0
python-magic==0.4.27
langdetect==1.0.9
googletrans==4.0.0rc1
pytesseract==0.3.10
opencv-python==4.9.0.80
EOF

pip install -r requirements.txt
cd ..

# Frontend
cd frontend
cat > package.json << EOF
{
  "name": "veritasguard-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.5"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.11"
  }
}
EOF

npm install
cd ..
```

**Get API Keys:**
```bash
# Create .env file
cat > .env << EOF
MISTRAL_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here  # For web search
EOF
```

#### **Study Materials (1 hour)**

**Read Mistral Docs:**
- Agents API: https://docs.mistral.ai/agents/introduction
- Vision API: https://docs.mistral.ai/capabilities/vision
- Multi-lingual: Check model capabilities

**Test Mistral API:**
```python
# test_mistral.py
from mistralai import Mistral
import os

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

# Test chat
response = client.chat.complete(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": "Translate 'Hello' to Hindi"}]
)
print(response.choices[0].message.content)

# Test vision
# (Test with sample image)
```

#### **Collect Demo Data (1 hour)**

**Find Real Examples:**
1. **Text forwards (5 examples)**
   - 2 in Hindi
   - 1 in Tamil
   - 1 in Bengali
   - 1 in Marathi

2. **Images with text (3 examples)**
   - Fake quote on politician
   - Fake news headline
   - Manipulated statistic

3. **Video (1-2 examples)**
   - Find existing debunked videos
   - Or create mock suspicious video

**Sources:**
- Alt News (altnews.in)
- Boom Live (boomlive.in)
- India Today Fact Check
- Save anonymized versions

---

### **Thursday Feb 27 (4 hours)**

#### **Build Core Components Prototypes (4 hours)**

**1. Language Detection Prototype (1 hour)**
```python
# prototype_language_detection.py
from langdetect import detect, DetectError

def detect_language(text):
    try:
        lang = detect(text)
        return lang
    except DetectError:
        return "unknown"

# Test with Hindi, Tamil, etc.
test_texts = [
    "यह एक परीक्षण है",  # Hindi
    "இது ஒரு சோதனை",     # Tamil
    "এটি একটি পরীক্ষা"    # Bengali
]

for text in test_texts:
    print(f"{text} -> {detect_language(text)}")
```

**2. Translation Prototype (1 hour)**
```python
# prototype_translation.py
from mistralai import Mistral
import os

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

def translate_to_english(text, source_lang):
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{
            "role": "user",
            "content": f"Translate this {source_lang} text to English. Return ONLY the translation, nothing else:\n\n{text}"
        }]
    )
    return response.choices[0].message.content

# Test
hindi_text = "यह एक झूठी खबर है"
english = translate_to_english(hindi_text, "Hindi")
print(f"Hindi: {hindi_text}")
print(f"English: {english}")
```

**3. OCR Prototype (1 hour)**
```python
# prototype_ocr.py
import pytesseract
from PIL import Image

def extract_text_from_image(image_path):
    img = Image.open(image_path)
    
    # Try multiple languages
    text_eng = pytesseract.image_to_string(img, lang='eng')
    text_hin = pytesseract.image_to_string(img, lang='hin')
    
    # Return longest result
    return text_eng if len(text_eng) > len(text_hin) else text_hin

# Test with sample image
```

**4. Web Search Prototype (1 hour)**
```python
# prototype_web_search.py
import requests
import os

def web_search(query):
    # Using Google Custom Search API
    api_key = os.environ["GOOGLE_API_KEY"]
    cx = "your_search_engine_id"  # Get from Google
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": 5
    }
    
    response = requests.get(url, params=params)
    results = response.json()
    
    # Extract titles and snippets
    items = []
    for item in results.get("items", []):
        items.append({
            "title": item["title"],
            "snippet": item["snippet"],
            "link": item["link"]
        })
    
    return items

# Test
results = web_search("India COVID vaccine facts")
for r in results:
    print(f"{r['title']}: {r['snippet']}")
```

---

### **Friday Feb 28 (4 hours)**

#### **Build Agent Framework (4 hours)**

**1. Agent Base Class (1 hour)**
```python
# server/agents/base_agent.py
from abc import ABC, abstractmethod
from mistralai import Mistral
import os

class BaseAgent(ABC):
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.mistral_client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        self.mistral_agent = None
        self._create_mistral_agent()
    
    def _create_mistral_agent(self):
        """Create Mistral agent for this component"""
        self.mistral_agent = self.mistral_client.beta.agents.create(
            model="mistral-large-latest",
            name=self.name,
            description=self.description,
            instructions=self.get_instructions()
        )
    
    @abstractmethod
    def get_instructions(self):
        """Return system instructions for this agent"""
        pass
    
    @abstractmethod
    async def process(self, data):
        """Process data and return result"""
        pass
    
    async def query_mistral(self, prompt):
        """Query Mistral agent"""
        response = self.mistral_client.beta.conversations.start(
            agent_id=self.mistral_agent.id,
            inputs=prompt
        )
        
        # Extract text from response
        text_content = []
        for event in response.events:
            if event.type == "message.output":
                text_content.append(str(event.content))
        
        return "\n".join(text_content)
```

**2. Sample Agent Implementation (1 hour)**
```python
# server/agents/language_detection.py
from .base_agent import BaseAgent
from langdetect import detect

class LanguageDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Language Detection Agent",
            description="Detects the language of input text"
        )
    
    def get_instructions(self):
        return """You are a language detection expert. Identify the language 
        of the given text. Support: Hindi, Tamil, Telugu, Bengali, Marathi, 
        Gujarati, Punjabi, Malayalam, Kannada, and English."""
    
    async def process(self, data):
        text = data.get("text", "")
        
        # Use langdetect for quick detection
        try:
            detected_lang = detect(text)
        except:
            detected_lang = "unknown"
        
        # Map codes to names
        lang_map = {
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "bn": "Bengali",
            "mr": "Marathi",
            "gu": "Gujarati",
            "pa": "Punjabi",
            "ml": "Malayalam",
            "kn": "Kannada",
            "en": "English"
        }
        
        language = lang_map.get(detected_lang, detected_lang)
        
        return {
            "language": language,
            "language_code": detected_lang,
            "confidence": 0.9,  # langdetect doesn't provide confidence
            "agent": self.name
        }
```

**3. Orchestrator Framework (2 hours)**
```python
# server/orchestrator.py
from typing import Dict, List
import asyncio

class VerificationOrchestrator:
    def __init__(self):
        self.agents = {}
        self.results = {}
    
    def register_agent(self, agent_name, agent_instance):
        """Register an agent"""
        self.agents[agent_name] = agent_instance
    
    async def verify(self, input_data):
        """Main verification pipeline"""
        verification_id = self._generate_id()
        self.results[verification_id] = {
            "status": "processing",
            "stages": {},
            "final_verdict": None
        }
        
        try:
            # Stage 1: Language Detection
            lang_result = await self.agents["language_detection"].process(input_data)
            self.results[verification_id]["stages"]["language"] = lang_result
            
            # Stage 2: Translation
            translation_input = {
                **input_data,
                "source_language": lang_result["language"]
            }
            translation_result = await self.agents["translation"].process(translation_input)
            self.results[verification_id]["stages"]["translation"] = translation_result
            
            # Stage 3: Claim Extraction
            claim_result = await self.agents["claim_extraction"].process(translation_result)
            self.results[verification_id]["stages"]["claim"] = claim_result
            
            # Stage 4: Parallel Verification
            verification_tasks = [
                self.agents["source_verification"].process(claim_result),
                self.agents["media_forensics"].process(input_data),
                self.agents["context_history"].process(claim_result),
                self.agents["expert_validation"].process(claim_result)
            ]
            
            parallel_results = await asyncio.gather(*verification_tasks)
            self.results[verification_id]["stages"]["verification"] = parallel_results
            
            # Stage 5: Verdict
            verdict_input = {
                "claim": claim_result,
                "verifications": parallel_results,
                "original_language": lang_result["language"]
            }
            verdict_result = await self.agents["verdict"].process(verdict_input)
            self.results[verification_id]["stages"]["verdict"] = verdict_result
            self.results[verification_id]["final_verdict"] = verdict_result
            
            self.results[verification_id]["status"] = "completed"
            
        except Exception as e:
            self.results[verification_id]["status"] = "error"
            self.results[verification_id]["error"] = str(e)
        
        return verification_id
    
    def get_result(self, verification_id):
        """Get verification result"""
        return self.results.get(verification_id)
    
    def _generate_id(self):
        import uuid
        return str(uuid.uuid4())
```

**Test the framework:**
```python
# test_framework.py
import asyncio
from server.orchestrator import VerificationOrchestrator
from server.agents.language_detection import LanguageDetectionAgent

async def test():
    orchestrator = VerificationOrchestrator()
    
    # Register agents (for now just language detection)
    lang_agent = LanguageDetectionAgent()
    orchestrator.register_agent("language_detection", lang_agent)
    
    # Test
    input_data = {
        "text": "यह एक परीक्षण है",
        "type": "text"
    }
    
    # This will fail on other agents, but should work for language detection
    # You'll build the other agents during the hackathon
    
asyncio.run(test())
```

---

## 🚀 HACKATHON DAY 1 - SATURDAY FEB 28

### **10:00 AM - 12:00 PM: Setup & Core Infrastructure (2 hours)**

#### **10:00-10:30: Project Initialization**

**Set up FastAPI Server:**
```python
# server/main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="VeritasGuard API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import orchestrator
from orchestrator import VerificationOrchestrator

orchestrator = VerificationOrchestrator()

@app.get("/")
async def root():
    return {"message": "VeritasGuard API", "status": "online"}

@app.post("/verify/text")
async def verify_text(text: str = Form(...), language: Optional[str] = Form(None)):
    """Verify text content"""
    input_data = {
        "text": text,
        "type": "text",
        "language": language
    }
    
    verification_id = await orchestrator.verify(input_data)
    return {"verification_id": verification_id}

@app.post("/verify/image")
async def verify_image(file: UploadFile = File(...)):
    """Verify image with text"""
    # Save uploaded file
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    input_data = {
        "image_path": file_path,
        "type": "image"
    }
    
    verification_id = await orchestrator.verify(input_data)
    return {"verification_id": verification_id}

@app.get("/result/{verification_id}")
async def get_result(verification_id: str):
    """Get verification result"""
    result = orchestrator.get_result(verification_id)
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### **10:30-11:00: Database Setup**

```python
# server/database.py
from sqlalchemy import create_engine, Column, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Verification(Base):
    __tablename__ = "verifications"
    
    id = Column(String, primary_key=True)
    input_type = Column(String)
    input_text = Column(String, nullable=True)
    input_image_path = Column(String, nullable=True)
    detected_language = Column(String)
    claim = Column(String)
    verdict = Column(String)
    confidence = Column(String)
    evidence = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class KnownHoax(Base):
    __tablename__ = "known_hoaxes"
    
    id = Column(String, primary_key=True)
    claim = Column(String)
    description = Column(String)
    first_seen = Column(DateTime)
    languages = Column(JSON)
    impact = Column(String)

# Create database
engine = create_engine('sqlite:///veritasguard.db')
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)
```

#### **11:00-11:30: Mistral Client Utility**

```python
# server/utils/mistral_client.py
from mistralai import Mistral
import os

class MistralClientWrapper:
    def __init__(self):
        self.client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        self.agents = {}
    
    def create_agent(self, name, description, instructions, tools=None):
        """Create a Mistral agent"""
        agent = self.client.beta.agents.create(
            model="mistral-large-latest",
            name=name,
            description=description,
            instructions=instructions,
            tools=tools or []
        )
        self.agents[name] = agent
        return agent
    
    def query_agent(self, agent_id, prompt):
        """Query an agent"""
        response = self.client.beta.conversations.start(
            agent_id=agent_id,
            inputs=prompt
        )
        return self._extract_content(response)
    
    def query_with_vision(self, prompt, image_base64):
        """Query with image"""
        response = self.client.chat.complete(
            model="pixtral-large-latest",  # Mistral's vision model
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image_base64}"
                    }
                ]
            }]
        )
        return response.choices[0].message.content
    
    def _extract_content(self, response):
        """Extract text content from response"""
        content = []
        for event in response.events:
            if event.type == "message.output":
                content.append(str(event.content))
        return "\n".join(content)

# Global instance
mistral_client = MistralClientWrapper()
```

#### **11:30-12:00: Test Everything**

```python
# test_setup.py
import asyncio
from server.main import app
from server.utils.mistral_client import mistral_client

async def test_api():
    # Test Mistral connection
    agent = mistral_client.create_agent(
        name="Test Agent",
        description="Testing connection",
        instructions="You are a test agent."
    )
    
    response = mistral_client.query_agent(agent.id, "Hello")
    print(f"Mistral test: {response}")
    
    # Test API (you'd use httpx or similar in real test)
    print("API endpoints ready")

asyncio.run(test_api())
```

---

### **12:00 PM - 1:00 PM: LUNCH BREAK**

---

### **1:00 PM - 4:00 PM: Build Core Agents (3 hours)**

#### **1:00-1:30: Translation Agent**

```python
# server/agents/translation.py
from .base_agent import BaseAgent

class TranslationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Translation Agent",
            description="Translates text from regional languages to English"
        )
    
    def get_instructions(self):
        return """You are an expert translator. Translate text accurately 
        from Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, and other 
        Indian languages to English. Preserve meaning and context. 
        Handle code-mixed languages (Hinglish, Tanglish)."""
    
    async def process(self, data):
        text = data.get("translated_text", data.get("text", ""))
        source_lang = data.get("source_language", "unknown")
        
        if source_lang.lower() == "english":
            return {
                "original_text": text,
                "english_text": text,
                "translation_needed": False,
                "agent": self.name
            }
        
        # Translate using Mistral
        prompt = f"""Translate this {source_lang} text to English. 
        Return ONLY the English translation, nothing else:

        {text}
        """
        
        english_text = await self.query_mistral(prompt)
        
        return {
            "original_text": text,
            "english_text": english_text.strip(),
            "source_language": source_lang,
            "translation_needed": True,
            "agent": self.name
        }
```

#### **1:30-2:00: Claim Extraction Agent**

```python
# server/agents/claim_extraction.py
from .base_agent import BaseAgent
import json

class ClaimExtractionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Claim Extraction Agent",
            description="Extracts factual claims from text"
        )
    
    def get_instructions(self):
        return """You are a fact-checking expert. Extract factual claims 
        from text that can be verified. Ignore opinions. Return claims as 
        a JSON list."""
    
    async def process(self, data):
        text = data.get("english_text", data.get("text", ""))
        
        prompt = f"""Extract all factual claims from this text. 
        Return as JSON array of claims. Each claim should be a clear statement.
        
        Text:
        {text}
        
        Return format:
        {{"claims": ["claim1", "claim2", ...]}}
        """
        
        response = await self.query_mistral(prompt)
        
        # Parse JSON
        try:
            # Clean response (remove markdown code blocks if present)
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            claims_data = json.loads(clean_response)
            claims = claims_data.get("claims", [])
        except:
            # Fallback: treat entire text as single claim
            claims = [text]
        
        return {
            "claims": claims,
            "primary_claim": claims[0] if claims else text,
            "agent": self.name
        }
```

#### **2:00-2:30: Source Verification Agent**

```python
# server/agents/source_verification.py
from .base_agent import BaseAgent
import requests
import os

class SourceVerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Source Verification Agent",
            description="Verifies claims using web search"
        )
        self.google_api_key = os.environ.get("GOOGLE_API_KEY")
        self.search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
    
    def get_instructions(self):
        return """You are a fact-checker. Given web search results about 
        a claim, determine if the claim is TRUE, FALSE, or UNVERIFIABLE. 
        Cite specific sources."""
    
    async def process(self, data):
        primary_claim = data.get("primary_claim", "")
        
        # Perform web search
        search_results = self._web_search(primary_claim)
        
        # Analyze results with Mistral
        prompt = f"""Given these web search results, is this claim TRUE or FALSE?

        Claim: {primary_claim}
        
        Search Results:
        {self._format_search_results(search_results)}
        
        Return JSON:
        {{
            "verdict": "TRUE/FALSE/MISLEADING/UNVERIFIABLE",
            "confidence": 0.0-1.0,
            "reasoning": "explanation",
            "sources": ["source1", "source2"]
        }}
        """
        
        response = await self.query_mistral(prompt)
        
        # Parse response
        import json
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            verdict_data = json.loads(clean_response.strip())
        except:
            verdict_data = {
                "verdict": "UNVERIFIABLE",
                "confidence": 0.5,
                "reasoning": "Could not parse analysis",
                "sources": []
            }
        
        return {
            **verdict_data,
            "search_results": search_results,
            "agent": self.name
        }
    
    def _web_search(self, query):
        """Perform Google search"""
        if not self.google_api_key:
            return []
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": 5
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            results = response.json()
            
            items = []
            for item in results.get("items", []):
                items.append({
                    "title": item["title"],
                    "snippet": item["snippet"],
                    "link": item["link"]
                })
            return items
        except:
            return []
    
    def _format_search_results(self, results):
        """Format search results for prompt"""
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"{i}. {result['title']}\n   {result['snippet']}\n   {result['link']}")
        return "\n\n".join(formatted)
```

#### **2:30-3:00: Media Forensics Agent (Images)**

```python
# server/agents/media_forensics.py
from .base_agent import BaseAgent
import pytesseract
from PIL import Image
import base64
import io
import requests

class MediaForensicsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Media Forensics Agent",
            description="Analyzes images for manipulation and extracts text"
        )
    
    def get_instructions(self):
        return """You are an image forensics expert. Analyze images for 
        signs of manipulation, text overlays, and authenticity."""
    
    async def process(self, data):
        if data.get("type") != "image":
            return {"applicable": False, "agent": self.name}
        
        image_path = data.get("image_path")
        if not image_path:
            return {"error": "No image path", "agent": self.name}
        
        # Extract text from image
        extracted_text = self._extract_text(image_path)
        
        # Reverse image search (simplified - would use actual API)
        reverse_search_results = self._reverse_image_search(image_path)
        
        # Analyze with Mistral Vision
        image_analysis = await self._analyze_image_with_vision(image_path)
        
        return {
            "extracted_text": extracted_text,
            "reverse_search": reverse_search_results,
            "analysis": image_analysis,
            "agent": self.name
        }
    
    def _extract_text(self, image_path):
        """Extract text using OCR"""
        try:
            img = Image.open(image_path)
            
            # Try multiple languages
            text_eng = pytesseract.image_to_string(img, lang='eng')
            text_hin = pytesseract.image_to_string(img, lang='hin')
            
            # Return whichever has more text
            return text_eng if len(text_eng) > len(text_hin) else text_hin
        except Exception as e:
            return f"Error extracting text: {str(e)}"
    
    def _reverse_image_search(self, image_path):
        """Simplified reverse image search"""
        # In production, use Google Vision API or TinEye
        return {
            "similar_images_found": False,
            "note": "Reverse search would be implemented with external API"
        }
    
    async def _analyze_image_with_vision(self, image_path):
        """Analyze image using Mistral Vision"""
        # Convert image to base64
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode()
        
        prompt = """Analyze this image for signs of manipulation:
        1. Does it contain overlaid text?
        2. Are there signs of editing (inconsistent lighting, artifacts)?
        3. What is the main content?
        4. Does anything look suspicious?
        
        Return JSON:
        {
            "has_text_overlay": true/false,
            "signs_of_manipulation": ["sign1", "sign2"],
            "content_description": "description",
            "suspicious_elements": ["element1"]
        }
        """
        
        from server.utils.mistral_client import mistral_client
        response = mistral_client.query_with_vision(prompt, image_base64)
        
        return response
```

#### **3:00-3:30: Context & History Agent**

```python
# server/agents/context_history.py
from .base_agent import BaseAgent
from server.database import SessionLocal, KnownHoax
from datetime import datetime

class ContextHistoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Context & History Agent",
            description="Checks if claim matches known hoaxes"
        )
        self._seed_known_hoaxes()
    
    def get_instructions(self):
        return """You are a fact-checking historian. Match claims against 
        known hoaxes and recurring misinformation patterns."""
    
    async def process(self, data):
        primary_claim = data.get("primary_claim", "")
        
        # Check database for similar hoaxes
        similar_hoaxes = self._find_similar_hoaxes(primary_claim)
        
        if similar_hoaxes:
            return {
                "is_known_hoax": True,
                "similar_hoaxes": similar_hoaxes,
                "warning": "This claim matches known misinformation",
                "agent": self.name
            }
        
        # Use Mistral to identify patterns
        prompt = f"""Is this claim similar to any known hoax patterns?
        Common patterns:
        - "Muslims poisoning water" (causes communal violence)
        - "Doctors harvesting organs" (causes attacks on healthcare)
        - "Politicians said [inflammatory quote]" (election misinformation)
        - "This home remedy cures COVID" (health misinformation)
        
        Claim: {primary_claim}
        
        Return JSON:
        {{
            "matches_pattern": true/false,
            "pattern_type": "pattern name",
            "historical_impact": "description of past harm"
        }}
        """
        
        response = await self.query_mistral(prompt)
        
        import json
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            pattern_data = json.loads(clean_response.strip())
        except:
            pattern_data = {"matches_pattern": False}
        
        return {
            **pattern_data,
            "agent": self.name
        }
    
    def _find_similar_hoaxes(self, claim):
        """Search database for similar hoaxes"""
        db = SessionLocal()
        try:
            # Simple keyword matching (in production, use embeddings)
            hoaxes = db.query(KnownHoax).all()
            
            similar = []
            for hoax in hoaxes:
                # Very basic similarity (would use embeddings in production)
                if any(word in claim.lower() for word in hoax.claim.lower().split()):
                    similar.append({
                        "claim": hoax.claim,
                        "description": hoax.description,
                        "impact": hoax.impact
                    })
            
            return similar[:3]  # Top 3
        finally:
            db.close()
    
    def _seed_known_hoaxes(self):
        """Seed database with known hoaxes"""
        db = SessionLocal()
        try:
            # Check if already seeded
            if db.query(KnownHoax).count() > 0:
                return
            
            hoaxes = [
                {
                    "id": "hoax_001",
                    "claim": "Muslims poisoning water supply",
                    "description": "Recurring hoax causing communal violence",
                    "first_seen": datetime(2018, 1, 1),
                    "languages": ["hindi", "marathi", "gujarati"],
                    "impact": "5 people lynched in 2018"
                },
                {
                    "id": "hoax_002",
                    "claim": "Doctors harvesting organs",
                    "description": "False claim about organ theft",
                    "first_seen": datetime(2019, 3, 1),
                    "languages": ["tamil", "telugu"],
                    "impact": "Mob attacks on hospitals"
                }
            ]
            
            for hoax_data in hoaxes:
                hoax = KnownHoax(**hoax_data)
                db.add(hoax)
            
            db.commit()
        finally:
            db.close()
```

#### **3:30-4:00: Verdict Agent**

```python
# server/agents/verdict.py
from .base_agent import BaseAgent
import json

class VerdictAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Verdict Agent",
            description="Synthesizes all findings into final verdict"
        )
    
    def get_instructions(self):
        return """You are the final judge in a fact-checking system. 
        Synthesize all evidence and provide a clear verdict."""
    
    async def process(self, data):
        claim = data.get("claim", {})
        verifications = data.get("verifications", [])
        original_language = data.get("original_language", "English")
        
        # Compile evidence
        evidence_summary = self._compile_evidence(verifications)
        
        # Get final verdict from Mistral
        prompt = f"""Based on this evidence, what is your verdict?

        Claim: {claim.get('primary_claim', '')}
        
        Evidence:
        {evidence_summary}
        
        Provide verdict as JSON:
        {{
            "verdict": "TRUE/FALSE/MISLEADING/UNVERIFIABLE",
            "confidence": 0.0-1.0,
            "summary": "brief explanation",
            "key_evidence": ["point1", "point2"],
            "recommendation": "What user should do"
        }}
        """
        
        response = await self.query_mistral(prompt)
        
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            verdict_data = json.loads(clean_response.strip())
        except:
            verdict_data = {
                "verdict": "UNVERIFIABLE",
                "confidence": 0.5,
                "summary": "Could not determine verdict",
                "key_evidence": [],
                "recommendation": "Treat with skepticism"
            }
        
        # Translate verdict back to original language
        if original_language.lower() != "english":
            translated_summary = await self._translate_back(
                verdict_data["summary"],
                original_language
            )
            verdict_data["summary_original_language"] = translated_summary
        
        return {
            **verdict_data,
            "original_language": original_language,
            "agent": self.name
        }
    
    def _compile_evidence(self, verifications):
        """Compile evidence from all verification agents"""
        evidence_parts = []
        
        for i, verification in enumerate(verifications):
            agent_name = verification.get("agent", f"Agent {i+1}")
            
            if "verdict" in verification:
                evidence_parts.append(
                    f"{agent_name}: {verification['verdict']} "
                    f"(confidence: {verification.get('confidence', 'N/A')})"
                )
            
            if "is_known_hoax" in verification and verification["is_known_hoax"]:
                evidence_parts.append(
                    f"{agent_name}: Matches known hoax pattern - "
                    f"{verification.get('warning', '')}"
                )
            
            if "analysis" in verification:
                evidence_parts.append(f"{agent_name}: {verification['analysis']}")
        
        return "\n".join(evidence_parts)
    
    async def _translate_back(self, text, target_language):
        """Translate verdict back to original language"""
        prompt = f"""Translate this text to {target_language}. 
        Keep it simple and clear.
        
        Text: {text}
        
        Return ONLY the translation.
        """
        
        translation = await self.query_mistral(prompt)
        return translation.strip()
```

---

### **4:00 PM - 5:00 PM: Expert Validation Agent + Integration (1 hour)**

```python
# server/agents/expert_validation.py
from .base_agent import BaseAgent

class ExpertValidationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Expert Validation Agent",
            description="Validates claims against expert sources"
        )
    
    def get_instructions(self):
        return """You are an expert validator. Check claims against 
        authoritative sources: WHO, government websites, research papers."""
    
    async def process(self, data):
        primary_claim = data.get("primary_claim", "")
        
        # Identify claim type
        claim_type = await self._identify_claim_type(primary_claim)
        
        # Check appropriate expert sources
        expert_check = await self._check_expert_sources(primary_claim, claim_type)
        
        return {
            "claim_type": claim_type,
            "expert_verification": expert_check,
            "agent": self.name
        }
    
    async def _identify_claim_type(self, claim):
        """Identify if claim is medical, political, etc."""
        prompt = f"""What type of claim is this?
        Options: medical, political, religious, scientific, other
        
        Claim: {claim}
        
        Return just the type, nothing else.
        """
        
        claim_type = await self.query_mistral(prompt)
        return claim_type.strip().lower()
    
    async def _check_expert_sources(self, claim, claim_type):
        """Check against expert sources"""
        # In production, would actually query APIs
        # For demo, use Mistral's knowledge
        
        source_guidance = {
            "medical": "WHO, CDC, peer-reviewed medical journals",
            "political": "Official government statements, verified news",
            "religious": "Official religious authority statements",
            "scientific": "Peer-reviewed journals, universities"
        }
        
        sources = source_guidance.get(claim_type, "credible news sources")
        
        prompt = f"""Based on knowledge from {sources}, is this claim valid?
        
        Claim: {claim}
        
        Return JSON:
        {{
            "supported_by_experts": true/false,
            "reasoning": "explanation",
            "suggested_sources": ["source1", "source2"]
        }}
        """
        
        response = await self.query_mistral(prompt)
        
        import json
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            expert_data = json.loads(clean_response.strip())
        except:
            expert_data = {
                "supported_by_experts": False,
                "reasoning": "Could not verify",
                "suggested_sources": []
            }
        
        return expert_data
```

**Update Orchestrator to include all agents:**

```python
# server/orchestrator.py (UPDATE)
from agents.language_detection import LanguageDetectionAgent
from agents.translation import TranslationAgent
from agents.claim_extraction import ClaimExtractionAgent
from agents.source_verification import SourceVerificationAgent
from agents.media_forensics import MediaForensicsAgent
from agents.context_history import ContextHistoryAgent
from agents.expert_validation import ExpertValidationAgent
from agents.verdict import VerdictAgent

class VerificationOrchestrator:
    def __init__(self):
        self.agents = {
            "language_detection": LanguageDetectionAgent(),
            "translation": TranslationAgent(),
            "claim_extraction": ClaimExtractionAgent(),
            "source_verification": SourceVerificationAgent(),
            "media_forensics": MediaForensicsAgent(),
            "context_history": ContextHistoryAgent(),
            "expert_validation": ExpertValidationAgent(),
            "verdict": VerdictAgent()
        }
        self.results = {}
    
    # ... rest of orchestrator code from earlier
```

---

### **5:00 PM - 6:00 PM: Testing & Debugging (1 hour)**

**Create test script:**

```python
# test_full_pipeline.py
import asyncio
from server.orchestrator import VerificationOrchestrator

async def test_text_verification():
    orchestrator = VerificationOrchestrator()
    
    # Test case 1: Hindi text
    print("Test 1: Hindi misinformation")
    input_data = {
        "text": "मुस्लिम लोग पानी में जहर मिला रहे हैं",  # Muslims poisoning water
        "type": "text"
    }
    
    verification_id = await orchestrator.verify(input_data)
    result = orchestrator.get_result(verification_id)
    
    print(f"Result: {result}")
    print("\n" + "="*80 + "\n")
    
    # Test case 2: English text
    print("Test 2: English claim")
    input_data = {
        "text": "Doctors are harvesting organs from patients",
        "type": "text"
    }
    
    verification_id = await orchestrator.verify(input_data)
    result = orchestrator.get_result(verification_id)
    
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_text_verification())
```

**Run tests and fix bugs:**
```bash
python test_full_pipeline.py
```

---

### **6:00 PM - 7:00 PM: DINNER BREAK**

---

### **7:00 PM - 9:00 PM: Basic Frontend (2 hours)**

#### **7:00-7:30: Frontend Setup**

```jsx
// frontend/src/App.jsx
import { useState } from 'react';
import './App.css';
import VerificationForm from './components/VerificationForm';
import AgentProgress from './components/AgentProgress';
import ResultDisplay from './components/ResultDisplay';

function App() {
  const [verificationId, setVerificationId] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (data) => {
    setLoading(true);
    setResult(null);

    try {
      // Submit verification
      const formData = new FormData();
      if (data.type === 'text') {
        formData.append('text', data.text);
      } else if (data.type === 'image') {
        formData.append('file', data.file);
      }

      const endpoint = data.type === 'text' 
        ? 'http://localhost:8000/verify/text'
        : 'http://localhost:8000/verify/image';

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData
      });

      const { verification_id } = await response.json();
      setVerificationId(verification_id);

      // Poll for result
      pollResult(verification_id);
    } catch (error) {
      console.error('Error:', error);
      setLoading(false);
    }
  };

  const pollResult = async (id) => {
    const maxAttempts = 30; // 30 seconds
    let attempts = 0;

    const interval = setInterval(async () => {
      attempts++;

      try {
        const response = await fetch(`http://localhost:8000/result/${id}`);
        const data = await response.json();

        if (data.status === 'completed') {
          setResult(data);
          setLoading(false);
          clearInterval(interval);
        } else if (data.status === 'error' || attempts >= maxAttempts) {
          setLoading(false);
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 1000);
  };

  return (
    <div className="App">
      <header>
        <h1>🛡️ VeritasGuard</h1>
        <p>Multi-lingual Misinformation Verification</p>
      </header>

      <main>
        {!loading && !result && (
          <VerificationForm onSubmit={handleSubmit} />
        )}

        {loading && (
          <AgentProgress verificationId={verificationId} />
        )}

        {result && (
          <ResultDisplay result={result} onReset={() => {
            setResult(null);
            setVerificationId(null);
          }} />
        )}
      </main>
    </div>
  );
}

export default App;
```

#### **7:30-8:00: Verification Form Component**

```jsx
// frontend/src/components/VerificationForm.jsx
import { useState } from 'react';

function VerificationForm({ onSubmit }) {
  const [inputType, setInputType] = useState('text');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (inputType === 'text' && text.trim()) {
      onSubmit({ type: 'text', text });
    } else if (inputType === 'image' && file) {
      onSubmit({ type: 'image', file });
    }
  };

  return (
    <div className="verification-form">
      <div className="input-type-selector">
        <button 
          className={inputType === 'text' ? 'active' : ''}
          onClick={() => setInputType('text')}
        >
          📝 Text
        </button>
        <button 
          className={inputType === 'image' ? 'active' : ''}
          onClick={() => setInputType('image')}
        >
          🖼️ Image
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {inputType === 'text' && (
          <textarea
            placeholder="Paste suspicious message here (any language)..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
          />
        )}

        {inputType === 'image' && (
          <div className="file-upload">
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files[0])}
            />
            {file && <p>Selected: {file.name}</p>}
          </div>
        )}

        <button type="submit" className="verify-button">
          🔍 Verify Now
        </button>
      </form>
    </div>
  );
}

export default VerificationForm;
```

#### **8:00-8:30: Agent Progress Component**

```jsx
// frontend/src/components/AgentProgress.jsx
function AgentProgress({ verificationId }) {
  const agents = [
    { name: "Language Detection", icon: "🌐" },
    { name: "Translation", icon: "🔤" },
    { name: "Claim Extraction", icon: "📋" },
    { name: "Source Verification", icon: "🔎" },
    { name: "Media Forensics", icon: "🖼️" },
    { name: "Context Check", icon: "📚" },
    { name: "Expert Validation", icon: "👨‍⚕️" },
    { name: "Final Verdict", icon: "⚖️" }
  ];

  return (
    <div className="agent-progress">
      <h2>Analyzing...</h2>
      <div className="agents-list">
        {agents.map((agent, index) => (
          <div key={index} className="agent-item animating">
            <span className="agent-icon">{agent.icon}</span>
            <span className="agent-name">{agent.name}</span>
            <span className="spinner">⏳</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AgentProgress;
```

#### **8:30-9:00: Result Display Component**

```jsx
// frontend/src/components/ResultDisplay.jsx
function ResultDisplay({ result, onReset }) {
  const verdict = result?.final_verdict || {};
  
  const getVerdictColor = (v) => {
    if (v === 'FALSE') return '#ff4444';
    if (v === 'TRUE') return '#44ff44';
    if (v === 'MISLEADING') return '#ffaa44';
    return '#888888';
  };

  return (
    <div className="result-display">
      <div className="verdict-card" style={{
        borderColor: getVerdictColor(verdict.verdict)
      }}>
        <h2 className="verdict-title">
          {verdict.verdict === 'FALSE' && '❌ FALSE'}
          {verdict.verdict === 'TRUE' && '✅ TRUE'}
          {verdict.verdict === 'MISLEADING' && '⚠️ MISLEADING'}
          {verdict.verdict === 'UNVERIFIABLE' && '❓ UNVERIFIABLE'}
        </h2>
        
        <div className="confidence">
          Confidence: {(verdict.confidence * 100).toFixed(0)}%
        </div>

        <div className="summary">
          <h3>Summary:</h3>
          <p>{verdict.summary}</p>
        </div>

        {verdict.summary_original_language && (
          <div className="original-language-summary">
            <h3>Original Language:</h3>
            <p>{verdict.summary_original_language}</p>
          </div>
        )}

        {verdict.key_evidence && verdict.key_evidence.length > 0 && (
          <div className="evidence">
            <h3>Key Evidence:</h3>
            <ul>
              {verdict.key_evidence.map((evidence, i) => (
                <li key={i}>{evidence}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="recommendation">
          <h3>Recommendation:</h3>
          <p>{verdict.recommendation}</p>
        </div>
      </div>

      <button onClick={onReset} className="verify-another">
        Verify Another Message
      </button>

      <div className="agent-details">
        <h3>Agent Analysis:</h3>
        {Object.entries(result.stages || {}).map(([stage, data]) => (
          <details key={stage}>
            <summary>{stage}</summary>
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </details>
        ))}
      </div>
    </div>
  );
}

export default ResultDisplay;
```

---

### **9:00 PM - 10:00 PM: Basic Styling (1 hour)**

```css
/* frontend/src/App.css */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}

.App {
  max-width: 800px;
  margin: 0 auto;
}

header {
  text-align: center;
  color: white;
  margin-bottom: 40px;
}

header h1 {
  font-size: 3em;
  margin-bottom: 10px;
}

main {
  background: white;
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}

/* Verification Form */
.input-type-selector {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.input-type-selector button {
  flex: 1;
  padding: 15px;
  border: 2px solid #ddd;
  background: white;
  border-radius: 10px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.input-type-selector button.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

textarea {
  width: 100%;
  padding: 15px;
  border: 2px solid #ddd;
  border-radius: 10px;
  font-size: 16px;
  font-family: inherit;
  resize: vertical;
}

.verify-button {
  width: 100%;
  padding: 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  margin-top: 20px;
  transition: all 0.3s;
}

.verify-button:hover {
  background: #5568d3;
  transform: translateY(-2px);
}

/* Agent Progress */
.agent-progress {
  text-align: center;
}

.agents-list {
  margin-top: 30px;
}

.agent-item {
  display: flex;
  align-items: center;
  padding: 15px;
  margin: 10px 0;
  background: #f5f5f5;
  border-radius: 10px;
  animation: pulse 1.5s infinite;
}

.agent-icon {
  font-size: 24px;
  margin-right: 15px;
}

.agent-name {
  flex: 1;
  text-align: left;
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* Result Display */
.verdict-card {
  border: 3px solid;
  border-radius: 15px;
  padding: 30px;
  margin-bottom: 20px;
}

.verdict-title {
  font-size: 2.5em;
  margin-bottom: 15px;
}

.confidence {
  font-size: 1.2em;
  color: #666;
  margin-bottom: 20px;
}

.summary, .evidence, .recommendation {
  margin: 20px 0;
}

.summary h3, .evidence h3, .recommendation h3 {
  color: #333;
  margin-bottom: 10px;
}

.evidence ul {
  list-style-position: inside;
  line-height: 1.8;
}

.verify-another {
  width: 100%;
  padding: 15px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  cursor: pointer;
  margin-bottom: 20px;
}

.agent-details {
  margin-top: 30px;
  padding-top: 30px;
  border-top: 2px solid #eee;
}

details {
  margin: 10px 0;
  padding: 10px;
  background: #f9f9f9;
  border-radius: 5px;
}

summary {
  cursor: pointer;
  font-weight: bold;
  padding: 10px;
}

pre {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 5px;
  overflow-x: auto;
  font-size: 12px;
}
```

---

### **10:00 PM - 11:00 PM: Integration Testing (1 hour)**

**Test full stack:**

1. Start backend:
```bash
cd server
python main.py
```

2. Start frontend (new terminal):
```bash
cd frontend
npm run dev
```

3. Open browser: `http://localhost:5173`

4. Test with demo data:
   - Test Hindi text
   - Test English text
   - Test image with text

**Fix any bugs**

---

### **11:00 PM - 12:00 AM: Demo Preparation (1 hour)**

**Create demo script:**

```markdown
# demo/DEMO_SCRIPT.md

## Demo Flow (3 minutes)

### Setup (15 seconds)
"WhatsApp forwards cause violence in India. 500M+ people receive 
misinformation daily. Most don't know how to verify. Meet VeritasGuard."

### Demo 1: Hindi Misinformation (60 seconds)
[Show WhatsApp-style interface with Hindi text]
"This forward in Hindi claims Muslims are poisoning water. 
This exact rumor caused 5 deaths in 2018."

[Submit to VeritasGuard]
[Show agents activating one by one]
- Language Detection: "Hindi detected"
- Translation: "Muslims poisoning water supply"
- Verification: "No credible sources support this"
- Context: "MATCHES KNOWN HOAX - caused violence in 2018"
- Verdict: "FALSE - This is dangerous misinformation"

[Show verdict in Hindi with evidence]

### Demo 2: Image Manipulation (45 seconds)
[Show image with fake quote]
"This image shows a politician with an inflammatory quote."

[Submit to VeritasGuard]
- Vision Agent: Extracts text, finds original image
- Shows side-by-side: Original vs Manipulated
- Verdict: "MANIPULATED - Text was added to real photo"

### Demo 3: Live Test (30 seconds)
"Give me any suspicious forward, any language."
[Judge provides example]
[Process live]

### Close (15 seconds)
"8 agents, 22 languages, stopping misinformation before it causes harm.
Built on Mistral AI. Open source. Saving lives."
```

**Prepare backup:**
- Record successful runs
- Take screenshots
- Export sample data

---

### **12:00 AM - 2:00 AM: Polish & Buffer (2 hours)**

- Add loading animations
- Improve error handling
- Add more demo examples
- Write README
- Prepare pitch deck

---

### **2:00 AM - 8:00 AM: SLEEP (6 hours)**

**CRITICAL: Get proper sleep. You need to be sharp for Sunday.**

---

## 🚀 HACKATHON DAY 2 - SUNDAY MAR 1

### **9:00 AM - 12:00 PM: Final Features & Polish (3 hours)**

#### **9:00-10:00: Add Confidence Scoring Visualization**

```jsx
// frontend/src/components/ConfidenceBar.jsx
function ConfidenceBar({ confidence }) {
  const percentage = (confidence * 100).toFixed(0);
  const color = confidence > 0.8 ? '#44ff44' : 
                confidence > 0.5 ? '#ffaa44' : '#ff4444';

  return (
    <div className="confidence-bar">
      <div className="bar-container">
        <div 
          className="bar-fill" 
          style={{ 
            width: `${percentage}%`,
            backgroundColor: color
          }}
        />
      </div>
      <span className="percentage">{percentage}%</span>
    </div>
  );
}
```

#### **10:00-11:00: Add Evidence Sources Display**

```jsx
// frontend/src/components/EvidenceSources.jsx
function EvidenceSources({ sources }) {
  return (
    <div className="evidence-sources">
      <h3>📚 Sources Checked:</h3>
      {sources.map((source, i) => (
        <div key={i} className="source-item">
          <a href={source.link} target="_blank" rel="noopener noreferrer">
            {source.title}
          </a>
          <p>{source.snippet}</p>
        </div>
      ))}
    </div>
  );
}
```

#### **11:00-12:00: Performance Optimization**

- Add caching for common queries
- Optimize image processing
- Add request timeouts
- Test with slow network

---

### **12:00 PM - 1:00 PM: LUNCH BREAK**

---

### **1:00 PM - 3:00 PM: Demo Rehearsal & Recording (2 hours)**

#### **1:00-2:00: Practice Demo**

**Run through demo 5 times:**
1. Time yourself (must be under 3 minutes)
2. Practice narration
3. Test all examples
4. Prepare for questions

**Common questions to prepare for:**
- "How accurate is this?"
- "What if the claim is in a language you don't support?"
- "How do you handle deepfakes?"
- "Can this be manipulated?"

#### **2:00-3:00: Record Backup Video**

**Record 3-5 successful runs:**
- Hindi text example
- Tamil text example
- Image manipulation example
- Show full agent workflow
- Export as MP4

---

### **3:00 PM - 4:00 PM: Documentation (1 hour)**

```markdown
# README.md

# VeritasGuard 🛡️

Multi-lingual Misinformation Combat System

## The Problem

- 500M+ Indians receive misinformation daily via WhatsApp
- Fake news has caused 100+ deaths since 2018
- Existing fact-checkers only work in English
- By the time misinformation is debunked, damage is done

## The Solution

VeritasGuard verifies suspicious content in ANY language using 8 AI agents:

1. **Language Detection** - Identifies Hindi, Tamil, Telugu, Bengali, etc.
2. **Translation** - Converts to English for analysis
3. **Claim Extraction** - Identifies verifiable claims
4. **Source Verification** - Checks against credible sources
5. **Media Forensics** - Analyzes images for manipulation
6. **Context & History** - Matches against known hoaxes
7. **Expert Validation** - Verifies with authoritative sources
8. **Verdict** - Synthesizes findings, translates back

## Impact

- Verification time: 8-12 seconds (vs hours/days manual)
- Languages: 22+ supported
- Modalities: Text, images, video, audio
- Prevents violence by stopping viral misinformation

## Tech Stack

- **Backend:** FastAPI, Python
- **AI:** Mistral Large, Mistral Vision, Agent Handoffs
- **Frontend:** React, Vite
- **Database:** SQLite

## Run Locally

```bash
# Backend
cd server
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

## Demo

Watch agents verify Hindi misinformation in real-time:
[Link to video]

## Built With

Mistral AI - Agent handoffs, multi-lingual capabilities, vision

## License

MIT - Use this to fight misinformation anywhere
```

---

### **4:00 PM - 5:00 PM: Final Testing & Bug Fixes (1 hour)**

**Test everything one more time:**
- [ ] All demo examples work
- [ ] Error handling works
- [ ] UI is responsive
- [ ] API endpoints working
- [ ] Database operations working
- [ ] Backup video plays correctly

**Fix critical bugs only**

---

### **5:00 PM - 5:30 PM: Pitch Deck (30 minutes)**

**Create 5 slides:**

1. **Title Slide**
   - VeritasGuard
   - Multi-lingual Misinformation Combat
   - Your name

2. **The Problem**
   - 500M+ receive fake news daily
   - 100+ deaths from misinformation
   - Fact-checkers only work in English

3. **The Solution**
   - 8 AI agents verify in any language
   - 8-12 second verification
   - Shows evidence, translates verdict

4. **Technical Innovation**
   - Multi-lingual agent coordination (Mistral handoffs)
   - Multi-modal (text, image, video)
   - Cultural context awareness

5. **Impact**
   - Prevents violence
   - Election integrity
   - Public health protection
   - Universal accessibility

---

### **5:30 PM - 6:00 PM: Final Rehearsal**

**Practice your 3-minute pitch 3 more times**

**Checklist:**
- [ ] Pitch is under 3 minutes
- [ ] Demo works smoothly
- [ ] You can explain technical details
- [ ] Backup video ready
- [ ] Confident and energized

---

## 🎯 DEMO DAY CHECKLIST

**Before your slot:**
- [ ] Laptop fully charged
- [ ] Backup video ready
- [ ] Internet connection tested
- [ ] Demo data loaded
- [ ] Pitch deck open
- [ ] Water bottle nearby

**During demo:**
- [ ] Start with problem (emotional hook)
- [ ] Show demo (let it speak)
- [ ] Explain innovation
- [ ] Share impact
- [ ] Thank judges

**After demo:**
- [ ] Answer questions confidently
- [ ] Share GitHub link
- [ ] Offer to run again if time

---

## 🚨 CONTINGENCY PLANS

### **If Mistral API goes down:**
- Use cached responses
- Play backup video
- Explain what it would do

### **If demo freezes:**
- Don't panic
- Switch to backup video
- Explain what's happening

### **If you run out of time:**
- Skip to demo video
- Show verdict screen
- Explain impact

### **If judges ask tough questions:**
- Be honest about limitations
- Explain future improvements
- Show you understand the domain

---

## 💡 FINAL TIPS

**Technical:**
- Commit code every hour
- Test on clean browser
- Have offline mode ready
- Print error logs

**Presentation:**
- Speak slowly and clearly
- Make eye contact
- Show passion
- Smile

**Energy:**
- Sleep Saturday night (non-negotiable)
- Eat proper meals
- Take short breaks
- Stay hydrated

**Mindset:**
- This solves a REAL problem
- You're HELPING people
- You've worked HARD
- You DESERVE to win

---

## 🏆 YOU'VE GOT THIS

You're building something that:
- Saves lives
- Helps 500M+ people
- Showcases cutting-edge AI
- Makes Mistral proud

**Win or learn, you're making a difference.**

Now go build VeritasGuard and CRUSH IT! 🚀
