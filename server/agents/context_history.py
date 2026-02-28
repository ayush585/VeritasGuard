from server.agents.base_agent import BaseAgent
from server.database import search_hoaxes


class ContextHistoryAgent(BaseAgent):
    def __init__(self):
        super().__init__("ContextHistory", model="mistral-medium-latest")

    def get_instructions(self) -> str:
        return (
            "You are a fact-checking context expert. Given a claim and any matching known hoaxes, "
            "provide historical context about similar claims. Identify if this is a recurring "
            "misinformation pattern, a seasonal hoax, or connected to known disinformation campaigns. "
            "Respond with JSON:\n"
            "{\n"
            '  "known_hoax_match": true|false,\n'
            '  "match_confidence": 0.0-1.0,\n'
            '  "historical_context": "...",\n'
            '  "pattern_type": "recurring|seasonal|one-time|campaign|unknown",\n'
            '  "similar_claims": ["..."],\n'
            '  "recommendation": "..."\n'
            "}"
        )

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        original_text = data.get("original_text", text)
        claims = data.get("claims", {})

        # Search known hoaxes database
        hoax_matches = search_hoaxes(text)
        if original_text != text:
            hoax_matches += search_hoaxes(original_text)

        # Deduplicate by claim text
        seen = set()
        unique_matches = []
        for m in hoax_matches:
            if m["claim"] not in seen:
                seen.add(m["claim"])
                unique_matches.append(m)

        if unique_matches:
            matches_text = "\n".join(
                f"- [{m['verdict']}] {m['claim']}: {m['explanation']} (score: {m['match_score']:.2f})"
                for m in unique_matches
            )
        else:
            matches_text = "No matches found in known hoaxes database."

        prompt = (
            f"Analyze the historical context of this claim:\n\n"
            f"CLAIM: {text}\n\n"
            f"ORIGINAL TEXT: {original_text}\n\n"
            f"KNOWN HOAX MATCHES:\n{matches_text}\n\n"
            f"EXTRACTED CLAIMS: {claims}\n\n"
            f"Respond ONLY with JSON per your instructions."
        )

        response = await self._query(prompt)
        result = self._parse_response(response)

        if "known_hoax_match" not in result:
            result = {
                "known_hoax_match": len(unique_matches) > 0,
                "match_confidence": unique_matches[0]["match_score"] if unique_matches else 0.0,
                "historical_context": response[:500] if response else "No context available.",
                "pattern_type": "unknown",
                "similar_claims": [m["claim"] for m in unique_matches],
                "recommendation": "Manual review recommended.",
            }

        # Inject raw DB matches for the verdict agent
        result["db_matches"] = unique_matches

        return result
