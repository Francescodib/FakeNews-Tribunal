import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Analysis, RefreshToken, User


# --- User ---

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, hashed_pw: str) -> User:
    user = User(email=email, hashed_pw=hashed_pw)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# --- Refresh Token ---

async def create_refresh_token(
    db: AsyncSession, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_refresh_token_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token: RefreshToken) -> None:
    await db.delete(token)
    await db.commit()


# --- Analysis ---

async def create_analysis(
    db: AsyncSession,
    user_id: uuid.UUID,
    claim: str,
    llm_provider: str,
    llm_model: str,
    language: str,
) -> Analysis:
    analysis = Analysis(
        user_id=user_id,
        claim=claim,
        status="pending",
        llm_provider=llm_provider,
        llm_model=llm_model,
        language=language,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def get_analysis(db: AsyncSession, analysis_id: uuid.UUID) -> Analysis | None:
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    return result.scalar_one_or_none()


async def get_analyses_by_user(
    db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 20
) -> tuple[list[Analysis], int]:
    offset = (page - 1) * page_size
    q = select(Analysis).where(Analysis.user_id == user_id).order_by(Analysis.created_at.desc())
    total_result = await db.execute(
        select(Analysis).where(Analysis.user_id == user_id)
    )
    total = len(total_result.all())
    result = await db.execute(q.limit(page_size).offset(offset))
    return list(result.scalars().all()), total


async def update_analysis_status(db: AsyncSession, analysis: Analysis, status: str) -> None:
    analysis.status = status
    await db.commit()


async def update_analysis_complete(
    db: AsyncSession,
    analysis: Analysis,
    debate_json: list,
    verdict_json: dict,
    processing_ms: int,
) -> None:
    analysis.status = "completed"
    analysis.debate_json = debate_json
    analysis.verdict_json = verdict_json
    analysis.processing_ms = processing_ms
    analysis.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(analysis)


async def update_analysis_error(db: AsyncSession, analysis: Analysis, error: str) -> None:
    analysis.status = "failed"
    analysis.error = error
    analysis.completed_at = datetime.now(timezone.utc)
    await db.commit()


async def delete_analysis(db: AsyncSession, analysis: Analysis) -> None:
    await db.delete(analysis)
    await db.commit()


# --- Admin ---

async def list_users(
    db: AsyncSession, page: int = 1, page_size: int = 50
) -> tuple[list[User], int]:
    offset = (page - 1) * page_size
    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar_one()
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(page_size).offset(offset)
    )
    return list(result.scalars().all()), total


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.commit()


async def get_global_stats(db: AsyncSession) -> dict:
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_analyses = (await db.execute(select(func.count()).select_from(Analysis))).scalar_one()

    status_rows = await db.execute(
        select(Analysis.status, func.count()).group_by(Analysis.status)
    )
    by_status = {row[0]: row[1] for row in status_rows}

    provider_rows = await db.execute(
        select(Analysis.llm_provider, func.count()).group_by(Analysis.llm_provider)
    )
    by_provider = {row[0]: row[1] for row in provider_rows}

    return {
        "total_users": total_users,
        "total_analyses": total_analyses,
        "analyses_by_status": by_status,
        "analyses_by_provider": by_provider,
    }
