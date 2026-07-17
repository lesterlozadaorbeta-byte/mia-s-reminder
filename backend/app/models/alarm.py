"""Alarm model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Alarm(Base):
    """Alarm with multiple schedule support."""

    __tablename__ = "alarms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Alarm details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    alarm_type = Column(String(50), default="general")  # general, wake_up, medication, study, custom

    # Schedule
    alarm_time = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String(100), default="UTC")

    # Recurrence
    is_recurring = Column(Boolean, default=False)
    repeat_days = Column(JSON, default=list)  # [0,1,2,3,4] = Mon-Fri
    recurrence_rule = Column(String(500), nullable=True)

    # Sound and vibration
    sound_file = Column(String(255), default="default")
    volume = Column(Integer, default=80)  # 0-100
    vibration_enabled = Column(Boolean, default=True)
    vibration_pattern = Column(String(50), default="default")  # default, gentle, strong

    # Snooze settings
    snooze_enabled = Column(Boolean, default=True)
    snooze_duration_minutes = Column(Integer, default=5)
    max_snooze_count = Column(Integer, default=3)
    current_snooze_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    next_trigger_at = Column(DateTime(timezone=True), nullable=True)

    # AI metadata
    created_by_ai = Column(Boolean, default=False)

    # Labels/Tags
    label = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="alarms")

    def __repr__(self):
        return f"<Alarm {self.title} at {self.alarm_time}>"
