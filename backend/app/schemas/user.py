"""User schemas."""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserCreateOAuth(BaseModel):
    firebase_token: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    notification_preferences: Optional[Dict[str, Any]] = None
    reminder_frequency_minutes: Optional[Dict[str, Any]] = None
    telegram_chat_id: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    avatar_url: Optional[str]
    auth_provider: str
    timezone: str
    language: str
    theme: str
    telegram_chat_id: Optional[str]
    notification_preferences: Dict[str, Any]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    timezone: str = "UTC"
    language: str = "en"
    theme: str = "system"
    notification_preferences: Dict[str, Any] = {}
    reminder_frequency_minutes: Dict[str, Any] = {"default": 5, "max_duration_minutes": 60}
