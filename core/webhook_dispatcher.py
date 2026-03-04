"""Webhook delivery logic — fire HTTP POST to registered webhook URLs after analysis completes."""

import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from core.config import settings
from core.logging import get_logger
from db.models import Webhook, WebhookDelivery
from db.repository import (
    create_webhook_delivery,
    get_active_webhooks_by_user,
    update_webhook_delivery,
)
from db.session import AsyncSessionLocal

logger = get_logger(__name__)

_BACKOFF_SECONDS = [5, 30, 300]


def _sign_payload(secret: str, body: bytes) -> str:
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


async def _deliver_once(
    webhook: Webhook,
    delivery_id: uuid.UUID,
    payload: dict,
    attempt: int,
) -> bool:
    """Attempt one HTTP POST delivery. Returns True on success."""
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "X-Tribunal-Event": payload.get("event", "")}
    if webhook.secret:
        headers["X-Tribunal-Signature"] = _sign_payload(webhook.secret, body)

    try:
        async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT_S) as client:
            resp = await client.post(webhook.url, content=body, headers=headers)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning(
            "webhook.delivery_failed",
            webhook_id=str(webhook.id),
            delivery_id=str(delivery_id),
            attempt=attempt,
            error=str(exc),
        )
        return False


async def _deliver_with_retry(
    webhook: Webhook,
    delivery_id: uuid.UUID,
    payload: dict,
) -> None:
    for attempt in range(1, settings.WEBHOOK_MAX_RETRIES + 1):
        if attempt > 1:
            delay = _BACKOFF_SECONDS[min(attempt - 2, len(_BACKOFF_SECONDS) - 1)]
            await asyncio.sleep(delay)

        success = await _deliver_once(webhook, delivery_id, payload, attempt)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
            delivery = result.scalar_one_or_none()
            if delivery:
                await update_webhook_delivery(
                    db, delivery,
                    status="delivered" if success else ("failed" if attempt >= settings.WEBHOOK_MAX_RETRIES else "pending"),
                    attempts=attempt,
                )

        if success:
            logger.info("webhook.delivered", webhook_id=str(webhook.id), delivery_id=str(delivery_id))
            return

    logger.error("webhook.exhausted", webhook_id=str(webhook.id), delivery_id=str(delivery_id))


async def dispatch_webhooks(
    user_id: uuid.UUID,
    event: str,
    analysis_id: uuid.UUID,
    payload: dict,
) -> None:
    """Find all active webhooks for user and fire deliveries (non-blocking via asyncio.create_task)."""
    try:
        async with AsyncSessionLocal() as db:
            webhooks = await get_active_webhooks_by_user(db, user_id)
            for wh in webhooks:
                full_payload = {
                    "event": event,
                    "analysis_id": str(analysis_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **payload,
                }
                delivery = await create_webhook_delivery(
                    db,
                    webhook_id=wh.id,
                    event=event,
                    payload=full_payload,
                    analysis_id=analysis_id,
                )
                # Fire-and-forget retry loop
                asyncio.create_task(
                    _deliver_with_retry(wh, delivery.id, full_payload),
                    name=f"webhook-{wh.id}-{delivery.id}",
                )
    except Exception as exc:
        logger.error("webhook.dispatch_error", user_id=str(user_id), error=str(exc))
