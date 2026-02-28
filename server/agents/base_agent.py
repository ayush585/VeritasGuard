import asyncio
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
            print(f"[{self.name}] Query error: {e}")
            return ""

    def _parse_response(self, text: str) -> dict:
        return parse_json_safe(text)
