import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth_middleware import get_admin_user, hash_password
from api.models.schemas import (
    AdminStatsResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from db.models import User
from db.repository import delete_user, get_global_stats, get_user_by_email, get_user_by_id, list_users, update_user
from db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListResponse)
async def list_all_users(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    users, total = await list_users(db, page, page_size)
    return AdminUserListResponse(
        items=[AdminUserResponse(
            id=u.id, email=u.email, is_admin=u.is_admin, is_disabled=u.is_disabled, created_at=u.created_at
        ) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user_detail(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return AdminUserResponse(
        id=user.id, email=user.email, is_admin=user.is_admin, is_disabled=user.is_disabled, created_at=user.created_at
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user_endpoint(
    user_id: uuid.UUID,
    body: AdminUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.email and body.email != user.email:
        conflict = await get_user_by_email(db, body.email)
        if conflict:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already in use")
    if body.is_admin is False and user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot remove your own admin role")
    if body.is_disabled is True and user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot disable your own account")
    updated = await update_user(
        db,
        user,
        email=body.email,
        hashed_pw=hash_password(body.password) if body.password else None,
        is_admin=body.is_admin,
        is_disabled=body.is_disabled,
    )
    return AdminUserResponse(
        id=updated.id, email=updated.email, is_admin=updated.is_admin,
        is_disabled=updated.is_disabled, created_at=updated.created_at,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    await delete_user(db, user)


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    stats = await get_global_stats(db)
    return AdminStatsResponse(**stats)
