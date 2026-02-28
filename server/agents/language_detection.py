from server.agents.base_agent import BaseAgent

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

# Unicode ranges for Indian scripts
SCRIPT_RANGES = {
    "hi": [(0x0900, 0x097F)],  # Devanagari
    "ta": [(0x0B80, 0x0BFF)],  # Tamil
    "te": [(0x0C00, 0x0C7F)],  # Telugu
    "bn": [(0x0980, 0x09FF)],  # Bengali
    "mr": [(0x0900, 0x097F)],  # Devanagari (same as Hindi)
    "gu": [(0x0A80, 0x0AFF)],  # Gujarati
}


def detect_script(text: str) -> str | None:
    script_counts = {}
    for char in text:
        cp = ord(char)
        for lang, ranges in SCRIPT_RANGES.items():
            for start, end in ranges:
                if start <= cp <= end:
                    script_counts[lang] = script_counts.get(lang, 0) + 1

    if not script_counts:
        return None
    return max(script_counts, key=script_counts.get)


class LanguageDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__("LanguageDetector", model="mistral-small-latest")

    def get_instructions(self) -> str:
        return (
            "You are a language detection expert. Identify the language of the given text. "
            "Supported languages: Hindi (hi), Tamil (ta), Telugu (te), Bengali (bn), "
            "Marathi (mr), Gujarati (gu), English (en). "
            "Respond with JSON: {\"language\": \"<iso_code>\", \"confidence\": <0-1>, \"script\": \"<script_name>\"}"
        )

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")

        # Try langdetect first
        detected_lang = None
        confidence = 0.0

        if LANGDETECT_AVAILABLE:
            try:
                detected_lang = detect(text)
                confidence = 0.85
            except Exception:
                pass

        # Unicode fallback for Indian scripts
        script_lang = detect_script(text)
        if script_lang and (not detected_lang or detected_lang not in SCRIPT_RANGES):
            detected_lang = script_lang
            confidence = 0.9

        # Default to English
        if not detected_lang:
            detected_lang = "en"
            confidence = 0.5

        # Map langdetect codes to our codes
        lang_map = {"hi": "hi", "ta": "ta", "te": "te", "bn": "bn", "mr": "mr", "gu": "gu", "en": "en"}
        final_lang = lang_map.get(detected_lang, detected_lang)

        return {
            "language": final_lang,
            "confidence": confidence,
            "method": "langdetect+unicode"
        }
