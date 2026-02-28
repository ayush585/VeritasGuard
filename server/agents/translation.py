from server.agents.base_agent import BaseAgent


LANGUAGE_NAMES = {
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "en": "English"
}


class TranslationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Translator", model="mistral-medium-latest")

    def get_instructions(self) -> str:
        return (
            "You are an expert translator specializing in Indian languages. "
            "Translate text accurately while preserving meaning, context, and nuance. "
            "Always respond with JSON: {\"translated_text\": \"...\", \"source_language\": \"...\", \"target_language\": \"...\"}"
        )

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        source_lang = data.get("source_language", "hi")
        target_lang = data.get("target_language", "en")

        if source_lang == target_lang:
            return {
                "translated_text": text,
                "source_language": source_lang,
                "target_language": target_lang
            }

        source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
        target_name = LANGUAGE_NAMES.get(target_lang, target_lang)

        prompt = (
            f"Translate the following {source_name} text to {target_name}. "
            f"Preserve the original meaning exactly.\n\n"
            f"Text: {text}\n\n"
            f"Respond ONLY with JSON: {{\"translated_text\": \"...\", \"source_language\": \"{source_lang}\", \"target_language\": \"{target_lang}\"}}"
        )

        response = await self._query(prompt)
        result = self._parse_response(response)

        if "translated_text" not in result:
            # If parsing failed, use the raw response as translation
            result = {
                "translated_text": response.strip(),
                "source_language": source_lang,
                "target_language": target_lang
            }

        return result
