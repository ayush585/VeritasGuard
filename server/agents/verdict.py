from server.agents.base_agent import BaseAgent


LANGUAGE_NAMES = {
    "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
    "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "en": "English"
}


class VerdictAgent(BaseAgent):
    def __init__(self):
        super().__init__("VerdictSynthesizer", model="mistral-medium-latest")

    def get_instructions(self) -> str:
        return (
            "You are a fact-checking verdict synthesizer. Given evidence from multiple verification agents, "
            "produce a final verdict. Verdicts must be one of: TRUE, FALSE, MOSTLY_TRUE, MOSTLY_FALSE, "
            "PARTIALLY_TRUE, UNVERIFIABLE. Provide a confidence score (0-1) and detailed explanation.\n"
            "Always respond with JSON:\n"
            "{\n"
            "  \"verdict\": \"TRUE|FALSE|MOSTLY_TRUE|MOSTLY_FALSE|PARTIALLY_TRUE|UNVERIFIABLE\",\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"summary\": \"English explanation of the verdict\",\n"
            "  \"key_evidence\": [\"point 1\", \"point 2\"],\n"
            "  \"sources_quality\": \"high|medium|low|none\"\n"
            "}"
        )

    async def process(self, data: dict) -> dict:
        claims = data.get("claims", {})
        source_results = data.get("source_verification", {})
        media_results = data.get("media_forensics", {})
        context_results = data.get("context_history", {})
        expert_results = data.get("expert_validation", {})
        original_text = data.get("original_text", "")
        original_language = data.get("original_language", "en")

        prompt = (
            f"Synthesize a fact-checking verdict based on the following evidence:\n\n"
            f"ORIGINAL CLAIM: {original_text}\n\n"
            f"EXTRACTED CLAIMS: {claims}\n\n"
            f"SOURCE VERIFICATION: {source_results}\n\n"
            f"MEDIA FORENSICS: {media_results}\n\n"
            f"CONTEXT & HISTORY: {context_results}\n\n"
            f"EXPERT VALIDATION: {expert_results}\n\n"
            f"Provide your verdict as JSON per your instructions."
        )

        response = await self._query(prompt)
        result = self._parse_response(response)

        if "verdict" not in result:
            result = {
                "verdict": "UNVERIFIABLE",
                "confidence": 0.3,
                "summary": "Unable to determine verdict due to insufficient evidence.",
                "key_evidence": [],
                "sources_quality": "none"
            }

        # Translate summary to original language if needed
        if original_language != "en":
            lang_name = LANGUAGE_NAMES.get(original_language, original_language)
            translate_prompt = (
                f"Translate this fact-check summary to {lang_name}. "
                f"Keep it clear and accessible:\n\n"
                f"\"{result.get('summary', '')}\"\n\n"
                f"Respond with JSON: {{\"native_summary\": \"...\"}}"
            )
            trans_response = await self._query(translate_prompt)
            trans_result = self._parse_response(trans_response)
            result["native_summary"] = trans_result.get("native_summary", result.get("summary", ""))
        else:
            result["native_summary"] = result.get("summary", "")

        return result
