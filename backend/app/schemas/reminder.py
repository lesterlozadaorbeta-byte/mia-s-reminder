"""Reminder schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    notes: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=4)
    remind_at: datetime
    timezone: str = "UTC"

    # Recurrence
    is_recurring: bool = False
    recurrence_type: Optional[str] = None  # daily, weekly, monthly, yearly, custom
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[datetime] = None

    # Persistent settings
    is_persistent: bool = True
    persistence_interval_minutes: int = Field(default=5, ge=1, le=60)
    max_persistence_duration_minutes: int = Field(default=60, ge=5, le=480)

    # Notification channels
    notify_push: bool = True
    notify_telegram: bool = True
    notify_email: bool = False

    # Attachments
    attachments: List[str] = []


class ReminderUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=4)
    remind_at: Optional[datetime] = None
    timezone: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_type: Optional[str] = None
    recurrence_rule: Optional[str] = None
    recurrence_end: Optional[datetime] = None
    is_persistent: Optional[bool] = None
    persistence_interval_minutes: Optional[int] = Field(None, ge=1, le=60)
    max_persistence_duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    notify_push: Optional[bool] = None
    notify_telegram: Optional[bool] = None
    notify_email: Optional[bool] = None
    status: Optional[str] = None


class ReminderResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    notes: Optional[str]
    priority: int
    remind_at: datetime
    timezone: str
    is_recurring: bool
    recurrence_type: Optional[str]
    recurrence_rule: Optional[str]
    is_persistent: bool
    persistence_interval_minutes: int
    max_persistence_duration_minutes: int
    status: str
    snoozed_until: Optional[datetime]
    snooze_count: int
    notify_push: bool
    notify_telegram: bool
    notify_email: bool
    attachments: List[str]
    created_by_ai: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReminderSnooze(BaseModel):
    snooze_minutes: int = Field(..., ge=1, le=120)


class ReminderAction(BaseModel):
    """Action taken on a reminder (from Telegram or Push notification)."""
    action: str  # done, snooze_5, snooze_10, snooze_30
    reminder_id: UUID
