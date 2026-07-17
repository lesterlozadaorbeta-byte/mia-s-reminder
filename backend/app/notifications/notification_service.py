"""Notification service - FCM push, Telegram, email."""

import logging
from typing import Dict, Any, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    """Unified notification service for push, Telegram, and email."""

    async def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Send push notification via Firebase Cloud Messaging."""
        try:
            import firebase_admin
            from firebase_admin import messaging

            # Get user's FCM token from database
            fcm_token = await self._get_fcm_token(user_id)
            if not fcm_token:
                logger.warning(f"No FCM token for user {user_id}")
                return

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={k: str(v) for k, v in (data or {}).items()},
                token=fcm_token,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        priority="high",
                        channel_id="reminders",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                            content_available=True,
                        ),
                    ),
                ),
            )

            response = messaging.send(message)
            logger.info(f"Push notification sent: {response}")

        except Exception as e:
            logger.error(f"Push notification error: {e}")

    async def send_telegram(
        self,
        user_id: str,
        reminder_data: Dict[str, Any],
    ):
        """Send reminder notification via Telegram with action buttons."""
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot

            bot = Bot(token=settings.telegram_bot_token)

            # Get user's Telegram chat ID
            chat_id = await self._get_telegram_chat_id(user_id)
            if not chat_id:
                logger.warning(f"No Telegram chat ID for user {user_id}")
                return

            # Build message
            priority_emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢"}
            priority = reminder_data.get("priority", 3)

            message_text = (
                f"{priority_emoji.get(priority, '🔔')} **Reminder**\n\n"
                f"📌 {reminder_data['title']}\n"
            )

            if reminder_data.get("description"):
                message_text += f"📝 {reminder_data['description']}\n"

            message_text += f"⏰ {reminder_data['remind_at']}\n"

            if reminder_data.get("is_persistent"):
                message_text += "\n⚠️ _This reminder will keep notifying until you mark it done._"

            # Inline keyboard buttons
            reminder_id = reminder_data["reminder_id"]
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done", callback_data=f"done_{reminder_id}")],
                [
                    InlineKeyboardButton("⏳ 5 min", callback_data=f"snooze_5_{reminder_id}"),
                    InlineKeyboardButton("⏳ 10 min", callback_data=f"snooze_10_{reminder_id}"),
                ],
                [InlineKeyboardButton("⏳ 30 min", callback_data=f"snooze_30_{reminder_id}")],
            ])

            await bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

            logger.info(f"Telegram notification sent to {chat_id}")

        except Exception as e:
            logger.error(f"Telegram notification error: {e}")

    async def _get_fcm_token(self, user_id: str) -> Optional[str]:
        """Get user's FCM token from Redis cache or database."""
        from app.core.redis import redis_client

        # Check Redis cache first
        token = await redis_client.get(f"fcm_token:{user_id}")
        if token:
            return token

        # Fall back to database
        from app.core.database import get_session_factory
        from app.models.user import User
        from sqlalchemy import select

        async with get_session_factory()() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and user.notification_preferences:
                return user.notification_preferences.get("fcm_token")

        return None

    async def _get_telegram_chat_id(self, user_id: str) -> Optional[str]:
        """Get user's Telegram chat ID."""
        from app.core.database import get_session_factory
        from app.models.user import User
        from sqlalchemy import select

        async with get_session_factory()() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return user.telegram_chat_id if user else None
