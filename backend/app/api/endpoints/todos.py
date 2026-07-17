"""Todo API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.todo import Todo, TodoCategory
from app.schemas.todo import (
    TodoCategoryCreate,
    TodoCategoryResponse,
    TodoCreate,
    TodoListResponse,
    TodoResponse,
    TodoUpdate,
)

router = APIRouter()


# --- Categories ---

@router.get("/categories", response_model=List[TodoCategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List todo categories."""
    result = await db.execute(
        select(TodoCategory).where(TodoCategory.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/categories", response_model=TodoCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: TodoCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a todo category."""
    category = TodoCategory(
        user_id=current_user.id,
        name=data.name,
        color=data.color,
        icon=data.icon,
    )
    db.add(category)
    await db.flush()
    return category


# --- Todos ---

@router.get("", response_model=TodoListResponse)
async def list_todos(
    category_id: Optional[UUID] = Query(None),
    is_completed: Optional[bool] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=4),
    sort_by: str = Query("sort_order", regex="^(sort_order|priority|due_date|created_at)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List todos with filters and sorting."""
    query = select(Todo).where(
        Todo.user_id == current_user.id,
        Todo.parent_id == None,  # Only top-level todos
    )

    if category_id:
        query = query.where(Todo.category_id == category_id)
    if is_completed is not None:
        query = query.where(Todo.is_completed == is_completed)
    if priority:
        query = query.where(Todo.priority == priority)

    # Sorting
    sort_map = {
        "sort_order": Todo.sort_order,
        "priority": Todo.priority,
        "due_date": Todo.due_date,
        "created_at": Todo.created_at.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, Todo.sort_order))

    result = await db.execute(query.options(selectinload(Todo.subtasks)))
    todos = result.scalars().all()

    # Count stats
    total = len(todos)
    completed = sum(1 for t in todos if t.is_completed)

    return TodoListResponse(
        todos=todos,
        total=total,
        completed=completed,
        pending=total - completed,
    )


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(
    data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new todo."""
    todo = Todo(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        notes=data.notes,
        priority=data.priority,
        category_id=data.category_id,
        parent_id=data.parent_id,
        due_date=data.due_date,
        estimated_duration_minutes=data.estimated_duration_minutes,
        tags=data.tags,
    )
    db.add(todo)
    await db.flush()
    return todo


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific todo with subtasks."""
    result = await db.execute(
        select(Todo)
        .where(Todo.id == todo_id, Todo.user_id == current_user.id)
        .options(selectinload(Todo.subtasks))
    )
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: UUID,
    data: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a todo."""
    result = await db.execute(
        select(Todo).where(Todo.id == todo_id, Todo.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle completion
    if "is_completed" in update_data:
        if update_data["is_completed"] and not todo.is_completed:
            update_data["completed_at"] = datetime.now(timezone.utc)
            update_data["progress_percent"] = 100.0
        elif not update_data["is_completed"]:
            update_data["completed_at"] = None

    for field, value in update_data.items():
        setattr(todo, field, value)

    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a todo and its subtasks."""
    result = await db.execute(
        select(Todo).where(Todo.id == todo_id, Todo.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    await db.delete(todo)


@router.post("/{todo_id}/complete", response_model=TodoResponse)
async def complete_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a todo as completed."""
    result = await db.execute(
        select(Todo).where(Todo.id == todo_id, Todo.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    todo.is_completed = True
    todo.completed_at = datetime.now(timezone.utc)
    todo.progress_percent = 100.0

    return todo
