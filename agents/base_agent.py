from abc import ABC, abstractmethod

from llm.provider import complete


class BaseAgent(ABC):
    def __init__(self, provider: str, model_override: str | None = None) -> None:
        self.provider = provider
        self.model_override = model_override

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        ...

    async def _call(self, messages: list[dict], temperature: float = 0.3) -> str:
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages
        return await complete(
            messages=full_messages,
            provider=self.provider,
            model_override=self.model_override,
            temperature=temperature,
        )
