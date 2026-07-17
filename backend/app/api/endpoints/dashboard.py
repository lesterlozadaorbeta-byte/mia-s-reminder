"""Dashboard API endpoint."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.calendar import CalendarEvent
from app.models.todo import Todo
from app.models.reminder import Reminder
from app.models.alarm import Alarm

router = APIRouter()


@router.get("")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get dashboard data - today's schedule, upcoming items, stats."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)

    # Today's events
    events_result = await db.execute(
        select(CalendarEvent)
        .where(
            CalendarEvent.user_id == current_user.id,
            CalendarEvent.start_time >= today_start,
            CalendarEvent.start_time < today_end,
        )
        .order_by(CalendarEvent.start_time)
    )
    today_events = events_result.scalars().all()

    # Upcoming reminders (next 7 days)
    reminders_result = await db.execute(
        select(Reminder)
        .where(
            Reminder.user_id == current_user.id,
            Reminder.status == "active",
            Reminder.remind_at >= now,
            Reminder.remind_at < week_end,
        )
        .order_by(Reminder.remind_at)
        .limit(10)
    )
    upcoming_reminders = reminders_result.scalars().all()

    # Active alarms
    alarms_result = await db.execute(
        select(Alarm)
        .where(
            Alarm.user_id == current_user.id,
            Alarm.is_active == True,
        )
        .order_by(Alarm.next_trigger_at)
        .limit(5)
    )
    active_alarms = alarms_result.scalars().all()

    # Pending todos
    todos_result = await db.execute(
        select(Todo)
        .where(
            Todo.user_id == current_user.id,
            Todo.is_completed == False,
            Todo.parent_id == None,
        )
        .order_by(Todo.priority, Todo.due_date)
        .limit(10)
    )
    pending_todos = todos_result.scalars().all()

    # Productivity stats
    total_todos = await db.execute(
        select(func.count(Todo.id)).where(Todo.user_id == current_user.id)
    )
    completed_todos = await db.execute(
        select(func.count(Todo.id)).where(
            Todo.user_id == current_user.id,
            Todo.is_completed == True,
        )
    )

    total_count = total_todos.scalar() or 0
    completed_count = completed_todos.scalar() or 0
    completion_rate = (completed_count / total_count * 100) if total_count > 0 else 0

    # Tasks completed this week
    week_start = today_start - timedelta(days=today_start.weekday())
    weekly_completed = await db.execute(
        select(func.count(Todo.id)).where(
            Todo.user_id == current_user.id,
            Todo.is_completed == True,
            Todo.completed_at >= week_start,
        )
    )

    return {
        "today_events": [
            {
                "id": str(e.id),
                "title": e.title,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "color": e.color,
                "location": e.location,
            }
            for e in today_events
        ],
        "upcoming_reminders": [
            {
                "id": str(r.id),
                "title": r.title,
                "remind_at": r.remind_at.isoformat(),
                "priority": r.priority,
                "is_persistent": r.is_persistent,
            }
            for r in upcoming_reminders
        ],
        "active_alarms": [
            {
                "id": str(a.id),
                "title": a.title,
                "next_trigger_at": a.next_trigger_at.isoformat() if a.next_trigger_at else None,
                "alarm_type": a.alarm_type,
            }
            for a in active_alarms
        ],
        "pending_todos": [
            {
                "id": str(t.id),
                "title": t.title,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "progress_percent": t.progress_percent,
            }
            for t in pending_todos
        ],
        "stats": {
            "total_tasks": total_count,
            "completed_tasks": completed_count,
            "completion_rate": round(completion_rate, 1),
            "weekly_completed": weekly_completed.scalar() or 0,
            "active_reminders": len(upcoming_reminders),
            "today_event_count": len(today_events),
        },
    }
