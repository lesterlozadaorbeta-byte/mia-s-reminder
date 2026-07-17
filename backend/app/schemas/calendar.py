"""Calendar and Event schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class CalendarCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    color: str = Field(default="#4285F4", pattern=r"^#[0-9A-Fa-f]{6}$")


class CalendarUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_visible: Optional[bool] = None


class CalendarResponse(BaseModel):
    id: UUID
    name: str
    color: str
    is_default: bool
    is_visible: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    calendar_id: Optional[UUID] = None  # Uses default calendar if None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    timezone: str = "UTC"
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[datetime] = None


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    timezone: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[datetime] = None
    status: Optional[str] = None


class EventResponse(BaseModel):
    id: UUID
    calendar_id: UUID
    title: str
    description: Optional[str]
    location: Optional[str]
    color: Optional[str]
    start_time: datetime
    end_time: datetime
    all_day: bool
    timezone: str
    is_recurring: bool
    recurrence_rule: Optional[str]
    status: str
    created_by_ai: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventsQueryParams(BaseModel):
    start_date: datetime
    end_date: datetime
    calendar_ids: Optional[List[UUID]] = None


class ConflictResponse(BaseModel):
    has_conflict: bool
    conflicting_events: List[EventResponse] = []
    suggestion: Optional[str] = None
