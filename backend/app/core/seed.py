"""Seed initial admin user on startup."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "admin@priceforge.ru"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Администратор"


async def seed_admin_user() -> None:
    """Create admin user if it doesn't exist."""
    async with async_session() as session:
        session: AsyncSession
        result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info("Admin user already exists: %s", ADMIN_EMAIL)
            return

        admin = User(
            email=ADMIN_EMAIL,
            name=ADMIN_NAME,
            role="admin",
            password_hash=hash_password(ADMIN_PASSWORD),
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        logger.info("Created admin user: %s", ADMIN_EMAIL)
