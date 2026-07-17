"""Alarm schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class AlarmCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    alarm_type: str = "general"  # general, wake_up, medication, study, custom
    alarm_time: datetime
    timezone: str = "UTC"

    # Recurrence
    is_recurring: bool = False
    repeat_days: List[int] = []  # 0=Mon, 6=Sun
    recurrence_rule: Optional[str] = None

    # Sound
    sound_file: str = "default"
    volume: int = Field(default=80, ge=0, le=100)
    vibration_enabled: bool = True
    vibration_pattern: str = "default"

    # Snooze
    snooze_enabled: bool = True
    snooze_duration_minutes: int = Field(default=5, ge=1, le=30)
    max_snooze_count: int = Field(default=3, ge=1, le=10)

    # Label
    label: Optional[str] = None


class AlarmUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    alarm_type: Optional[str] = None
    alarm_time: Optional[datetime] = None
    timezone: Optional[str] = None
    is_recurring: Optional[bool] = None
    repeat_days: Optional[List[int]] = None
    sound_file: Optional[str] = None
    volume: Optional[int] = Field(None, ge=0, le=100)
    vibration_enabled: Optional[bool] = None
    snooze_enabled: Optional[bool] = None
    snooze_duration_minutes: Optional[int] = Field(None, ge=1, le=30)
    max_snooze_count: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None
    label: Optional[str] = None


class AlarmResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    alarm_type: str
    alarm_time: datetime
    timezone: str
    is_recurring: bool
    repeat_days: List[int]
    sound_file: str
    volume: int
    vibration_enabled: bool
    vibration_pattern: str
    snooze_enabled: bool
    snooze_duration_minutes: int
    max_snooze_count: int
    current_snooze_count: int
    is_active: bool
    next_trigger_at: Optional[datetime]
    last_triggered_at: Optional[datetime]
    created_by_ai: bool
    label: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlarmSnooze(BaseModel):
    alarm_id: UUID


class AlarmStop(BaseModel):
    alarm_id: UUID
