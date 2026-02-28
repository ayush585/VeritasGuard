from server.agents.base_agent import BaseAgent


class ClaimExtractionAgent(BaseAgent):
    def __init__(self):
        super().__init__("ClaimExtractor", model="mistral-medium-latest")

    def get_instructions(self) -> str:
        return (
            "You are a fact-checking expert who extracts verifiable claims from text. "
            "Analyze the input text and identify specific, verifiable factual claims. "
            "For each claim, assess its type (factual, opinion, prediction, etc.) and "
            "how verifiable it is. Always respond with JSON:\n"
            "{\n"
            "  \"claims\": [\n"
            "    {\"claim\": \"...\", \"type\": \"factual|opinion|statistical|prediction\", "
            "\"verifiability\": \"high|medium|low\", \"key_entities\": [\"...\"]}\n"
            "  ],\n"
            "  \"main_claim\": \"...\",\n"
            "  \"category\": \"health|politics|science|religion|social|technology|other\"\n"
            "}"
        )

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        original_text = data.get("original_text", text)

        prompt = (
            f"Extract all verifiable claims from this text:\n\n"
            f"\"{text}\"\n\n"
            f"Original text (may be in a different language): \"{original_text}\"\n\n"
            f"Respond ONLY with the JSON format specified in your instructions."
        )

        response = await self._query(prompt)
        result = self._parse_response(response)

        if "claims" not in result:
            result = {
                "claims": [{"claim": text, "type": "factual", "verifiability": "medium", "key_entities": []}],
                "main_claim": text,
                "category": "other"
            }

        return result
