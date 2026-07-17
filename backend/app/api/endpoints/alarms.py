"""Alarm API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.alarm import Alarm
from app.schemas.alarm import AlarmCreate, AlarmResponse, AlarmUpdate

router = APIRouter()


@router.get("", response_model=List[AlarmResponse])
async def list_alarms(
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user alarms."""
    query = select(Alarm).where(Alarm.user_id == current_user.id)

    if active_only:
        query = query.where(Alarm.is_active == True)

    query = query.order_by(Alarm.alarm_time)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=AlarmResponse, status_code=status.HTTP_201_CREATED)
async def create_alarm(
    data: AlarmCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new alarm."""
    alarm = Alarm(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        alarm_type=data.alarm_type,
        alarm_time=data.alarm_time,
        timezone=data.timezone,
        is_recurring=data.is_recurring,
        repeat_days=data.repeat_days,
        recurrence_rule=data.recurrence_rule,
        sound_file=data.sound_file,
        volume=data.volume,
        vibration_enabled=data.vibration_enabled,
        vibration_pattern=data.vibration_pattern,
        snooze_enabled=data.snooze_enabled,
        snooze_duration_minutes=data.snooze_duration_minutes,
        max_snooze_count=data.max_snooze_count,
        next_trigger_at=data.alarm_time,
        label=data.label,
    )
    db.add(alarm)
    await db.flush()
    return alarm


@router.get("/{alarm_id}", response_model=AlarmResponse)
async def get_alarm(
    alarm_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific alarm."""
    result = await db.execute(
        select(Alarm).where(Alarm.id == alarm_id, Alarm.user_id == current_user.id)
    )
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return alarm


@router.patch("/{alarm_id}", response_model=AlarmResponse)
async def update_alarm(
    alarm_id: UUID,
    data: AlarmUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an alarm."""
    result = await db.execute(
        select(Alarm).where(Alarm.id == alarm_id, Alarm.user_id == current_user.id)
    )
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(alarm, field, value)

    return alarm


@router.delete("/{alarm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alarm(
    alarm_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an alarm."""
    result = await db.execute(
        select(Alarm).where(Alarm.id == alarm_id, Alarm.user_id == current_user.id)
    )
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")

    await db.delete(alarm)


@router.post("/{alarm_id}/toggle", response_model=AlarmResponse)
async def toggle_alarm(
    alarm_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle alarm active/inactive."""
    result = await db.execute(
        select(Alarm).where(Alarm.id == alarm_id, Alarm.user_id == current_user.id)
    )
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")

    alarm.is_active = not alarm.is_active
    return alarm


@router.post("/{alarm_id}/snooze", response_model=AlarmResponse)
async def snooze_alarm(
    alarm_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Snooze an alarm."""
    result = await db.execute(
        select(Alarm).where(Alarm.id == alarm_id, Alarm.user_id == current_user.id)
    )
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")

    if alarm.current_snooze_count >= alarm.max_snooze_count:
        raise HTTPException(status_code=400, detail="Maximum snooze count reached")

    alarm.current_snooze_count += 1
    alarm.next_trigger_at = datetime.now(timezone.utc) + timedelta(
        minutes=alarm.snooze_duration_minutes
    )
    return alarm
