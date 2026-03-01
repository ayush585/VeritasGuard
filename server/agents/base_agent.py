import asyncio
import os
from abc import ABC, abstractmethod
from server.utils.mistral_client import get_mistral_client, parse_json_safe
from server.utils.mistral_adapter import MistralAdapter


class BaseAgent(ABC):
    def __init__(self, name: str, model: str = "mistral-medium-latest"):
        self.name = name
        self.model = model
        self.client = get_mistral_client()
        self.adapter = MistralAdapter(self.client)
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        capabilities = self.adapter.capability_summary()
        print(f"[{self.name}] Adapter capabilities: {capabilities}")
        self._initialized = True

    @abstractmethod
    def get_instructions(self) -> str:
        pass

    @abstractmethod
    async def process(self, data: dict) -> dict:
        pass

    async def _query(self, prompt: str) -> str:
        await self.initialize()
        max_retries_raw = os.getenv("MISTRAL_QUERY_MAX_RETRIES", "2")
        try:
            max_retries = max(0, int(max_retries_raw))
        except (TypeError, ValueError):
            max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                response = await self.adapter.run_agent_chat(
                    name=self.name,
                    model=self.model,
                    instructions=self.get_instructions(),
                    user_prompt=prompt,
                )
                return str(response.get("text", "") or "")
            except Exception as e:
                error_text = str(e)
                is_rate_limit = "Status 429" in error_text or "rate_limited" in error_text.lower()
                if is_rate_limit and attempt < max_retries:
                    await asyncio.sleep(0.6 * (2**attempt))
                    continue
                print(f"[{self.name}] Query error: {e}")
                return ""

        return ""

    def _parse_response(self, text: str) -> dict:
        return parse_json_safe(text)
