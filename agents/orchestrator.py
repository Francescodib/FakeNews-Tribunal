import time
from datetime import datetime, timezone
from uuid import UUID

from agents.devil_advocate import DevilAdvocateAgent
from agents.judge import JudgeAgent
from agents.researcher import ResearcherAgent
from core.logging import get_logger

logger = get_logger(__name__)


class DebateOrchestrator:
    def __init__(
        self,
        provider: str,
        model_override: str | None = None,
        max_rounds: int = 5,
    ) -> None:
        self.provider = provider
        self.model_override = model_override
        self.max_rounds = max_rounds
        self._researcher = ResearcherAgent(provider, model_override)
        self._advocate = DevilAdvocateAgent(provider, model_override)
        self._judge = JudgeAgent(provider, model_override)

    async def run(
        self,
        claim: str,
        language: str = "it",
        analysis_id: UUID | None = None,
        on_round_complete: "DebateRoundCallback | None" = None,
    ) -> "DebateResult":
        log = logger.bind(analysis_id=str(analysis_id) if analysis_id else None, claim_length=len(claim))
        log.info("orchestrator.start", provider=self.provider, max_rounds=self.max_rounds)

        start_time = time.monotonic()
        rounds: list[dict] = []
        debate_transcript = ""
        judge_guidance: str | None = None

        for round_number in range(1, self.max_rounds + 1):
            log.info("orchestrator.round_start", round=round_number)

            # Researcher
            researcher_report, researcher_sources = await self._researcher.run(
                claim=claim,
                round_number=round_number,
                language=language,
                previous_challenge=rounds[-1]["advocate_challenge"] if rounds else None,
                judge_guidance=judge_guidance,
            )

            # Devil's Advocate
            advocate_challenge, advocate_sources = await self._advocate.run(
                claim=claim,
                round_number=round_number,
                researcher_report=researcher_report,
                language=language,
            )

            round_data = {
                "round_number": round_number,
                "researcher_report": researcher_report,
                "researcher_sources": researcher_sources,
                "advocate_challenge": advocate_challenge,
                "advocate_counter_sources": advocate_sources,
                "judge_continuation_reason": None,
            }

            # Update transcript
            debate_transcript += (
                f"\n\n--- Round {round_number} ---\n"
                f"### Researcher\n{researcher_report}\n\n"
                f"### Devil's Advocate\n{advocate_challenge}"
            )

            # Judge evaluation
            judge_result = await self._judge.evaluate(
                claim=claim,
                debate_transcript=debate_transcript,
                current_round=round_number,
                max_rounds=self.max_rounds,
            )

            if judge_result.get("continue"):
                judge_guidance = judge_result.get("reason")
                round_data["judge_continuation_reason"] = judge_guidance
                rounds.append(round_data)
                if on_round_complete:
                    await on_round_complete(round_data)
                log.info("orchestrator.continue", round=round_number, reason=judge_guidance)
                continue

            # Final verdict
            rounds.append(round_data)
            if on_round_complete:
                await on_round_complete(round_data)

            verdict_raw = judge_result.get("verdict", {})
            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            log.info(
                "orchestrator.done",
                rounds=round_number,
                label=verdict_raw.get("label"),
                confidence=verdict_raw.get("confidence"),
                elapsed_ms=elapsed_ms,
            )

            return DebateResult(
                verdict=verdict_raw,
                rounds=rounds,
                total_rounds=round_number,
                processing_time_ms=elapsed_ms,
            )

        # Should not reach here (Judge forces verdict at max_rounds)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return DebateResult(
            verdict={
                "label": "UNVERIFIABLE",
                "confidence": 0.2,
                "summary": "Max rounds reached without a verdict.",
                "reasoning": "The debate exhausted the maximum number of rounds.",
                "supporting_source_urls": [],
                "contradicting_source_urls": [],
            },
            rounds=rounds,
            total_rounds=self.max_rounds,
            processing_time_ms=elapsed_ms,
        )


class DebateResult:
    def __init__(
        self,
        verdict: dict,
        rounds: list[dict],
        total_rounds: int,
        processing_time_ms: int,
    ) -> None:
        self.verdict = verdict
        self.rounds = rounds
        self.total_rounds = total_rounds
        self.processing_time_ms = processing_time_ms


DebateRoundCallback = "callable[[dict], None]"
