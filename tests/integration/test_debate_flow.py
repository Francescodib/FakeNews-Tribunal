"""
Integration tests — run only with real API keys.
Skip by default unless RUN_INTEGRATION=1 is set.
"""
import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Set RUN_INTEGRATION=1 to run integration tests",
)


@pytest.mark.asyncio
async def test_full_debate_flow():
    from agents.orchestrator import DebateOrchestrator

    orchestrator = DebateOrchestrator(provider="anthropic", max_rounds=2)
    result = await orchestrator.run(
        claim="The Great Wall of China is visible from space.",
        language="en",
    )

    assert result.verdict is not None
    assert result.verdict.get("label") in {"TRUE", "FALSE", "MISLEADING", "PARTIALLY_TRUE", "UNVERIFIABLE"}
    assert 0.0 <= result.verdict.get("confidence", 0.0) <= 1.0
    assert result.total_rounds >= 1
