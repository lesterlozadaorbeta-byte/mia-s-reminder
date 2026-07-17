"""Bootstrap utilities - first-run setup."""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


async def make_first_user_admin():
    """Make the first registered user an admin.
    
    Call this after init_db to ensure there's an admin
    if users already exist.
    """
    async with AsyncSessionLocal() as db:
        # Check if any admin exists
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar() or 0

        if user_count == 0:
            logger.info("No users yet - first user to register will become admin")
            return

        # Check if any admin exists
        result = await db.execute(select(User).limit(1))
        first_user = result.scalar_one_or_none()

        if first_user:
            prefs = first_user.notification_preferences or {}
            if prefs.get("tier") != "admin":
                prefs["tier"] = "admin"
                prefs["role"] = "admin"
                first_user.notification_preferences = prefs
                await db.commit()
                logger.info(f"Made {first_user.email} an admin (first user)")


async def promote_user_to_admin(email: str):
    """Promote a specific user to admin by email."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            prefs = user.notification_preferences or {}
            prefs["tier"] = "admin"
            prefs["role"] = "admin"
            user.notification_preferences = prefs
            await db.commit()
            logger.info(f"Promoted {email} to admin")
            return True
        return False
