import asyncio
import os
from abc import ABC, abstractmethod
from server.utils.mistral_client import get_mistral_client, parse_json_safe


class BaseAgent(ABC):
    def __init__(self, name: str, model: str = "mistral-medium-latest"):
        self.name = name
        self.model = model
        self.client = get_mistral_client()
        self.agent_id = None
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        # Try to create a Mistral agent via the beta API
        try:
            agent = await asyncio.to_thread(
                self.client.beta.agents.create,
                name=self.name,
                model=self.model,
                instructions=self.get_instructions(),
            )
            self.agent_id = agent.id
            print(f"[{self.name}] Created Mistral agent: {self.agent_id}")
        except Exception as e:
            print(f"[{self.name}] Agent API unavailable, using direct chat: {e}")
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
                if self.agent_id:
                    # Use the agents conversational endpoint
                    try:
                        response = await asyncio.to_thread(
                            self.client.beta.agents.chat,
                            agent_id=self.agent_id,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        return response.choices[0].message.content
                    except Exception:
                        pass  # fall through to direct chat

                # Fallback: direct chat.complete with system prompt
                try:
                    response = await asyncio.to_thread(
                        self.client.chat.complete,
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    return response.choices[0].message.content
                except Exception:
                    response = await asyncio.to_thread(
                        self.client.chat.complete,
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self.get_instructions()},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    return response.choices[0].message.content
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
