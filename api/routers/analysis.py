import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agents.orchestrator import DebateOrchestrator
from api.middleware.auth_middleware import get_current_user
from api.models.schemas import (
    AnalysisCreatedResponse,
    AnalysisListResponse,
    AnalysisRequest,
    AnalysisResult,
    DebateRound,
    Source,
    Verdict,
    VerdictLabel,
)
from core.config import settings
from core.events import create_queue, drop_queue, format_sse, get_queue, is_done_sentinel, push_done
from core.pdf import generate_verdict_pdf_async
from api.rate_limit import limiter
from core.logging import get_logger
from db.models import Analysis, User
from db.repository import (
    create_analysis,
    delete_analysis,
    get_analyses_by_user,
    get_analysis,
    update_analysis_complete,
    update_analysis_error,
    update_analysis_status,
)
from db.session import AsyncSessionLocal, get_db
from llm.provider import resolve_model

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = get_logger(__name__)

_STREAM_TIMEOUT_S = 600  # 10 minutes max stream duration


@router.post("", response_model=AnalysisCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/hour")
async def submit_analysis(
    request: Request,
    body: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = body.llm_provider
    model = resolve_model(provider, body.llm_model)
    analysis = await create_analysis(
        db,
        user_id=current_user.id,
        claim=body.claim,
        llm_provider=provider,
        llm_model=model,
        language=body.language,
    )
    # Create SSE queue BEFORE starting background task so no events are lost
    create_queue(analysis.id)
    background_tasks.add_task(
        _run_debate,
        analysis_id=analysis.id,
        claim=body.claim,
        language=body.language,
        provider=provider,
        model_override=body.llm_model,
        max_rounds=min(body.max_rounds, settings.MAX_DEBATE_ROUNDS),
    )
    return AnalysisCreatedResponse(
        analysis_id=analysis.id,
        status_url=f"/api/v1/analysis/{analysis.id}",
    )


@router.get("/{analysis_id}/stream")
async def stream_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream debate progress via Server-Sent Events.

    Events emitted:
    - round_start      {"round": N, "max_rounds": M}
    - agent_start      {"agent": "researcher"|"devil_advocate"|"judge", "round": N}
    - researcher_done  {"round": N, "report": str, "sources": [...]}
    - advocate_done    {"round": N, "challenge": str, "sources": [...]}
    - judge_continue   {"round": N, "reason": str}
    - verdict          {"verdict": {...}, "total_rounds": N, "processing_time_ms": N}
    - error            {"message": str}
    - done             {}
    """
    analysis = await get_analysis(db, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Already completed: replay from DB
    if analysis.status == "completed":
        return StreamingResponse(
            _replay_completed(analysis),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if analysis.status == "failed":
        async def _err():
            yield format_sse("error", {"message": analysis.error or "Analysis failed"})
            yield format_sse("done", {})
        return StreamingResponse(_err(), media_type="text/event-stream")

    q = get_queue(analysis_id)
    if q is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Stream not available for this analysis")

    return StreamingResponse(
        _stream_queue(q, analysis_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{analysis_id}", response_model=AnalysisResult)
async def get_analysis_result(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = await get_analysis(db, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return _to_schema(analysis)


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analyses, total = await get_analyses_by_user(db, current_user.id, page, page_size)
    return AnalysisListResponse(
        items=[_to_schema(a) for a in analyses],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{analysis_id}/export")
async def export_analysis_pdf(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export the completed analysis verdict as a PDF report."""
    analysis = await get_analysis(db, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.status != "completed" or not analysis.verdict_json:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Analysis not yet completed")

    pdf_bytes = await generate_verdict_pdf_async(
        claim=analysis.claim,
        verdict=analysis.verdict_json,
        rounds=analysis.debate_json or [],
        analysis_id=str(analysis.id),
        created_at=analysis.created_at.isoformat(),
        llm_provider=analysis.llm_provider,
        llm_model=analysis.llm_model,
    )
    filename = f"verdict_{analysis_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis_endpoint(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = await get_analysis(db, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    await delete_analysis(db, analysis)


# --- SSE generators ---

async def _stream_queue(q: asyncio.Queue, analysis_id: uuid.UUID):
    try:
        deadline = asyncio.get_event_loop().time() + _STREAM_TIMEOUT_S
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                yield format_sse("error", {"message": "Stream timeout"})
                break
            try:
                item = await asyncio.wait_for(q.get(), timeout=min(remaining, 30))
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"  # SSE comment keeps connection alive
                continue
            if is_done_sentinel(item):
                break
            yield format_sse(item["event"], item["data"])
    finally:
        yield format_sse("done", {})
        drop_queue(analysis_id)


async def _replay_completed(analysis: Analysis):
    for rnd in (analysis.debate_json or []):
        yield format_sse("round_start", {"round": rnd["round_number"]})
        yield format_sse("researcher_done", {
            "round": rnd["round_number"],
            "report": rnd["researcher_report"],
            "sources": rnd["researcher_sources"],
        })
        yield format_sse("advocate_done", {
            "round": rnd["round_number"],
            "challenge": rnd["advocate_challenge"],
            "sources": rnd["advocate_counter_sources"],
        })
        if rnd.get("judge_continuation_reason"):
            yield format_sse("judge_continue", {
                "round": rnd["round_number"],
                "reason": rnd["judge_continuation_reason"],
            })
    if analysis.verdict_json:
        yield format_sse("verdict", {
            "verdict": analysis.verdict_json,
            "total_rounds": len(analysis.debate_json or []),
            "processing_time_ms": analysis.processing_ms or 0,
        })
    yield format_sse("done", {})


# --- Background task ---

async def _run_debate(
    analysis_id: uuid.UUID,
    claim: str,
    language: str,
    provider: str,
    model_override: str | None,
    max_rounds: int,
) -> None:
    async with AsyncSessionLocal() as db:
        analysis = await get_analysis(db, analysis_id)
        if not analysis:
            return

        await update_analysis_status(db, analysis, "running")
        try:
            orchestrator = DebateOrchestrator(
                provider=provider,
                model_override=model_override,
                max_rounds=max_rounds,
            )
            result = await orchestrator.run(
                claim=claim,
                language=language,
                analysis_id=analysis_id,
            )
            await update_analysis_complete(
                db,
                analysis,
                debate_json=result.rounds,
                verdict_json=result.verdict,
                processing_ms=result.processing_time_ms,
            )
        except Exception as exc:
            logger.error("debate.failed", analysis_id=str(analysis_id), error=str(exc))
            await update_analysis_error(db, analysis, str(exc))
            from core.events import push
            await push(analysis_id, "error", {"message": str(exc)})
        finally:
            await push_done(analysis_id)


# --- Schema conversion ---

def _to_schema(a: Analysis) -> AnalysisResult:
    rounds = [_round_to_schema(r) for r in (a.debate_json or [])]
    verdict = _verdict_to_schema(a.verdict_json, rounds) if a.verdict_json else None
    return AnalysisResult(
        id=a.id,
        claim=a.claim,
        created_at=a.created_at,
        status=a.status,
        debate=rounds,
        verdict=verdict,
        llm_provider=a.llm_provider,
        llm_model=a.llm_model,
        error=a.error,
    )


def _round_to_schema(r: dict) -> DebateRound:
    return DebateRound(
        round_number=r["round_number"],
        researcher_report=r["researcher_report"],
        researcher_sources=[_src(s) for s in r.get("researcher_sources", [])],
        advocate_challenge=r["advocate_challenge"],
        advocate_counter_sources=[_src(s) for s in r.get("advocate_counter_sources", [])],
        judge_continuation_reason=r.get("judge_continuation_reason"),
    )


def _verdict_to_schema(v: dict, rounds: list[DebateRound]) -> Verdict:
    all_sources: list[Source] = []
    for rnd in rounds:
        all_sources.extend(rnd.researcher_sources)
        all_sources.extend(rnd.advocate_counter_sources)

    supporting_urls = set(v.get("supporting_source_urls", []))
    contradicting_urls = set(v.get("contradicting_source_urls", []))

    return Verdict(
        label=VerdictLabel(v.get("label", "UNVERIFIABLE")),
        confidence=float(v.get("confidence", 0.0)),
        summary=v.get("summary", ""),
        reasoning=v.get("reasoning", ""),
        supporting_sources=[s for s in all_sources if s.url in supporting_urls],
        contradicting_sources=[s for s in all_sources if s.url in contradicting_urls],
        total_rounds=v.get("total_rounds", len(rounds)),
        processing_time_ms=v.get("processing_time_ms", 0),
    )


def _src(s: dict) -> Source:
    return Source(
        url=s.get("url", ""),
        title=s.get("title", ""),
        snippet=s.get("snippet", ""),
        domain=s.get("domain", ""),
        retrieved_at=s.get("retrieved_at", ""),
        credibility_tier=s.get("credibility_tier"),
        credibility_score=s.get("credibility_score"),
        credibility_note=s.get("credibility_note"),
    )
