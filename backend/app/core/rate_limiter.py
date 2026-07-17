"""Per-user rate limiting and usage quotas to prevent abuse."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()


# --- Usage Tier Definitions ---

USAGE_TIERS = {
    "free": {
        "ai_messages_per_day": 50,
        "reminders_total": 100,
        "events_total": 200,
        "todos_total": 500,
        "alarms_total": 20,
        "api_requests_per_minute": 30,
    },
    "pro": {
        "ai_messages_per_day": 500,
        "reminders_total": 5000,
        "events_total": 10000,
        "todos_total": 50000,
        "alarms_total": 200,
        "api_requests_per_minute": 120,
    },
    "admin": {
        "ai_messages_per_day": 99999,
        "reminders_total": 99999,
        "events_total": 99999,
        "todos_total": 99999,
        "alarms_total": 99999,
        "api_requests_per_minute": 999,
    },
}


def get_user_tier(user) -> str:
    """Get user's subscription tier."""
    # Check notification_preferences for tier info
    prefs = user.notification_preferences or {}
    return prefs.get("tier", "free")


def get_user_limits(user) -> dict:
    """Get usage limits for a user based on their tier."""
    tier = get_user_tier(user)
    return USAGE_TIERS.get(tier, USAGE_TIERS["free"])


async def check_ai_message_limit(user) -> bool:
    """Check if user has exceeded their daily AI message limit."""
    tier_limits = get_user_limits(user)
    max_messages = tier_limits["ai_messages_per_day"]

    # Use Redis to track daily usage
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"ai_usage:{user.id}:{today}"

    rc = get_redis_client()
    current_count = await rc.get(key)
    if current_count and int(current_count) >= max_messages:
        return False  # Limit exceeded

    return True


async def increment_ai_usage(user):
    """Increment AI message counter for the day."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"ai_usage:{user.id}:{today}"

    rc = get_redis_client()
    pipe = rc.pipeline()
    pipe.incr(key)
    pipe.expire(key, 86400)  # Expire after 24 hours
    await pipe.execute()


async def get_ai_usage_today(user) -> int:
    """Get current AI message usage for today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"ai_usage:{user.id}:{today}"
    rc = get_redis_client()
    count = await rc.get(key)
    return int(count) if count else 0


async def check_resource_limit(user, resource_type: str, db: AsyncSession) -> bool:
    """Check if user has exceeded their total resource limit."""
    from app.models.reminder import Reminder
    from app.models.calendar import CalendarEvent
    from app.models.todo import Todo
    from app.models.alarm import Alarm

    tier_limits = get_user_limits(user)

    model_map = {
        "reminders_total": Reminder,
        "events_total": CalendarEvent,
        "todos_total": Todo,
        "alarms_total": Alarm,
    }

    model = model_map.get(resource_type)
    if not model:
        return True

    max_count = tier_limits.get(resource_type, 9999)

    result = await db.execute(
        select(func.count(model.id)).where(model.user_id == user.id)
    )
    current_count = result.scalar() or 0

    return current_count < max_count


async def check_rate_limit_per_user(user) -> bool:
    """Check per-user API rate limit (requests per minute)."""
    tier_limits = get_user_limits(user)
    max_rpm = tier_limits["api_requests_per_minute"]

    # Sliding window in Redis
    now = datetime.now(timezone.utc)
    minute_key = f"rpm:{user.id}:{now.strftime('%Y-%m-%d-%H-%M')}"

    rc = get_redis_client()
    current = await rc.get(minute_key)
    if current and int(current) >= max_rpm:
        return False

    pipe = rc.pipeline()
    pipe.incr(minute_key)
    pipe.expire(minute_key, 120)  # Keep for 2 minutes then auto-expire
    await pipe.execute()

    return True


# --- FastAPI Dependencies ---

async def enforce_rate_limit(
    request: Request,
    current_user=Depends(get_current_user),
):
    """Dependency that enforces per-user rate limiting."""
    allowed = await check_rate_limit_per_user(current_user)
    if not allowed:
        tier = get_user_tier(current_user)
        limits = get_user_limits(current_user)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "tier": tier,
                "limit": f"{limits['api_requests_per_minute']} requests/minute",
                "upgrade_message": "Upgrade to Pro for higher limits" if tier == "free" else None,
            },
        )
    return current_user


async def enforce_ai_limit(
    current_user=Depends(get_current_user),
):
    """Dependency that enforces AI message daily limit."""
    allowed = await check_ai_message_limit(current_user)
    if not allowed:
        tier = get_user_tier(current_user)
        limits = get_user_limits(current_user)
        usage = await get_ai_usage_today(current_user)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Daily AI message limit reached",
                "tier": tier,
                "used": usage,
                "limit": limits["ai_messages_per_day"],
                "resets": "midnight UTC",
                "upgrade_message": "Upgrade to Pro for 500 messages/day" if tier == "free" else None,
            },
        )
    return current_user


async def enforce_reminder_limit(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dependency that enforces reminder creation limit."""
    allowed = await check_resource_limit(current_user, "reminders_total", db)
    if not allowed:
        tier = get_user_tier(current_user)
        limits = get_user_limits(current_user)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Reminder limit reached",
                "tier": tier,
                "limit": limits["reminders_total"],
                "upgrade_message": "Upgrade to Pro for more reminders" if tier == "free" else None,
            },
        )
    return current_user


async def enforce_event_limit(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dependency that enforces event creation limit."""
    allowed = await check_resource_limit(current_user, "events_total", db)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Event limit reached for your plan"},
        )
    return current_user


async def enforce_todo_limit(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dependency that enforces todo creation limit."""
    allowed = await check_resource_limit(current_user, "todos_total", db)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Task limit reached for your plan"},
        )
    return current_user


# --- Usage Stats Endpoint Helper ---

async def get_usage_stats(user, db: AsyncSession) -> dict:
    """Get comprehensive usage stats for a user."""
    from app.models.reminder import Reminder
    from app.models.calendar import CalendarEvent
    from app.models.todo import Todo
    from app.models.alarm import Alarm

    tier = get_user_tier(user)
    limits = get_user_limits(user)

    # Count resources
    reminders_count = (await db.execute(
        select(func.count(Reminder.id)).where(Reminder.user_id == user.id)
    )).scalar() or 0

    events_count = (await db.execute(
        select(func.count(CalendarEvent.id)).where(CalendarEvent.user_id == user.id)
    )).scalar() or 0

    todos_count = (await db.execute(
        select(func.count(Todo.id)).where(Todo.user_id == user.id)
    )).scalar() or 0

    alarms_count = (await db.execute(
        select(func.count(Alarm.id)).where(Alarm.user_id == user.id)
    )).scalar() or 0

    ai_usage_today = await get_ai_usage_today(user)

    return {
        "tier": tier,
        "usage": {
            "ai_messages_today": ai_usage_today,
            "reminders": reminders_count,
            "events": events_count,
            "todos": todos_count,
            "alarms": alarms_count,
        },
        "limits": limits,
        "percentages": {
            "ai_messages": round(ai_usage_today / limits["ai_messages_per_day"] * 100, 1),
            "reminders": round(reminders_count / limits["reminders_total"] * 100, 1),
            "events": round(events_count / limits["events_total"] * 100, 1),
            "todos": round(todos_count / limits["todos_total"] * 100, 1),
            "alarms": round(alarms_count / limits["alarms_total"] * 100, 1),
        },
    }
