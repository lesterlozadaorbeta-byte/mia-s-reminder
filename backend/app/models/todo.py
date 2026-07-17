"""Todo and TodoCategory models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TodoCategory(Base):
    """Category for organizing todos."""

    __tablename__ = "todo_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#4285F4")
    icon = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    todos = relationship("Todo", back_populates="category")

    def __repr__(self):
        return f"<TodoCategory {self.name}>"


class Todo(Base):
    """Todo item with subtask support."""

    __tablename__ = "todos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("todo_categories.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("todos.id", ondelete="CASCADE"), nullable=True)

    # Task details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Priority: 1 (highest) to 4 (lowest)
    priority = Column(Integer, default=3)

    # Status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Scheduling
    due_date = Column(DateTime(timezone=True), nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)  # AI-estimated
    actual_duration_minutes = Column(Integer, nullable=True)

    # Progress
    progress_percent = Column(Float, default=0.0)

    # AI metadata
    created_by_ai = Column(Boolean, default=False)
    ai_breakdown = Column(JSON, default=list)  # AI-suggested subtasks
    sort_order = Column(Integer, default=0)

    # Tags
    tags = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="todos")
    category = relationship("TodoCategory", back_populates="todos")
    subtasks = relationship("Todo", backref="parent", remote_side=[id], cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Todo {self.title}>"
