"""Todo schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class TodoCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#4285F4", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None


class TodoCategoryResponse(BaseModel):
    id: UUID
    name: str
    color: str
    icon: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    notes: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=4)
    category_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    tags: List[str] = []


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=4)
    category_id: Optional[UUID] = None
    is_completed: Optional[bool] = None
    due_date: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    progress_percent: Optional[float] = Field(None, ge=0, le=100)
    sort_order: Optional[int] = None
    tags: Optional[List[str]] = None


class TodoResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    notes: Optional[str]
    priority: int
    category_id: Optional[UUID]
    parent_id: Optional[UUID]
    is_completed: bool
    completed_at: Optional[datetime]
    due_date: Optional[datetime]
    estimated_duration_minutes: Optional[int]
    actual_duration_minutes: Optional[int]
    progress_percent: float
    created_by_ai: bool
    tags: List[str]
    sort_order: int
    subtasks: List["TodoResponse"] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TodoListResponse(BaseModel):
    todos: List[TodoResponse]
    total: int
    completed: int
    pending: int


# Resolve forward reference
TodoResponse.model_rebuild()
