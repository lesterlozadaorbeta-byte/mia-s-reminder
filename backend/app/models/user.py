"""User model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Null for OAuth users
    full_name = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)

    # Auth providers
    firebase_uid = Column(String(255), unique=True, nullable=True, index=True)
    auth_provider = Column(String(50), default="email")  # email, google, apple, facebook

    # Telegram
    telegram_chat_id = Column(String(100), nullable=True, unique=True)
    telegram_username = Column(String(100), nullable=True)

    # Settings
    timezone = Column(String(100), default="UTC")
    language = Column(String(10), default="en")
    theme = Column(String(20), default="system")  # light, dark, system
    notification_preferences = Column(JSON, default=dict)

    # Reminder settings
    reminder_frequency_minutes = Column(
        JSON, default=lambda: {"default": 5, "max_duration_minutes": 60}
    )

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships (lazy loaded to avoid circular import issues)
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    calendars = relationship("Calendar", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    todos = relationship("Todo", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    alarms = relationship("Alarm", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"
