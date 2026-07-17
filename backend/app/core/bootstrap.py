"""Bootstrap utilities - first-run setup."""

import logging
from sqlalchemy import select, func

from app.core.database import get_session_factory
from app.models.user import User

logger = logging.getLogger(__name__)


async def make_first_user_admin():
    """Make the first registered user an admin."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar() or 0

        if user_count == 0:
            logger.info("No users yet - first user to register will become admin")
            return

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
