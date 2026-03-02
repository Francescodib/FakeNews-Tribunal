import asyncio
import time

import litellm

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

litellm.drop_params = True


def resolve_model(provider: str, model_override: str | None = None) -> str:
    if model_override:
        return model_override
    return settings.PROVIDER_MODEL_MAP.get(provider, settings.PROVIDER_MODEL_MAP["anthropic"])


async def complete(
    messages: list[dict],
    provider: str,
    model_override: str | None = None,
    temperature: float = 0.3,
    max_retries: int = 3,
) -> str:
    model = resolve_model(provider, model_override)
    delay = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            start = time.monotonic()
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            usage = response.usage or {}
            logger.info(
                "llm.complete",
                provider=provider,
                model=model,
                elapsed_ms=elapsed_ms,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning(
                "llm.error",
                attempt=attempt,
                max_retries=max_retries,
                error=str(exc),
            )
            if attempt == max_retries:
                raise
            await asyncio.sleep(delay)
            delay *= 2

    raise RuntimeError("LLM completion failed after retries")
