import asyncio
import os
from typing import Any

import httpx

from server.agents.base_agent import BaseAgent


class SourceVerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("SourceVerifier", model="mistral-medium-latest")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.google_search_available = bool(self.google_api_key and self.search_engine_id)
        self.enable_google_fallback = (
            os.getenv("ENABLE_GOOGLE_SEARCH_FALLBACK", "false").strip().lower() in {"1", "true", "yes", "on"}
        )

    def get_instructions(self) -> str:
        return (
            "You are a source verification expert. Given a claim and web search findings, "
            "assess source credibility and claim consensus. "
            "Prioritize official institutions, high-quality journalism, and cross-source consistency. "
            "Respond with JSON:\n"
            "{\n"
            '  "source_quality": "high|medium|low|none",\n'
            '  "supporting_sources": [{"title": "...", "url": "...", "stance": "supports|refutes|neutral"}],\n'
            '  "consensus": "supports|refutes|mixed|insufficient",\n'
            '  "analysis": "..."\n'
            "}"
        )

    async def _search_with_mistral(self, query: str) -> tuple[list[dict], str]:
        search_prompt = (
            f"Use web search to gather up to 5 high-credibility sources that verify this claim:\n\n"
            f"{query}\n\n"
            "Return short evidence notes with source titles and URLs."
        )

        # Preferred path: conversations API with explicit web_search tool.
        try:
            response = await asyncio.to_thread(
                self.client.beta.conversations.start,
                model=self.model,
                inputs=search_prompt,
                tools=[{"type": "web_search"}],
            )
            text_parts: list[str] = []
            refs: list[dict] = []
            for event in getattr(response, "events", []) or []:
                if getattr(event, "type", "") != "message.output":
                    continue
                content = getattr(event, "content", [])
                if isinstance(content, str):
                    text_parts.append(content)
                    continue
                for item in content or []:
                    item_type = getattr(item, "type", "") or item.get("type", "")
                    if item_type in {"text", "output_text"}:
                        value = getattr(item, "text", None) or item.get("text", "")
                        if value:
                            text_parts.append(str(value))
                    elif item_type in {"url_citation", "citation"}:
                        refs.append(
                            {
                                "title": str(getattr(item, "title", None) or item.get("title", "Untitled")),
                                "url": str(getattr(item, "url", None) or item.get("url", "")),
                                "snippet": str(getattr(item, "content", None) or item.get("content", "")),
                            }
                        )
            summary = "\n".join([part.strip() for part in text_parts if part and part.strip()])
            refs = [r for r in refs if r.get("url")]
            return refs, summary
        except Exception:
            pass

        # Secondary path: chat completion with tool hint if supported.
        try:
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=self.model,
                messages=[{"role": "user", "content": search_prompt}],
                tools=[{"type": "web_search"}],
            )
            content = response.choices[0].message.content
            summary = str(content or "")
            return [], summary
        except Exception as e:
            raise RuntimeError(f"Mistral web search unavailable: {e}") from e

    async def _search_with_google(self, query: str) -> list[dict]:
        if not self.google_search_available:
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
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    }
                    for item in data.get("items", [])
                ]
        except Exception as e:
            print(f"[SourceVerifier] Google fallback failed: {e}")
            return []

    def _default_response(
        self,
        analysis: str,
        provider: str,
        attempted: bool,
        results: list[dict] | None = None,
    ) -> dict[str, Any]:
        return {
            "source_quality": "none",
            "supporting_sources": results or [],
            "consensus": "insufficient",
            "analysis": analysis,
            "search_provider": provider,
            "search_attempted": attempted,
            "search_results_count": len(results or []),
        }

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        claims = data.get("claims", {})
        main_claim = claims.get("main_claim", text) if isinstance(claims, dict) else text
        main_claim = str(main_claim or text).strip()
        if not main_claim:
            return self._default_response(
                "No claim provided for source verification.",
                provider="none",
                attempted=False,
            )

        provider = "mistral_web_search"
        search_attempted = True
        mistral_results: list[dict] = []
        search_summary = ""
        mistral_failed = False

        try:
            mistral_results, search_summary = await self._search_with_mistral(main_claim)
        except Exception as e:
            mistral_failed = True
            search_summary = str(e)

        if (mistral_failed or not mistral_results) and self.enable_google_fallback:
            provider = "google_custom_search_fallback"
            google_results = await self._search_with_google(main_claim)
            if google_results:
                mistral_results = google_results
                search_summary = "\n".join(
                    f"- {item['title']}: {item['snippet']} ({item['url']})" for item in google_results
                )

        if not mistral_results and not search_summary:
            return self._default_response(
                "No web evidence retrieved from Mistral search tooling.",
                provider=provider,
                attempted=search_attempted,
            )

        results_text = "\n".join(
            f"- {r.get('title', 'Untitled')}: {r.get('snippet', '')} ({r.get('url', '')})"
            for r in mistral_results
        )
        prompt = (
            "Assess whether reliable sources support or refute the claim below.\n\n"
            f"CLAIM: {main_claim}\n\n"
            f"SEARCH SUMMARY:\n{search_summary}\n\n"
            f"SEARCH SOURCES:\n{results_text or '[No explicit citations extracted]'}\n\n"
            "Respond ONLY with JSON per your instructions."
        )

        response = await self._query(prompt)
        result = self._parse_response(response)
        if not isinstance(result, dict) or "consensus" not in result:
            result = {
                "source_quality": "low" if mistral_results else "none",
                "supporting_sources": mistral_results,
                "consensus": "insufficient",
                "analysis": response[:500] if response else search_summary[:500],
            }

        if "supporting_sources" not in result or not isinstance(result.get("supporting_sources"), list):
            result["supporting_sources"] = mistral_results
        result["search_provider"] = provider
        result["search_attempted"] = search_attempted
        result["search_results_count"] = len(mistral_results)
        return result
