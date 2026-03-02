import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.orchestrator import DebateOrchestrator, DebateResult


MOCK_RESEARCHER_REPORT = "## Research Report — Round 1\n### Supporting Evidence\nSome evidence."
MOCK_CHALLENGE = "## Challenge Report — Round 1\n### Challenged Evidence\nSome challenge."
MOCK_VERDICT = {
    "continue": False,
    "verdict": {
        "label": "FALSE",
        "confidence": 0.85,
        "summary": "The claim is false.",
        "reasoning": "Based on evidence...",
        "supporting_source_urls": [],
        "contradicting_source_urls": [],
    },
}


@pytest.mark.asyncio
async def test_orchestrator_single_round():
    with (
        patch("agents.orchestrator.ResearcherAgent") as MockResearcher,
        patch("agents.orchestrator.DevilAdvocateAgent") as MockAdvocate,
        patch("agents.orchestrator.JudgeAgent") as MockJudge,
    ):
        researcher_instance = AsyncMock()
        researcher_instance.run = AsyncMock(return_value=(MOCK_RESEARCHER_REPORT, []))
        MockResearcher.return_value = researcher_instance

        advocate_instance = AsyncMock()
        advocate_instance.run = AsyncMock(return_value=(MOCK_CHALLENGE, []))
        MockAdvocate.return_value = advocate_instance

        judge_instance = AsyncMock()
        judge_instance.evaluate = AsyncMock(return_value=MOCK_VERDICT)
        MockJudge.return_value = judge_instance

        orchestrator = DebateOrchestrator(provider="anthropic", max_rounds=5)
        result = await orchestrator.run(claim="The Earth is flat.", language="en")

        assert isinstance(result, DebateResult)
        assert result.total_rounds == 1
        assert result.verdict["label"] == "FALSE"
        assert len(result.rounds) == 1


@pytest.mark.asyncio
async def test_orchestrator_continues_to_second_round():
    continue_response = {"continue": True, "reason": "Need more evidence."}
    final_response = {
        "continue": False,
        "verdict": {
            "label": "MISLEADING",
            "confidence": 0.7,
            "summary": "Misleading.",
            "reasoning": "...",
            "supporting_source_urls": [],
            "contradicting_source_urls": [],
        },
    }

    with (
        patch("agents.orchestrator.ResearcherAgent") as MockResearcher,
        patch("agents.orchestrator.DevilAdvocateAgent") as MockAdvocate,
        patch("agents.orchestrator.JudgeAgent") as MockJudge,
    ):
        researcher_instance = AsyncMock()
        researcher_instance.run = AsyncMock(return_value=(MOCK_RESEARCHER_REPORT, []))
        MockResearcher.return_value = researcher_instance

        advocate_instance = AsyncMock()
        advocate_instance.run = AsyncMock(return_value=(MOCK_CHALLENGE, []))
        MockAdvocate.return_value = advocate_instance

        judge_instance = AsyncMock()
        judge_instance.evaluate = AsyncMock(side_effect=[continue_response, final_response])
        MockJudge.return_value = judge_instance

        orchestrator = DebateOrchestrator(provider="anthropic", max_rounds=5)
        result = await orchestrator.run(claim="Vaccines cause autism.", language="en")

        assert result.total_rounds == 2
        assert result.verdict["label"] == "MISLEADING"
        assert len(result.rounds) == 2
