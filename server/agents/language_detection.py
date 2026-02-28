import re
from collections import Counter

from server.agents.base_agent import BaseAgent
from server.languages import (
    ALL_SUPPORTED_LANGUAGE_CODES,
    LANGDETECT_CODE_MAP,
    LANGUAGE_METADATA,
    MAJOR_ROMANIZED_HINTS,
    SCRIPT_RANGES,
    SCRIPT_TO_LANGUAGE_CODES,
    normalize_language_code,
)

try:
    from langdetect import DetectorFactory, detect

    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


def _detect_script(text: str) -> tuple[str | None, int]:
    script_counts: Counter[str] = Counter()
    for char in text:
        cp = ord(char)
        for script_name, ranges in SCRIPT_RANGES.items():
            for start, end in ranges:
                if start <= cp <= end:
                    script_counts[script_name] += 1
                    break
    if not script_counts:
        return None, 0
    script, count = script_counts.most_common(1)[0]
    return script, count


def _romanized_hint_language(text: str) -> tuple[str | None, float]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if len(words) < 3:
        return None, 0.0

    scores: Counter[str] = Counter()
    for code, hints in MAJOR_ROMANIZED_HINTS.items():
        for word in words:
            if word in hints:
                scores[code] += 1
    if not scores:
        return None, 0.0
    best_code, score = scores.most_common(1)[0]
    confidence = min(0.82, 0.5 + (score / max(1, len(words))) * 1.8)
    return best_code, confidence


class LanguageDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__("LanguageDetector", model="mistral-small-latest")

    def get_instructions(self) -> str:
        language_codes = ", ".join(ALL_SUPPORTED_LANGUAGE_CODES)
        return (
            "You are a language detection expert for Indian languages. Identify the primary "
            "language code of the user text, including code-mixed romanized inputs. "
            f"Supported language codes: {language_codes}. "
            "Respond with JSON: "
            "{\"language\": \"<iso_code>\", \"confidence\": <0-1>, \"script\": \"<script_name|unknown>\"}"
        )

    async def _llm_disambiguation(self, text: str) -> tuple[str | None, float]:
        prompt = (
            "Identify the primary language code for this text. "
            f"Allowed codes: {', '.join(ALL_SUPPORTED_LANGUAGE_CODES)}.\n\n"
            f'TEXT: "{text}"\n\n'
            "Respond ONLY as JSON: "
            "{\"language\": \"<iso_code>\", \"confidence\": <0-1>, \"script\": \"...\"}"
        )
        response = await self._query(prompt)
        parsed = self._parse_response(response)
        if not isinstance(parsed, dict):
            return None, 0.0
        code = normalize_language_code(parsed.get("language"))
        if code not in LANGUAGE_METADATA:
            return None, 0.0
        try:
            confidence = float(parsed.get("confidence", 0.55))
        except (TypeError, ValueError):
            confidence = 0.55
        return code, max(0.0, min(1.0, confidence))

    async def process(self, data: dict) -> dict:
        text = str(data.get("text", "") or "").strip()
        if not text:
            return {"language": "en", "confidence": 0.2, "method": "default", "script": "unknown"}

        detected_lang = None
        confidence = 0.0
        method = "default"

        if LANGDETECT_AVAILABLE:
            try:
                candidate = detect(text)
                mapped = LANGDETECT_CODE_MAP.get(candidate)
                if mapped:
                    detected_lang = mapped
                    confidence = 0.84
                    method = "langdetect"
            except Exception:
                pass

        script_name, script_count = _detect_script(text)
        if script_name and script_name != "latin":
            candidates = SCRIPT_TO_LANGUAGE_CODES.get(script_name, [])
            if len(candidates) == 1:
                detected_lang = candidates[0]
                confidence = 0.9
                method = "unicode_script"
            elif candidates and detected_lang not in candidates:
                detected_lang = candidates[0]
                confidence = 0.66
                method = "unicode_script_ambiguous"

        if (not detected_lang or script_name == "latin") and len(text) >= 12:
            hinted, hinted_conf = _romanized_hint_language(text)
            if hinted and hinted_conf > confidence:
                detected_lang = hinted
                confidence = hinted_conf
                method = "romanized_heuristic"

        if not detected_lang or (confidence < 0.7 and len(text) >= 18):
            llm_code, llm_conf = await self._llm_disambiguation(text)
            if llm_code and llm_conf >= confidence:
                detected_lang = llm_code
                confidence = max(llm_conf, 0.62)
                method = "mistral_disambiguation"

        if not detected_lang:
            detected_lang = "en"
            confidence = 0.5
            method = "default_en"

        return {
            "language": detected_lang,
            "confidence": round(float(confidence), 3),
            "method": method,
            "script": script_name or "unknown",
            "script_char_count": script_count,
        }
