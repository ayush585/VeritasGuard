from server.agents.base_agent import BaseAgent
from server.database import search_hoaxes
import re
import unicodedata


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

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
        return re.sub(r"\s+", " ", normalized).strip()

    def _score_overlap(self, text: str, phrase: str) -> float:
        text_tokens = set(self._normalize_text(text).split())
        phrase_tokens = set(self._normalize_text(phrase).split())
        if not text_tokens or not phrase_tokens:
            return 0.0
        return len(text_tokens.intersection(phrase_tokens)) / len(phrase_tokens)

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

        for match in unique_matches:
            overlap = max(
                self._score_overlap(text, match["claim"]),
                self._score_overlap(original_text, match["claim"]),
            )
            match["overlap_score"] = round(overlap, 3)
            match["combined_score"] = round(max(match.get("match_score", 0.0), overlap), 3)
        unique_matches.sort(key=lambda item: item.get("combined_score", 0.0), reverse=True)

        if unique_matches:
            matches_text = "\n".join(
                f"- [{m['verdict']}] {m['claim']}: {m['explanation']} "
                f"(db: {m['match_score']:.2f}, overlap: {m['overlap_score']:.2f})"
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

        if not isinstance(result, dict) or "known_hoax_match" not in result:
            strongest_match = unique_matches[0] if unique_matches else None
            result = {
                "known_hoax_match": len(unique_matches) > 0,
                "match_confidence": strongest_match["combined_score"] if strongest_match else 0.0,
                "historical_context": response[:500] if response else "No context available.",
                "pattern_type": "recurring" if unique_matches else "unknown",
                "similar_claims": [m["claim"] for m in unique_matches],
                "recommendation": "Manual review recommended.",
            }

        # Inject raw DB matches for the verdict agent
        result["db_matches"] = unique_matches
        result["matched_claim_count"] = len(unique_matches)
        if "match_confidence" not in result:
            result["match_confidence"] = unique_matches[0]["combined_score"] if unique_matches else 0.0
        if "pattern_type" not in result:
            result["pattern_type"] = "recurring" if unique_matches else "unknown"

        return result
