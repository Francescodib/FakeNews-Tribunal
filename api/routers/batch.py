import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth_middleware import get_active_user
from api.models.schemas import BatchListResponse, BatchRequest, BatchResponse, BatchStatusResponse
from api.rate_limit import limiter
from api.routers.analysis import _run_debate
from core.config import settings
from core.logging import get_logger
from db.models import User
from db.repository import (
    create_analysis,
    create_batch,
    get_analyses_by_batch,
    get_batch,
    get_batches_by_user,
)
from db.session import AsyncSessionLocal, get_db
from llm.provider import resolve_model
from core.events import create_queue

router = APIRouter(prefix="/batch", tags=["batch"])
logger = get_logger(__name__)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/hour")
async def submit_batch(
    request: Request,
    body: BatchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    if len(body.claims) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Too many claims: max {settings.MAX_BATCH_SIZE} per batch",
        )
    if len(body.claims) == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one claim required")

    provider = body.llm_provider
    model = resolve_model(provider, body.llm_model)
    max_rounds = min(body.max_rounds, settings.MAX_DEBATE_ROUNDS)

    batch = await create_batch(db, user_id=current_user.id, total=len(body.claims))
    analysis_ids: list[uuid.UUID] = []

    for claim in body.claims:
        analysis = await create_analysis(
            db,
            user_id=current_user.id,
            claim=claim,
            llm_provider=provider,
            llm_model=model,
            language=body.language,
            batch_id=batch.id,
        )
        create_queue(analysis.id)
        background_tasks.add_task(
            _run_debate,
            analysis_id=analysis.id,
            claim=claim,
            language=body.language,
            provider=provider,
            model_override=body.llm_model,
            max_rounds=max_rounds,
            batch_id=batch.id,
        )
        analysis_ids.append(analysis.id)

    return BatchResponse(
        batch_id=batch.id,
        analysis_ids=analysis_ids,
        status_url=f"/api/v1/batch/{batch.id}",
        total=len(body.claims),
    )


@router.get("", response_model=BatchListResponse)
async def list_batches(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    batches, total = await get_batches_by_user(db, current_user.id, page, page_size)
    items = []
    for b in batches:
        analyses = await get_analyses_by_batch(db, b.id)
        items.append(_batch_to_schema(b, [a.id for a in analyses]))
    return BatchListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    batch = await get_batch(db, batch_id)
    if not batch or batch.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Batch not found")
    analyses = await get_analyses_by_batch(db, batch_id)
    return _batch_to_schema(batch, [a.id for a in analyses])


def _batch_to_schema(b, analysis_ids: list[uuid.UUID]) -> BatchStatusResponse:
    return BatchStatusResponse(
        id=b.id,
        status=b.status,
        total=b.total,
        completed=b.completed,
        failed=b.failed,
        created_at=b.created_at,
        completed_at=b.completed_at,
        analysis_ids=analysis_ids,
    )
