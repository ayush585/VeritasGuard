import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from server.agents.base_agent import BaseAgent
from server.database import search_hoaxes


TRUSTED_DOMAINS: dict[str, float] = {
    "who.int": 0.98,
    "cdc.gov": 0.96,
    "pib.gov.in": 0.95,
    "gov.in": 0.9,
    "gov": 0.9,
    "un.org": 0.9,
    "reuters.com": 0.88,
    "apnews.com": 0.88,
    "bbc.com": 0.87,
    "thehindu.com": 0.84,
    "indianexpress.com": 0.84,
    "thewire.in": 0.8,
    "altnews.in": 0.86,
    "boomlive.in": 0.84,
    "indiatoday.in": 0.8,
}

LOW_VALUE_DOMAINS = {
    "quora.com",
    "pinterest.com",
    "reddit.com",
    "medium.com",
    "blogspot.com",
}


class SourceVerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("SourceVerifier", model="mistral-medium-latest")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.tavily_search_available = bool(self.tavily_api_key)
        self.enable_tavily_fallback = (
            os.getenv("ENABLE_TAVILY_SEARCH_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}
        )
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
            '  "supporting_sources": [{"title": "...", "url": "...", "snippet": "...", '
            '"publisher": "...", "published_at": "", "credibility_tier": "high|medium|low", '
            '"stance": "supports|refutes|neutral"}],\n'
            '  "consensus": "supports|refutes|mixed|insufficient",\n'
            '  "analysis": "..."\n'
            "}"
        )

    def _build_query_variants(self, claim: str, compact_mode: bool) -> list[str]:
        trimmed = claim.strip()
        quoted = f"\"{trimmed}\""
        variants = [
            quoted,
            trimmed,
            f"fact check {trimmed}",
            f"{trimmed} debunk",
        ]
        if compact_mode:
            variants = variants[:2]
        deduped: list[str] = []
        seen = set()
        for query in variants:
            if query and query not in seen:
                deduped.append(query)
                seen.add(query)
        return deduped

    def _domain_from_url(self, raw_url: str) -> str:
        parsed = urlparse(raw_url.strip())
        return (parsed.netloc or "").lower().replace("www.", "")

    def _domain_score(self, domain: str) -> float:
        if not domain:
            return 0.2
        if domain in TRUSTED_DOMAINS:
            return TRUSTED_DOMAINS[domain]
        for trusted_domain, score in TRUSTED_DOMAINS.items():
            if domain.endswith(f".{trusted_domain}") or domain.endswith(trusted_domain):
                return score
        if domain.endswith(".gov") or domain.endswith(".edu") or domain.endswith(".int"):
            return 0.85
        if domain.endswith(".gov.in") or ".gov.in" in domain:
            return 0.9
        return 0.45

    def _credibility_tier(self, domain: str) -> str:
        score = self._domain_score(domain)
        if score >= 0.78:
            return "high"
        if score >= 0.58:
            return "medium"
        return "low"

    def _infer_stance(self, text: str) -> str:
        lowered = (text or "").lower()
        refute_terms = ["false", "hoax", "fake", "debunk", "misleading", "no evidence", "myth"]
        support_terms = ["confirmed", "true", "verified", "evidence shows", "proven", "supports"]
        if any(token in lowered for token in refute_terms):
            return "refutes"
        if any(token in lowered for token in support_terms):
            return "supports"
        return "neutral"

    def _normalize_source(self, raw_source: dict[str, Any], provider: str) -> dict[str, Any] | None:
        url = str(raw_source.get("url", "")).strip()
        if not url.startswith("http"):
            return None
        domain = self._domain_from_url(url)
        if not domain:
            return None
        title = str(raw_source.get("title", "")).strip() or "Untitled"
        snippet = str(raw_source.get("snippet", "")).strip()
        published_at = raw_source.get("published_at") or None
        stance = self._infer_stance(f"{title}\n{snippet}")
        return {
            "title": title,
            "url": url,
            "snippet": snippet,
            "publisher": domain,
            "published_at": published_at,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "credibility_tier": self._credibility_tier(domain),
            "stance": stance,
            "provider": provider,
        }

    def _is_low_value(self, source: dict[str, Any]) -> bool:
        publisher = str(source.get("publisher", ""))
        snippet = str(source.get("snippet", ""))
        title = str(source.get("title", ""))
        if not source.get("url"):
            return True
        if publisher in LOW_VALUE_DOMAINS and len(snippet) < 40:
            return True
        if len(snippet) < 12 and len(title) < 14:
            return True
        return False

    def _dedupe_sources(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen_urls = set()
        seen_title_domain = set()
        for source in sources:
            url = source.get("url")
            publisher = source.get("publisher", "")
            title = str(source.get("title", "")).lower().strip()
            key = (publisher, title)
            if url in seen_urls or key in seen_title_domain:
                continue
            seen_urls.add(url)
            seen_title_domain.add(key)
            deduped.append(source)
        return deduped

    def _score_source_set(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        if not sources:
            return {"overall": 0.0, "source_quality": "none", "agreement": 0.0}

        domain_scores = [self._domain_score(str(item.get("publisher", ""))) for item in sources]
        avg_domain_score = sum(domain_scores) / max(1, len(domain_scores))

        stance_counts = {"supports": 0, "refutes": 0, "neutral": 0}
        for item in sources:
            stance = item.get("stance", "neutral")
            if stance not in stance_counts:
                stance = "neutral"
            stance_counts[stance] += 1

        decisive_count = stance_counts["supports"] + stance_counts["refutes"]
        if decisive_count == 0:
            agreement = 0.4
        else:
            majority = max(stance_counts["supports"], stance_counts["refutes"])
            agreement = majority / decisive_count

        recency_score = 0.5
        dated_items = 0
        recency_total = 0.0
        now = datetime.now(timezone.utc)
        for source in sources:
            published_at = source.get("published_at")
            if not published_at:
                continue
            try:
                published_dt = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
                age_days = max(0.0, (now - published_dt).days)
                dated_items += 1
                if age_days <= 30:
                    recency_total += 1.0
                elif age_days <= 180:
                    recency_total += 0.75
                elif age_days <= 365:
                    recency_total += 0.55
                else:
                    recency_total += 0.35
            except Exception:
                continue
        if dated_items:
            recency_score = recency_total / dated_items

        overall = round((avg_domain_score * 0.55) + (agreement * 0.3) + (recency_score * 0.15), 3)
        if overall >= 0.75:
            source_quality = "high"
        elif overall >= 0.55:
            source_quality = "medium"
        elif overall > 0:
            source_quality = "low"
        else:
            source_quality = "none"
        return {"overall": overall, "source_quality": source_quality, "agreement": round(agreement, 3)}

    def _derive_consensus(self, sources: list[dict[str, Any]]) -> str:
        stance_counts = {"supports": 0, "refutes": 0, "neutral": 0}
        for source in sources:
            stance = source.get("stance", "neutral")
            if stance not in stance_counts:
                stance = "neutral"
            stance_counts[stance] += 1
        if not sources:
            return "insufficient"
        if stance_counts["supports"] == stance_counts["refutes"] and stance_counts["supports"] > 0:
            return "mixed"
        if stance_counts["supports"] > stance_counts["refutes"]:
            return "supports"
        if stance_counts["refutes"] > stance_counts["supports"]:
            return "refutes"
        return "insufficient"

    def _parse_summary_urls(self, summary: str) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for url in re.findall(r"https?://[^\s\]\)]+", summary or ""):
            domain = self._domain_from_url(url)
            if not domain:
                continue
            candidates.append(
                {
                    "title": domain,
                    "url": url,
                    "snippet": "",
                }
            )
        return candidates

    async def _search_with_mistral(self, query: str) -> tuple[list[dict[str, Any]], str, str | None]:
        search_prompt = (
            "Use web search to find up to 6 credible sources for this claim. "
            "Return citations with URLs and concise evidence notes.\n\n"
            f"CLAIM QUERY: {query}"
        )
        # Adapter handles SDK variation and tool-support fallbacks.
        try:
            adapter_response = await self.adapter.run_chat(
                model=self.model,
                messages=[{"role": "user", "content": search_prompt}],
                tools=[{"type": "web_search"}],
            )
            summary = str(adapter_response.get("text", "") or "")
            refs = adapter_response.get("citations", [])
            if not refs and summary:
                refs = self._parse_summary_urls(summary)
            return refs, summary, None
        except Exception as e:
            return [], "", f"Mistral web search unavailable ({e})"

    async def _search_with_google(self, query: str) -> list[dict]:
        if not self.google_search_available:
            return []
        if not str(self.google_api_key or "").startswith("AIza"):
            print("[SourceVerifier] Google fallback skipped: API key format appears invalid.")
            return []

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": 5,
        }
        try:
            async with httpx.AsyncClient(timeout=8) as client:
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

    async def _search_with_tavily(self, query: str) -> list[dict]:
        if not self.tavily_search_available:
            return []
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": False,
            "include_raw_content": False,
        }
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", ""),
                        "published_at": item.get("published_date"),
                    }
                    for item in data.get("results", [])
                ]
        except Exception as e:
            print(f"[SourceVerifier] Tavily fallback failed: {e}")
            return []

    def _default_response(
        self,
        analysis: str,
        provider: str,
        attempted: bool,
        results: list[dict[str, Any]] | None = None,
        warnings: list[str] | None = None,
        evidence_completeness: str = "low",
    ) -> dict[str, Any]:
        return {
            "source_quality": "none",
            "supporting_sources": results or [],
            "consensus": "insufficient",
            "analysis": analysis,
            "search_provider": provider,
            "search_attempted": attempted,
            "search_results_count": len(results or []),
            "warnings": warnings or [],
            "source_score": 0.0,
            "evidence_completeness": evidence_completeness,
        }

    def _supplement_with_known_hoax_references(self, claim: str) -> list[dict[str, Any]]:
        matches = search_hoaxes(claim)
        if not matches:
            return []
        strongest = matches[0]
        references = strongest.get("references", []) if isinstance(strongest, dict) else []
        supplemented = []
        for ref in references[:2]:
            if not isinstance(ref, dict):
                continue
            normalized = self._normalize_source(
                {
                    "title": ref.get("title", "Known Hoax Reference"),
                    "url": ref.get("url", ""),
                    "snippet": ref.get("snippet", strongest.get("explanation", "")),
                    "published_at": ref.get("published_at"),
                },
                provider="local_hoax_reference",
            )
            if normalized:
                normalized["stance"] = "refutes"
                supplemented.append(normalized)
        return supplemented

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        claims = data.get("claims", {})
        compact_mode = bool(data.get("compact_mode", False))
        main_claim = claims.get("main_claim", text) if isinstance(claims, dict) else text
        main_claim = str(main_claim or text).strip()
        if not main_claim:
            return self._default_response(
                "No claim provided for source verification.",
                provider="none",
                attempted=False,
            )

        search_attempted = False
        providers_used: list[str] = []
        warnings: list[str] = []
        summary_parts: list[str] = []
        normalized_sources: list[dict[str, Any]] = []

        query_variants = self._build_query_variants(main_claim, compact_mode=compact_mode)
        for query in query_variants:
            search_attempted = True
            mistral_results, search_summary, mistral_error = await self._search_with_mistral(query)
            if mistral_error:
                warnings.append(mistral_error)
            if search_summary:
                summary_parts.append(search_summary[:300])
            if mistral_results:
                if "mistral_web_search" not in providers_used:
                    providers_used.append("mistral_web_search")
                normalized_sources.extend(
                    source
                    for source in (
                        self._normalize_source(item, provider="mistral_web_search") for item in mistral_results
                    )
                    if source is not None
                )
                normalized_sources = self._dedupe_sources(normalized_sources)
                normalized_sources = [source for source in normalized_sources if not self._is_low_value(source)]
                score = self._score_source_set(normalized_sources)
                if score["overall"] >= 0.72 and len(normalized_sources) >= 2:
                    break

        current_score = self._score_source_set(normalized_sources)
        should_try_tavily = self.enable_tavily_fallback and (
            not normalized_sources or current_score["overall"] < 0.45
        )
        if should_try_tavily:
            if self.tavily_search_available:
                for query in query_variants[:2]:
                    tavily_results = await self._search_with_tavily(query)
                    if not tavily_results:
                        continue
                    if "tavily_search_fallback" not in providers_used:
                        providers_used.append("tavily_search_fallback")
                    normalized_sources.extend(
                        source
                        for source in (
                            self._normalize_source(item, provider="tavily_search_fallback")
                            for item in tavily_results
                        )
                        if source is not None
                    )
                    normalized_sources = self._dedupe_sources(normalized_sources)
                    normalized_sources = [source for source in normalized_sources if not self._is_low_value(source)]
                    current_score = self._score_source_set(normalized_sources)
                    if current_score["overall"] >= 0.72 and len(normalized_sources) >= 2:
                        break
            else:
                warnings.append("Tavily fallback enabled but TAVILY_API_KEY is unavailable.")

        should_try_google = self.enable_google_fallback and (
            not normalized_sources or current_score["overall"] < 0.45
        )
        if should_try_google:
            if self.google_search_available:
                for query in query_variants[:2]:
                    google_results = await self._search_with_google(query)
                    if not google_results:
                        continue
                    if "google_custom_search_fallback" not in providers_used:
                        providers_used.append("google_custom_search_fallback")
                    normalized_sources.extend(
                        source
                        for source in (
                            self._normalize_source(item, provider="google_custom_search_fallback")
                            for item in google_results
                        )
                        if source is not None
                    )
                    normalized_sources = self._dedupe_sources(normalized_sources)
                    normalized_sources = [source for source in normalized_sources if not self._is_low_value(source)]
                    current_score = self._score_source_set(normalized_sources)
                    if current_score["overall"] >= 0.72 and len(normalized_sources) >= 2:
                        break
            else:
                warnings.append("Google fallback enabled but GOOGLE_API_KEY/GOOGLE_SEARCH_ENGINE_ID are unavailable.")

        final_sources = normalized_sources[:6]
        provider = "+".join(providers_used) if providers_used else "mistral_web_search"
        if not final_sources:
            analysis = "No high-quality evidence retrieved from configured search providers."
            if summary_parts:
                analysis = f"{analysis} Search summary: {' '.join(summary_parts)[:420]}"
            supplements = self._supplement_with_known_hoax_references(main_claim)
            if supplements:
                provider = f"{provider}+local_hoax_reference" if provider != "mistral_web_search" else "local_hoax_reference"
                analysis = (
                    "External web retrieval returned insufficient evidence; supplemented with known-hoax "
                    "curated references."
                )
                return self._default_response(
                    analysis=analysis,
                    provider=provider,
                    attempted=search_attempted,
                    warnings=warnings,
                    results=supplements,
                    evidence_completeness="medium",
                )
            return self._default_response(
                analysis=analysis,
                provider=provider,
                attempted=search_attempted,
                warnings=warnings,
            )

        current_score = self._score_source_set(final_sources)
        results_text = "\n".join(
            (
                f"- [{source['credibility_tier']}] {source['title']} ({source['url']}) "
                f"stance={source['stance']} snippet={source.get('snippet', '')[:220]}"
            )
            for source in final_sources
        )
        prompt = (
            "Assess whether reliable sources support or refute the claim below.\n\n"
            f"CLAIM: {main_claim}\n\n"
            f"SOURCE SCORE: {current_score['overall']}\n"
            f"SEARCH SOURCES:\n{results_text}\n\n"
            "Respond ONLY with JSON per your instructions."
        )
        if compact_mode:
            prompt = (
                "Return concise JSON verdict from the provided web evidence.\n\n"
                f"CLAIM: {main_claim}\nSOURCES:\n{results_text}\n"
            )

        response = await self._query(prompt)
        result = self._parse_response(response)
        if not isinstance(result, dict) or "consensus" not in result:
            result = {
                "source_quality": current_score["source_quality"],
                "supporting_sources": final_sources,
                "consensus": self._derive_consensus(final_sources),
                "analysis": (
                    response[:500]
                    if response
                    else f"Derived from {len(final_sources)} normalized sources with score {current_score['overall']}."
                ),
            }

        parsed_sources = result.get("supporting_sources", [])
        normalized_from_model = []
        if isinstance(parsed_sources, list):
            normalized_from_model = [
                normalized
                for normalized in (
                    self._normalize_source(item, provider=provider) for item in parsed_sources if isinstance(item, dict)
                )
                if normalized is not None
            ]

        if normalized_from_model:
            final_sources = self._dedupe_sources(normalized_from_model + final_sources)[:6]

        result["supporting_sources"] = final_sources
        result["source_quality"] = result.get("source_quality") or current_score["source_quality"]
        result["search_provider"] = provider
        result["search_attempted"] = search_attempted
        result["search_results_count"] = len(final_sources)
        result["source_score"] = current_score["overall"]
        result["warnings"] = warnings
        if len(final_sources) >= 3 and current_score["source_quality"] in {"high", "medium"}:
            result["evidence_completeness"] = "high"
        elif len(final_sources) >= 1:
            result["evidence_completeness"] = "medium"
            if len(final_sources) < 2:
                warnings.append("Evidence completeness low: fewer than 2 unique sources.")
        else:
            result["evidence_completeness"] = "low"
        return result
