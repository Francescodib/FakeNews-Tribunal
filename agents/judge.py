import json
import re

from agents.base_agent import BaseAgent
from core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are the Judge in a fact-checking tribunal. You observe a structured debate between a Researcher and a Devil's Advocate.

After each round, decide:
A) Whether sufficient evidence has been gathered to reach a reliable verdict.
B) If not, specify what additional research is needed.

When ready to judge, produce a final verdict using ONLY this JSON format:
{
  "continue": false,
  "verdict": {
    "label": "TRUE|FALSE|MISLEADING|UNVERIFIABLE|PARTIALLY_TRUE",
    "confidence": 0.0-1.0,
    "summary": "2-3 sentence summary for a general audience",
    "reasoning": "Full detailed reasoning in Markdown",
    "supporting_source_urls": ["url1", ...],
    "contradicting_source_urls": ["url2", ...]
  }
}

If more rounds are needed:
{
  "continue": true,
  "reason": "Specific explanation of what is missing and what the Researcher should focus on next"
}

Judgment criteria:
- Source credibility and recency
- Consistency across independent sources
- Quality of Devil's Advocate challenges
- Whether core factual claims are verifiable
- Confidence should reflect epistemic uncertainty, not just source count\
"""


class JudgeAgent(BaseAgent):
    def __init__(self, provider: str, model_override: str | None = None) -> None:
        super().__init__(provider, model_override)

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    async def evaluate(
        self,
        claim: str,
        debate_transcript: str,
        current_round: int,
        max_rounds: int,
    ) -> dict:
        logger.info("judge.evaluate", round=current_round, max_rounds=max_rounds)

        force_verdict = current_round >= max_rounds
        context = (
            f"**Claim:** {claim}\n\n"
            f"**Debate transcript (all rounds so far):**\n{debate_transcript}\n\n"
            f"**Current round:** {current_round} / {max_rounds}"
        )
        if force_verdict:
            context += "\n\n**IMPORTANT: This is the final round. You MUST emit a verdict now.**"

        raw = await self._call([{"role": "user", "content": context}], temperature=0.1)
        result = _parse_judge_response(raw)

        if force_verdict and result.get("continue"):
            logger.warning("judge.forced_verdict", round=current_round)
            result = {
                "continue": False,
                "verdict": {
                    "label": "UNVERIFIABLE",
                    "confidence": 0.3,
                    "summary": "Max debate rounds reached without sufficient evidence for a definitive verdict.",
                    "reasoning": raw,
                    "supporting_source_urls": [],
                    "contradicting_source_urls": [],
                },
            }

        logger.info("judge.done", continue_debate=result.get("continue"), round=current_round)
        return result


def _parse_judge_response(raw: str) -> dict:
    # Try to extract JSON block
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Retry hint: ask for clean JSON on next call (caller handles this)
    logger.warning("judge.parse_error", raw_preview=raw[:200])
    # Fallback: treat as continue with the raw text as reason
    return {"continue": True, "reason": raw[:500]}
