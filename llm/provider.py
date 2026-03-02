import asyncio
import os
import time

import litellm

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

litellm.drop_params = True

# Propagate API keys from pydantic-settings to os.environ so LiteLLM can find them
if settings.ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
if settings.OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
if settings.GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
os.environ.setdefault("OLLAMA_API_BASE", settings.OLLAMA_BASE_URL)


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

    extra_kwargs: dict = {}
    if provider == "ollama":
        extra_kwargs["api_base"] = settings.OLLAMA_BASE_URL

    for attempt in range(1, max_retries + 1):
        try:
            start = time.monotonic()
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                **extra_kwargs,
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
