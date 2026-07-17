"""Reminder API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.reminder import Reminder
from app.schemas.reminder import (
    ReminderCreate,
    ReminderResponse,
    ReminderSnooze,
    ReminderUpdate,
)

router = APIRouter()


@router.get("", response_model=List[ReminderResponse])
async def list_reminders(
    status_filter: Optional[str] = Query(None, alias="status"),
    upcoming: bool = Query(False, description="Only show upcoming reminders"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List reminders with optional filters."""
    query = select(Reminder).where(Reminder.user_id == current_user.id)

    if status_filter:
        query = query.where(Reminder.status == status_filter)

    if upcoming:
        query = query.where(
            Reminder.remind_at >= datetime.now(timezone.utc),
            Reminder.status == "active",
        )

    query = query.order_by(Reminder.remind_at)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    data: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new reminder."""
    reminder = Reminder(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        notes=data.notes,
        priority=data.priority,
        remind_at=data.remind_at,
        timezone=data.timezone,
        is_recurring=data.is_recurring,
        recurrence_type=data.recurrence_type,
        recurrence_rule=data.recurrence_rule,
        recurrence_end=data.recurrence_end,
        is_persistent=data.is_persistent,
        persistence_interval_minutes=data.persistence_interval_minutes,
        max_persistence_duration_minutes=data.max_persistence_duration_minutes,
        notify_push=data.notify_push,
        notify_telegram=data.notify_telegram,
        notify_email=data.notify_email,
        attachments=data.attachments,
    )
    db.add(reminder)
    await db.flush()
    return reminder


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific reminder."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.patch("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: UUID,
    data: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a reminder."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)

    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a reminder."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    await db.delete(reminder)


@router.post("/{reminder_id}/done", response_model=ReminderResponse)
async def mark_done(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a reminder as done."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.status = "completed"
    reminder.completed_at = datetime.now(timezone.utc)
    return reminder


@router.post("/{reminder_id}/snooze", response_model=ReminderResponse)
async def snooze_reminder(
    reminder_id: UUID,
    data: ReminderSnooze,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Snooze a reminder for specified minutes."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.status = "snoozed"
    reminder.snoozed_until = datetime.now(timezone.utc) + timedelta(minutes=data.snooze_minutes)
    reminder.snooze_count += 1
    return reminder
