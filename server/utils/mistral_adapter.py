import asyncio
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MistralCapabilities:
    chat_complete: bool
    ocr_process: bool
    beta_agents: bool
    beta_conversations: bool
    tools_in_chat: bool


class MistralAdapter:
    """SDK-compatibility adapter for Mistral API variants."""

    def __init__(self, client: Any):
        self.client = client
        self.capabilities = MistralCapabilities(
            chat_complete=bool(getattr(getattr(client, "chat", None), "complete", None)),
            ocr_process=bool(getattr(getattr(client, "ocr", None), "process", None)),
            beta_agents=bool(
                getattr(getattr(getattr(client, "beta", None), "agents", None), "create", None)
                and getattr(getattr(getattr(client, "beta", None), "agents", None), "chat", None)
            ),
            beta_conversations=bool(getattr(getattr(getattr(client, "beta", None), "conversations", None), "start", None)),
            tools_in_chat=bool(getattr(getattr(client, "chat", None), "complete", None)),
        )

    def capability_summary(self) -> dict[str, bool]:
        return {
            "chat_complete": self.capabilities.chat_complete,
            "ocr_process": self.capabilities.ocr_process,
            "beta_agents": self.capabilities.beta_agents,
            "beta_conversations": self.capabilities.beta_conversations,
            "tools_in_chat": self.capabilities.tools_in_chat,
        }

    async def run_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        if timeout:
            kwargs["timeout_ms"] = int(timeout * 1000)

        try:
            response = await asyncio.to_thread(self.client.chat.complete, **kwargs)
        except Exception:
            # Some SDK versions reject `tools`; retry without it.
            if tools:
                kwargs.pop("tools", None)
                response = await asyncio.to_thread(self.client.chat.complete, **kwargs)
            else:
                raise

        text = self._extract_text(response)
        citations = self._extract_citations(response, text)
        return {"text": text, "tool_events": [], "citations": citations, "raw": response}

    async def run_agent_chat(
        self,
        *,
        name: str,
        model: str,
        instructions: str,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        # Best path: beta agents (if available in current SDK).
        if self.capabilities.beta_agents:
            try:
                agent = await asyncio.to_thread(
                    self.client.beta.agents.create,
                    name=name,
                    model=model,
                    instructions=instructions,
                )
                response = await asyncio.to_thread(
                    self.client.beta.agents.chat,
                    agent_id=agent.id,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text = self._extract_text(response)
                citations = self._extract_citations(response, text)
                return {"text": text, "tool_events": [], "citations": citations, "raw": response}
            except Exception:
                pass

        # Next-best: conversations endpoint with tools.
        if self.capabilities.beta_conversations and tools:
            try:
                response = await asyncio.to_thread(
                    self.client.beta.conversations.start,
                    model=model,
                    inputs=user_prompt,
                    tools=tools,
                )
                text = self._extract_conversation_text(response)
                citations = self._extract_conversation_citations(response, text)
                return {"text": text, "tool_events": [], "citations": citations, "raw": response}
            except Exception:
                pass

        # Universal fallback: direct chat with system instructions.
        return await self.run_chat(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_prompt},
            ],
            tools=tools,
            timeout=timeout,
        )

    async def run_ocr_image(
        self,
        *,
        data_url: str,
        timeout: float | None = None,
        ocr_model: str = "mistral-ocr-latest",
        vision_model: str = "pixtral-large-latest",
    ) -> dict[str, Any]:
        if self.capabilities.ocr_process:
            try:
                response = await asyncio.to_thread(
                    self.client.ocr.process,
                    model=ocr_model,
                    document={"type": "image_url", "image_url": data_url},
                )
                text = self._extract_ocr_text(response)
                if text.strip():
                    return {"text": text.strip(), "tool_events": [], "citations": [], "raw": response}
            except Exception:
                pass

        chat_result = await self.run_chat(
            model=vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": "Extract all visible text from this image. Return only extracted text."},
                    ],
                }
            ],
            timeout=timeout,
        )
        return chat_result

    def _extract_text(self, response: Any) -> str:
        try:
            content = response.choices[0].message.content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        parts.append(str(item.get("text", "")))
                    else:
                        parts.append(str(getattr(item, "text", "")))
                return "\n".join([p for p in parts if p]).strip()
            return str(content or "").strip()
        except Exception:
            return str(response or "")

    def _extract_citations(self, response: Any, text: str) -> list[dict[str, str]]:
        citations: list[dict[str, str]] = []
        # SDK-native citation parsing if available.
        try:
            message = response.choices[0].message
            for item in getattr(message, "content", []) or []:
                item_type = getattr(item, "type", "")
                if item_type in {"url_citation", "citation"}:
                    citations.append(
                        {
                            "title": str(getattr(item, "title", "") or "Citation"),
                            "url": str(getattr(item, "url", "") or ""),
                            "snippet": str(getattr(item, "content", "") or ""),
                        }
                    )
        except Exception:
            pass

        # Fallback URL extraction from generated text.
        if not citations and text:
            for url in re.findall(r"https?://[^\s\]\)]+", text):
                citations.append({"title": "Extracted URL", "url": url, "snippet": ""})
        return citations

    def _extract_conversation_text(self, response: Any) -> str:
        parts: list[str] = []
        for event in getattr(response, "events", []) or []:
            if getattr(event, "type", "") != "message.output":
                continue
            content = getattr(event, "content", []) or []
            if isinstance(content, str):
                parts.append(content)
                continue
            for item in content:
                item_type = getattr(item, "type", "") or (item.get("type", "") if isinstance(item, dict) else "")
                if item_type in {"text", "output_text"}:
                    text = getattr(item, "text", None) or (item.get("text", "") if isinstance(item, dict) else "")
                    if text:
                        parts.append(str(text))
        return "\n".join([p.strip() for p in parts if p and str(p).strip()])

    def _extract_conversation_citations(self, response: Any, text: str) -> list[dict[str, str]]:
        refs: list[dict[str, str]] = []
        for event in getattr(response, "events", []) or []:
            if getattr(event, "type", "") != "message.output":
                continue
            content = getattr(event, "content", []) or []
            for item in content:
                item_type = getattr(item, "type", "") or (item.get("type", "") if isinstance(item, dict) else "")
                if item_type in {"url_citation", "citation"}:
                    refs.append(
                        {
                            "title": str(
                                getattr(item, "title", None)
                                or (item.get("title", "Citation") if isinstance(item, dict) else "Citation")
                            ),
                            "url": str(
                                getattr(item, "url", None)
                                or (item.get("url", "") if isinstance(item, dict) else "")
                            ),
                            "snippet": str(
                                getattr(item, "content", None)
                                or (item.get("content", "") if isinstance(item, dict) else "")
                            ),
                        }
                    )
        if not refs and text:
            return self._extract_citations({}, text)
        return refs

    def _extract_ocr_text(self, response: Any) -> str:
        pages = getattr(response, "pages", None)
        if pages is None and isinstance(response, dict):
            pages = response.get("pages", [])
        extracted_parts = []
        for page in pages or []:
            markdown = getattr(page, "markdown", None)
            if markdown is None and isinstance(page, dict):
                markdown = page.get("markdown", "")
            if markdown:
                extracted_parts.append(str(markdown).strip())
        return "\n\n".join(part for part in extracted_parts if part)
