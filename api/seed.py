"""
Development seed: create test users on startup if they don't exist.
Only runs when settings.ENV == "development".

Users created:
  admin@tribunal.test / Admin1234!  (is_admin=True)
  user1@tribunal.test / User1234!
  user2@tribunal.test / User1234!
  user3@tribunal.test / User1234!
"""

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.repository import create_user, get_user_by_email

logger = get_logger(__name__)

_DEV_USERS: list[dict] = [
    {"email": "admin@tribunal.test", "password": "Admin1234!", "is_admin": True},
    {"email": "user1@tribunal.test", "password": "User1234!"},
    {"email": "user2@tribunal.test", "password": "User1234!"},
    {"email": "user3@tribunal.test", "password": "User1234!"},
]


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


async def seed_dev_users(db: AsyncSession) -> None:
    created = 0
    for spec in _DEV_USERS:
        existing = await get_user_by_email(db, spec["email"])
        if existing:
            continue
        user = await create_user(db, spec["email"], _hash(spec["password"]))
        if spec.get("is_admin"):
            user.is_admin = True
            await db.commit()
        created += 1
        logger.info("seed.user_created", email=spec["email"], is_admin=spec.get("is_admin", False))

    if created:
        logger.info("seed.done", created=created)
