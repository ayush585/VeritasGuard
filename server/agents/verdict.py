from server.agents.base_agent import BaseAgent
from server.languages import get_language_name, normalize_language_code


DETERMINISTIC_OVERRIDE_THRESHOLD = 0.82
DETERMINISTIC_STRONG_THRESHOLD = 0.9
HIGH_RISK_CATEGORIES = {"communal", "health", "panic", "scam", "election"}


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

    def _deterministic_known_hoax_override(self, context_results: dict, source_results: dict) -> dict | None:
        if not isinstance(context_results, dict):
            return None
        if not context_results.get("known_hoax_match"):
            return None

        try:
            match_confidence = float(context_results.get("match_confidence", 0.0))
        except (TypeError, ValueError):
            match_confidence = 0.0
        if match_confidence < DETERMINISTIC_OVERRIDE_THRESHOLD:
            return None

        best_match = {}
        db_matches = context_results.get("db_matches", [])
        if isinstance(db_matches, list) and db_matches:
            best_match = db_matches[0] if isinstance(db_matches[0], dict) else {}

        risk_category = str(context_results.get("risk_category") or best_match.get("risk_category") or "unknown").lower()
        if risk_category not in HIGH_RISK_CATEGORIES:
            return None

        keyword_hits = int(best_match.get("keyword_hits", 0) or 0)
        overlap_score = float(best_match.get("overlap_score", 0.0) or 0.0)
        combined_score = float(best_match.get("combined_score", 0.0) or match_confidence)
        if keyword_hits < 1 or overlap_score < 0.35 or combined_score < DETERMINISTIC_OVERRIDE_THRESHOLD:
            return None

        forced_verdict = "FALSE" if match_confidence >= DETERMINISTIC_STRONG_THRESHOLD else "MOSTLY_FALSE"
        confidence = min(0.93, max(0.72, match_confidence))
        evidence = []
        matched_claim = best_match.get("claim")
        explanation = best_match.get("explanation")
        if matched_claim:
            evidence.append(f"Known hoax match: {matched_claim}")
        if explanation:
            evidence.append(f"Historical context: {explanation}")
        if not evidence:
            evidence.append("Known recurring hoax pattern matched with high confidence.")

        summary = (
            "Known recurring hoax pattern matched with high confidence in the historical database. "
            "To prevent unsafe ambiguity, this claim is treated as misinformation."
        )
        return {
            "verdict": forced_verdict,
            "confidence": round(confidence, 3),
            "summary": summary,
            "key_evidence": evidence,
            "sources_quality": source_results.get("source_quality", "low") if isinstance(source_results, dict) else "low",
            "deterministic_override_applied": True,
            "override_reason": "known_hoax_high_confidence",
            "override_match_score": round(match_confidence, 3),
        }

    async def process(self, data: dict) -> dict:
        claims = data.get("claims", {})
        source_results = data.get("source_verification", {})
        media_results = data.get("media_forensics", {})
        context_results = data.get("context_history", {})
        expert_results = data.get("expert_validation", {})
        original_text = data.get("original_text", "")
        original_language = data.get("original_language", "en")

        deterministic_result = self._deterministic_known_hoax_override(context_results, source_results)
        if deterministic_result:
            result = deterministic_result
        else:
            prompt = (
                f"Synthesize a fact-checking verdict based on the following evidence:\n\n"
                f"ORIGINAL CLAIM: {original_text}\n\n"
                f"EXTRACTED CLAIMS: {claims}\n\n"
                f"SOURCE VERIFICATION: {source_results}\n\n"
                f"MEDIA FORENSICS: {media_results}\n\n"
                f"CONTEXT & HISTORY: {context_results}\n\n"
                f"EXPERT VALIDATION: {expert_results}\n\n"
                "Prioritize evidence quality as follows: "
                "1) credible independent sources, "
                "2) known-hoax database matches, "
                "3) expert consistency confidence, "
                "4) media manipulation signals. "
                "If sources are weak or conflicting, reduce confidence.\n\n"
                "Provide your verdict as JSON per your instructions."
            )

            response = await self._query(prompt)
            result = self._parse_response(response)

            if "verdict" not in result:
                result = {
                    "verdict": "UNVERIFIABLE",
                    "confidence": 0.3,
                    "summary": "Unable to determine verdict due to insufficient evidence.",
                    "key_evidence": [],
                    "sources_quality": "none",
                }
            result["deterministic_override_applied"] = False
            result["override_reason"] = None
            result["override_match_score"] = None

        if result.get("verdict") == "UNVERIFIABLE":
            override_on_unverifiable = self._deterministic_known_hoax_override(context_results, source_results)
            if override_on_unverifiable:
                result = override_on_unverifiable

        # Translate summary to original language if needed
        original_language = normalize_language_code(original_language)
        if original_language != "en":
            lang_name = get_language_name(original_language)
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
