"""Calendar and Event models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Calendar(Base):
    """User calendar container."""

    __tablename__ = "calendars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False, default="My Calendar")
    color = Column(String(7), default="#4285F4")  # Hex color
    is_default = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="calendars")
    events = relationship("CalendarEvent", back_populates="calendar", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Calendar {self.name}>"


class CalendarEvent(Base):
    """Calendar event."""

    __tablename__ = "calendar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Event details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    color = Column(String(7), nullable=True)  # Override calendar color

    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    all_day = Column(Boolean, default=False)
    timezone = Column(String(100), default="UTC")

    # Recurrence (RFC 5545 RRULE format)
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(500), nullable=True)  # e.g., FREQ=WEEKLY;BYDAY=MO,WE,FR
    recurrence_end = Column(DateTime(timezone=True), nullable=True)
    parent_event_id = Column(UUID(as_uuid=True), nullable=True)  # For recurring event instances

    # Status
    status = Column(String(20), default="confirmed")  # confirmed, tentative, cancelled

    # AI metadata
    created_by_ai = Column(Boolean, default=False)
    ai_suggestions = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    calendar = relationship("Calendar", back_populates="events")

    def __repr__(self):
        return f"<CalendarEvent {self.title}>"
