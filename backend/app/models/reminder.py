"""Reminder model with persistent reminder support."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Reminder(Base):
    """Reminder with persistent notification support."""

    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Reminder details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Priority: 1 (urgent) to 4 (low)
    priority = Column(Integer, default=3)

    # Schedule
    remind_at = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String(100), default="UTC")

    # Recurrence
    is_recurring = Column(Boolean, default=False)
    recurrence_type = Column(String(20), nullable=True)  # daily, weekly, monthly, yearly, custom
    recurrence_rule = Column(String(500), nullable=True)  # RRULE format
    recurrence_end = Column(DateTime(timezone=True), nullable=True)

    # Persistent reminder settings
    is_persistent = Column(Boolean, default=True)
    persistence_interval_minutes = Column(Integer, default=5)  # Re-remind every N minutes
    max_persistence_duration_minutes = Column(Integer, default=60)  # Stop after N minutes
    persistence_started_at = Column(DateTime(timezone=True), nullable=True)
    snooze_count = Column(Integer, default=0)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(20), default="active")  # active, snoozed, completed, expired, cancelled
    snoozed_until = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Notification channels
    notify_push = Column(Boolean, default=True)
    notify_telegram = Column(Boolean, default=True)
    notify_email = Column(Boolean, default=False)

    # Attachments and metadata
    attachments = Column(JSON, default=list)  # List of attachment URLs
    metadata = Column(JSON, default=dict)

    # AI metadata
    created_by_ai = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="reminders")

    def __repr__(self):
        return f"<Reminder {self.title} at {self.remind_at}>"
