import os
import httpx
from server.agents.base_agent import BaseAgent


class SourceVerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("SourceVerifier", model="mistral-medium-latest")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.search_available = bool(self.google_api_key and self.search_engine_id)

    def get_instructions(self) -> str:
        return (
            "You are a source verification expert. Given a claim and web search results, "
            "assess the credibility of sources and whether they support or refute the claim. "
            "Consider source reliability, publication date, author credibility, and consensus. "
            "Respond with JSON:\n"
            "{\n"
            '  "source_quality": "high|medium|low|none",\n'
            '  "supporting_sources": [{"title": "...", "url": "...", "stance": "supports|refutes|neutral"}],\n'
            '  "consensus": "supports|refutes|mixed|insufficient",\n'
            '  "analysis": "..."\n'
            "}"
        )

    async def _web_search(self, query: str) -> list[dict]:
        if not self.search_available:
            return []
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": 5,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                return [
                    {"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")}
                    for item in data.get("items", [])
                ]
        except Exception as e:
            print(f"[SourceVerifier] Search failed: {e}")
            return []

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        claims = data.get("claims", {})
        main_claim = claims.get("main_claim", text) if isinstance(claims, dict) else text

        search_results = await self._web_search(main_claim)

        if not search_results:
            if not self.search_available:
                return {
                    "source_quality": "none",
                    "supporting_sources": [],
                    "consensus": "insufficient",
                    "analysis": "Web search unavailable (Google API keys not configured).",
                }
            return {
                "source_quality": "none",
                "supporting_sources": [],
                "consensus": "insufficient",
                "analysis": "No search results found.",
            }

        results_text = "\n".join(
            f"- {r['title']}: {r['snippet']} ({r['url']})" for r in search_results
        )

        prompt = (
            f"Verify this claim using the search results below:\n\n"
            f"CLAIM: {main_claim}\n\n"
            f"SEARCH RESULTS:\n{results_text}\n\n"
            f"Respond ONLY with JSON per your instructions."
        )

        response = await self._query(prompt)
        result = self._parse_response(response)

        if "consensus" not in result:
            result = {
                "source_quality": "low",
                "supporting_sources": [],
                "consensus": "insufficient",
                "analysis": response[:500] if response else "Could not analyze sources.",
            }

        return result
