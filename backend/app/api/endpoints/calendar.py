"""Calendar API endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.calendar import Calendar, CalendarEvent
from app.schemas.calendar import (
    CalendarCreate,
    CalendarResponse,
    CalendarUpdate,
    ConflictResponse,
    EventCreate,
    EventResponse,
    EventUpdate,
)

router = APIRouter()


# --- Calendar CRUD ---

@router.get("/calendars", response_model=List[CalendarResponse])
async def list_calendars(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all user calendars."""
    result = await db.execute(
        select(Calendar).where(Calendar.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/calendars", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar(
    data: CalendarCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new calendar."""
    calendar = Calendar(
        user_id=current_user.id,
        name=data.name,
        color=data.color,
    )
    db.add(calendar)
    await db.flush()
    return calendar


@router.patch("/calendars/{calendar_id}", response_model=CalendarResponse)
async def update_calendar(
    calendar_id: UUID,
    data: CalendarUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a calendar."""
    result = await db.execute(
        select(Calendar).where(
            Calendar.id == calendar_id,
            Calendar.user_id == current_user.id,
        )
    )
    calendar = result.scalar_one_or_none()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(calendar, field, value)

    return calendar


@router.delete("/calendars/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar(
    calendar_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a calendar."""
    result = await db.execute(
        select(Calendar).where(
            Calendar.id == calendar_id,
            Calendar.user_id == current_user.id,
            Calendar.is_default == False,
        )
    )
    calendar = result.scalar_one_or_none()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found or cannot delete default")

    await db.delete(calendar)


# --- Events CRUD ---

@router.get("/events", response_model=List[EventResponse])
async def list_events(
    start_date: datetime = Query(..., description="Start of date range"),
    end_date: datetime = Query(..., description="End of date range"),
    calendar_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List events in a date range."""
    query = select(CalendarEvent).where(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.start_time >= start_date,
        CalendarEvent.end_time <= end_date,
    )

    if calendar_id:
        query = query.where(CalendarEvent.calendar_id == calendar_id)

    query = query.order_by(CalendarEvent.start_time)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new calendar event."""
    # Validate calendar
    calendar_id = data.calendar_id
    if not calendar_id:
        result = await db.execute(
            select(Calendar).where(
                Calendar.user_id == current_user.id,
                Calendar.is_default == True,
            )
        )
        calendar = result.scalar_one_or_none()
        if not calendar:
            raise HTTPException(status_code=404, detail="No default calendar found")
        calendar_id = calendar.id

    # Validate times
    if data.end_time <= data.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    event = CalendarEvent(
        calendar_id=calendar_id,
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        location=data.location,
        color=data.color,
        start_time=data.start_time,
        end_time=data.end_time,
        all_day=data.all_day,
        timezone=data.timezone,
        is_recurring=data.is_recurring,
        recurrence_rule=data.recurrence_rule,
        recurrence_end=data.recurrence_end,
    )
    db.add(event)
    await db.flush()
    return event


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific event."""
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an event."""
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    return event


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an event."""
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await db.delete(event)


@router.post("/events/check-conflicts", response_model=ConflictResponse)
async def check_conflicts(
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    exclude_event_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check for scheduling conflicts."""
    query = select(CalendarEvent).where(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.start_time < end_time,
        CalendarEvent.end_time > start_time,
        CalendarEvent.status != "cancelled",
    )

    if exclude_event_id:
        query = query.where(CalendarEvent.id != exclude_event_id)

    result = await db.execute(query)
    conflicts = result.scalars().all()

    return ConflictResponse(
        has_conflict=len(conflicts) > 0,
        conflicting_events=conflicts,
        suggestion="Consider rescheduling to avoid overlap." if conflicts else None,
    )
