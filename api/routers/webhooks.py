import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth_middleware import get_active_user
from api.models.schemas import WebhookCreate, WebhookDeliveryResponse, WebhookResponse
from core.webhook_dispatcher import dispatch_webhooks
from db.models import User
from db.repository import (
    create_webhook,
    delete_webhook,
    get_webhook,
    get_webhook_deliveries,
    get_webhooks_by_user,
)
from db.session import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_endpoint(
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    wh = await create_webhook(db, user_id=current_user.id, url=body.url, secret=body.secret)
    return WebhookResponse(id=wh.id, url=wh.url, is_active=wh.is_active, created_at=wh.created_at)


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    webhooks = await get_webhooks_by_user(db, current_user.id)
    return [WebhookResponse(id=wh.id, url=wh.url, is_active=wh.is_active, created_at=wh.created_at) for wh in webhooks]


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_endpoint(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    wh = await get_webhook(db, webhook_id)
    if not wh or wh.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    await delete_webhook(db, wh)


@router.post("/{webhook_id}/test", status_code=status.HTTP_202_ACCEPTED)
async def test_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    wh = await get_webhook(db, webhook_id)
    if not wh or wh.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    # Fire a test delivery (analysis_id is a zero UUID for test events)
    test_analysis_id = uuid.UUID(int=0)
    await dispatch_webhooks(
        user_id=current_user.id,
        event="test",
        analysis_id=test_analysis_id,
        payload={"message": "This is a test delivery from FakeNews Tribunal"},
    )
    return {"detail": "Test delivery queued"}


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_deliveries(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    wh = await get_webhook(db, webhook_id)
    if not wh or wh.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    deliveries = await get_webhook_deliveries(db, webhook_id)
    return [
        WebhookDeliveryResponse(
            id=d.id,
            analysis_id=d.analysis_id,
            event=d.event,
            status=d.status,
            attempts=d.attempts,
            last_attempt_at=d.last_attempt_at,
            created_at=d.created_at,
        )
        for d in deliveries
    ]
