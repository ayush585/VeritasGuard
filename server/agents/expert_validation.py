from server.agents.base_agent import BaseAgent


class ExpertValidationAgent(BaseAgent):
    def __init__(self):
        super().__init__("ExpertValidator", model="mistral-medium-latest")

    def get_instructions(self) -> str:
        return (
            "You are an expert fact-checker with deep knowledge of Indian current affairs, "
            "science, health, politics, and social issues. Validate claims by checking them "
            "against authoritative sources such as government agencies (PIB, ICMR, WHO), "
            "established fact-checkers (Alt News, Boom Live, India Today Fact Check), "
            "and scientific consensus. "
            "Respond with JSON:\n"
            "{\n"
            '  "expert_verdict": "TRUE|FALSE|MOSTLY_TRUE|MOSTLY_FALSE|PARTIALLY_TRUE|UNVERIFIABLE",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "authoritative_sources": ["..."],\n'
            '  "domain": "health|politics|science|religion|social|technology|other",\n'
            '  "reasoning": "...",\n'
            '  "caveats": ["..."]\n'
            "}"
        )

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        claims = data.get("claims", {})
        main_claim = claims.get("main_claim", text) if isinstance(claims, dict) else text

        prompt = (
            f"As an expert fact-checker, validate this claim:\n\n"
            f"CLAIM: {main_claim}\n\n"
            f"ALL EXTRACTED CLAIMS: {claims}\n\n"
            f"Use your knowledge of authoritative sources to assess this claim. "
            f"Respond ONLY with JSON per your instructions."
        )

        response = await self._query(prompt)
        result = self._parse_response(response)

        if "expert_verdict" not in result:
            result = {
                "expert_verdict": "UNVERIFIABLE",
                "confidence": 0.3,
                "authoritative_sources": [],
                "domain": "other",
                "reasoning": response[:500] if response else "Could not complete expert validation.",
                "caveats": ["Expert analysis was limited"],
            }

        return result
