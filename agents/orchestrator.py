import asyncio
import time
from typing import Awaitable, Callable
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
        existing_rounds: list[dict] | None = None,
        on_round_complete: Callable[[dict], Awaitable[None]] | None = None,
    ) -> "DebateResult":
        # Import here to avoid circular import at module level
        from core.events import push

        prior = existing_rounds or []
        log = logger.bind(analysis_id=str(analysis_id) if analysis_id else None, claim_length=len(claim))
        log.info("orchestrator.start", provider=self.provider, max_rounds=self.max_rounds, resuming_from=len(prior))

        async def emit(event: str, data: dict) -> None:
            if analysis_id:
                await push(analysis_id, event, data)

        start_time = time.monotonic()
        # Restore state from prior rounds
        rounds: list[dict] = list(prior)
        debate_transcript = _rebuild_transcript(prior)
        judge_guidance: str | None = (
            prior[-1].get("judge_continuation_reason") if prior else None
        )

        for round_number in range(len(prior) + 1, self.max_rounds + 1):
            log.info("orchestrator.round_start", round=round_number)
            await emit("round_start", {"round": round_number, "max_rounds": self.max_rounds})

            # Researcher
            await emit("agent_start", {"agent": "researcher", "round": round_number})
            researcher_report, researcher_sources = await self._researcher.run(
                claim=claim,
                round_number=round_number,
                language=language,
                previous_challenge=rounds[-1]["advocate_challenge"] if rounds else None,
                judge_guidance=judge_guidance,
            )
            await emit("researcher_done", {
                "round": round_number,
                "report": researcher_report,
                "sources": researcher_sources,
            })

            # Devil's Advocate
            await emit("agent_start", {"agent": "devil_advocate", "round": round_number})
            advocate_challenge, advocate_sources = await self._advocate.run(
                claim=claim,
                round_number=round_number,
                researcher_report=researcher_report,
                language=language,
            )
            await emit("advocate_done", {
                "round": round_number,
                "challenge": advocate_challenge,
                "sources": advocate_sources,
            })

            round_data = {
                "round_number": round_number,
                "researcher_report": researcher_report,
                "researcher_sources": researcher_sources,
                "advocate_challenge": advocate_challenge,
                "advocate_counter_sources": advocate_sources,
                "judge_continuation_reason": None,
            }

            def _fmt_sources(sources: list[dict]) -> str:
                if not sources:
                    return "  (none)"
                lines = []
                for s in sources:
                    tier = s.get("credibility_tier", "unknown")
                    lines.append(f"  - [{tier}] {s.get('url', '')} — {s.get('title', '')}")
                return "\n".join(lines)

            debate_transcript += (
                f"\n\n--- Round {round_number} ---\n"
                f"### Researcher\n{researcher_report}\n"
                f"**Researcher sources:**\n{_fmt_sources(researcher_sources)}\n\n"
                f"### Devil's Advocate\n{advocate_challenge}\n"
                f"**Advocate sources:**\n{_fmt_sources(advocate_sources)}"
            )

            # Judge evaluation
            await emit("agent_start", {"agent": "judge", "round": round_number})
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
                    asyncio.create_task(on_round_complete(round_data))
                await emit("judge_continue", {"round": round_number, "reason": judge_guidance})
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
            await emit("verdict", {
                "verdict": verdict_raw,
                "total_rounds": round_number,
                "processing_time_ms": elapsed_ms,
            })

            return DebateResult(
                verdict=verdict_raw,
                rounds=rounds,
                total_rounds=round_number,
                processing_time_ms=elapsed_ms,
            )

        # Forced fallback (should not reach here — Judge forces verdict at max_rounds)
        # Emit any round that was completed but not yet covered by the loop break
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        fallback_verdict = {
            "label": "UNVERIFIABLE",
            "confidence": 0.2,
            "summary": "Max rounds reached without a verdict.",
            "reasoning": "The debate exhausted the maximum number of rounds.",
            "supporting_source_urls": [],
            "contradicting_source_urls": [],
        }
        await emit("verdict", {
            "verdict": fallback_verdict,
            "total_rounds": self.max_rounds,
            "processing_time_ms": elapsed_ms,
        })
        return DebateResult(
            verdict=fallback_verdict,
            rounds=rounds,
            total_rounds=self.max_rounds,
            processing_time_ms=elapsed_ms,
        )


def _rebuild_transcript(rounds: list[dict]) -> str:
    """Reconstruct the debate transcript string from previously saved rounds."""
    transcript = ""
    for r in rounds:
        def _fmt(sources: list[dict]) -> str:
            if not sources:
                return "  (none)"
            return "\n".join(
                f"  - [{s.get('credibility_tier','unknown')}] {s.get('url','')} — {s.get('title','')}"
                for s in sources
            )
        transcript += (
            f"\n\n--- Round {r['round_number']} ---\n"
            f"### Researcher\n{r['researcher_report']}\n"
            f"**Researcher sources:**\n{_fmt(r.get('researcher_sources', []))}\n\n"
            f"### Devil's Advocate\n{r['advocate_challenge']}\n"
            f"**Advocate sources:**\n{_fmt(r.get('advocate_counter_sources', []))}"
        )
    return transcript


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
