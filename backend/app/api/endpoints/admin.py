"""Admin panel API endpoints - user management, stats, monitoring."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import get_usage_stats, USAGE_TIERS
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.calendar import CalendarEvent
from app.models.todo import Todo
from app.models.reminder import Reminder
from app.models.alarm import Alarm

router = APIRouter()


def _require_admin(user: User):
    """Check if user is an admin."""
    prefs = user.notification_preferences or {}
    if prefs.get("tier") != "admin" and prefs.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("/stats")
async def get_platform_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get overall platform statistics."""
    _require_admin(current_user)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # User stats
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_today = (await db.execute(
        select(func.count(User.id)).where(User.last_login_at >= today_start)
    )).scalar() or 0
    new_this_week = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )).scalar() or 0
    new_this_month = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_ago)
    )).scalar() or 0

    # Content stats
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    total_reminders = (await db.execute(select(func.count(Reminder.id)))).scalar() or 0
    total_events = (await db.execute(select(func.count(CalendarEvent.id)))).scalar() or 0
    total_todos = (await db.execute(select(func.count(Todo.id)))).scalar() or 0
    total_alarms = (await db.execute(select(func.count(Alarm.id)))).scalar() or 0

    # Messages today
    messages_today = (await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= today_start)
    )).scalar() or 0

    # Conversations this week
    conversations_this_week = (await db.execute(
        select(func.count(Conversation.id)).where(Conversation.created_at >= week_ago)
    )).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "active_today": active_today,
            "new_this_week": new_this_week,
            "new_this_month": new_this_month,
        },
        "content": {
            "total_messages": total_messages,
            "messages_today": messages_today,
            "conversations_this_week": conversations_this_week,
            "total_reminders": total_reminders,
            "total_events": total_events,
            "total_todos": total_todos,
            "total_alarms": total_alarms,
        },
        "system": {
            "uptime": "healthy",
            "timestamp": now.isoformat(),
        },
    }


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|last_login_at|email|full_name)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users with search and pagination."""
    _require_admin(current_user)

    query = select(User)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_filter)) | (User.full_name.ilike(search_filter))
        )

    # Sorting
    sort_column = getattr(User, sort_by)
    query = query.order_by(desc(sort_column))

    # Pagination
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit))
    users = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "auth_provider": u.auth_provider,
                "tier": (u.notification_preferences or {}).get("tier", "free"),
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "telegram_linked": u.telegram_chat_id is not None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info about a specific user."""
    _require_admin(current_user)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get usage stats for this user
    usage = await get_usage_stats(user, db)

    # Count conversations
    conv_count = (await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
    )).scalar() or 0

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "auth_provider": user.auth_provider,
        "timezone": user.timezone,
        "language": user.language,
        "theme": user.theme,
        "telegram_chat_id": user.telegram_chat_id,
        "telegram_username": user.telegram_username,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "conversations_count": conv_count,
        "usage": usage,
    }


@router.patch("/users/{user_id}/tier")
async def update_user_tier(
    user_id: UUID,
    tier: str = Query(..., regex="^(free|pro|admin)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's subscription tier."""
    _require_admin(current_user)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefs = user.notification_preferences or {}
    prefs["tier"] = tier
    user.notification_preferences = prefs

    return {"message": f"User tier updated to {tier}", "user_id": str(user_id)}


@router.patch("/users/{user_id}/status")
async def toggle_user_status(
    user_id: UUID,
    is_active: bool = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a user account."""
    _require_admin(current_user)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-disable
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    user.is_active = is_active

    return {
        "message": f"User {'enabled' if is_active else 'disabled'}",
        "user_id": str(user_id),
        "is_active": is_active,
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a user and all their data (GDPR compliance)."""
    _require_admin(current_user)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)  # Cascade deletes all related data

    return {"message": "User and all associated data deleted", "user_id": str(user_id)}


@router.get("/activity")
async def get_recent_activity(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent activity across the platform."""
    _require_admin(current_user)

    # Recent messages
    messages_result = await db.execute(
        select(Message, Conversation.user_id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Message.role == "user")
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    messages = messages_result.all()

    # Recent signups
    signups_result = await db.execute(
        select(User).order_by(desc(User.created_at)).limit(10)
    )
    recent_signups = signups_result.scalars().all()

    return {
        "recent_messages": [
            {
                "content": msg.Message.content[:100],
                "role": msg.Message.role,
                "user_id": str(msg.user_id),
                "intent": msg.Message.intent_detected,
                "created_at": msg.Message.created_at.isoformat() if msg.Message.created_at else None,
            }
            for msg in messages[:20]
        ],
        "recent_signups": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "auth_provider": u.auth_provider,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in recent_signups
        ],
    }
