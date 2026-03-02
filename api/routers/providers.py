import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from api.middleware.auth_middleware import get_current_user
from core.config import settings
from db.models import User

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/ollama/models")
async def list_ollama_models(
    _: User = Depends(get_current_user),
):
    """Return models currently available in the local Ollama instance."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            r.raise_for_status()
            models = [f"ollama/{m['name']}" for m in r.json().get("models", [])]
            return {"models": models}
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is not reachable",
        )
