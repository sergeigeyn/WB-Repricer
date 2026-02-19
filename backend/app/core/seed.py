"""Seed initial admin user on startup."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


async def seed_admin_user() -> None:
    """Create admin user if ADMIN_PASSWORD is set in .env."""
    if not settings.ADMIN_PASSWORD:
        logger.info("ADMIN_PASSWORD not set, skipping seed")
        return

    async with async_session() as session:
        session: AsyncSession
        result = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info("Admin user already exists: %s", settings.ADMIN_EMAIL)
            return

        admin = User(
            email=settings.ADMIN_EMAIL,
            name=settings.ADMIN_NAME,
            role="admin",
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        logger.info("Created admin user: %s", settings.ADMIN_EMAIL)
