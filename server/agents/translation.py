from server.agents.base_agent import BaseAgent
from server.languages import get_language_name, normalize_language_code


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
        source_lang = normalize_language_code(data.get("source_language", "hi"))
        target_lang = normalize_language_code(data.get("target_language", "en"))

        if source_lang == target_lang:
            return {
                "translated_text": text,
                "source_language": source_lang,
                "target_language": target_lang
            }

        source_name = get_language_name(source_lang)
        target_name = get_language_name(target_lang)

        prompt = (
            f"Translate the following text from {source_name} to {target_name}. "
            "Preserve meaning, named entities, and factual claims exactly. "
            "Do not add commentary.\n\n"
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
