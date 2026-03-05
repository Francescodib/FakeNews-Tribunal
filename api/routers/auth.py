from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth_middleware import (
    create_access_token,
    create_refresh_token_value,
    get_current_user,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
)
from api.models.schemas import LoginRequest, LogoutRequest, MeResponse, MeUpdateRequest, RefreshRequest, RegisterRequest, TokenResponse
from db.models import User
from db.repository import (
    create_refresh_token,
    create_user,
    delete_refresh_token,
    get_refresh_token_by_hash,
    get_user_by_email,
    update_user,
)
from db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await create_user(db, body.email, hash_password(body.password))
    access = create_access_token(user.id)
    refresh_value = create_refresh_token_value()
    await create_refresh_token(db, user.id, hash_token(refresh_value), refresh_token_expiry())
    return TokenResponse(access_token=access, refresh_token=refresh_value)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_pw):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access = create_access_token(user.id)
    refresh_value = create_refresh_token_value()
    await create_refresh_token(db, user.id, hash_token(refresh_value), refresh_token_expiry())
    return TokenResponse(access_token=access, refresh_token=refresh_value)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_record = await get_refresh_token_by_hash(db, hash_token(body.refresh_token))
    if not token_record:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    user_id = token_record.user_id
    await delete_refresh_token(db, token_record)
    access = create_access_token(user_id)
    new_refresh_value = create_refresh_token_value()
    await create_refresh_token(db, user_id, hash_token(new_refresh_value), refresh_token_expiry())
    return TokenResponse(access_token=access, refresh_token=new_refresh_value)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, db: AsyncSession = Depends(get_db)):
    token_record = await get_refresh_token_by_hash(db, hash_token(body.refresh_token))
    if token_record:
        await delete_refresh_token(db, token_record)


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        is_disabled=user.is_disabled,
    )


@router.patch("/me", response_model=MeResponse)
async def update_me(
    body: MeUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.email is not None and body.email != user.email:
        existing = await get_user_by_email(db, body.email)
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already in use")

    new_hashed_pw = None
    if body.new_password is not None:
        if not body.current_password:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="current_password required to set a new password")
        if not verify_password(body.current_password, user.hashed_pw):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
        new_hashed_pw = hash_password(body.new_password)

    updated = await update_user(db, user, email=body.email, hashed_pw=new_hashed_pw)
    return MeResponse(
        id=updated.id,
        email=updated.email,
        is_admin=updated.is_admin,
        is_disabled=updated.is_disabled,
    )
