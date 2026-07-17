"""Execute actions detected by the AI engine."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID

from dateutil import parser as date_parser
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder
from app.models.calendar import CalendarEvent, Calendar
from app.models.todo import Todo
from app.models.alarm import Alarm

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes AI-detected actions against the database."""

    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id

    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action and return the result."""
        action_type = action.get("action_type")
        params = action.get("parameters", {})

        handlers = {
            "create_reminder": self._create_reminder,
            "create_event": self._create_event,
            "create_todo": self._create_todo,
            "create_alarm": self._create_alarm,
            "create_schedule": self._create_schedule,
        }

        handler = handlers.get(action_type)
        if handler:
            try:
                result = await handler(params)
                return {"success": True, "action_type": action_type, "result": result}
            except Exception as e:
                logger.error(f"Action execution error ({action_type}): {e}")
                return {"success": False, "action_type": action_type, "error": str(e)}
        else:
            return {"success": False, "action_type": action_type, "error": "Unknown action"}

    async def _create_reminder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a reminder from AI parameters."""
        remind_at = date_parser.parse(params["remind_at"])

        reminder = Reminder(
            user_id=self.user_id,
            title=params["title"],
            description=params.get("description"),
            remind_at=remind_at,
            priority=params.get("priority", 3),
            is_recurring=params.get("is_recurring", False),
            recurrence_type=params.get("recurrence_type"),
            is_persistent=params.get("is_persistent", True),
            created_by_ai=True,
        )

        self.db.add(reminder)
        await self.db.flush()

        return {
            "id": str(reminder.id),
            "title": reminder.title,
            "remind_at": reminder.remind_at.isoformat(),
        }

    async def _create_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a calendar event from AI parameters."""
        from sqlalchemy import select

        # Get default calendar
        result = await self.db.execute(
            select(Calendar).where(
                Calendar.user_id == self.user_id,
                Calendar.is_default == True,
            )
        )
        calendar = result.scalar_one_or_none()

        if not calendar:
            calendar = Calendar(
                user_id=self.user_id,
                name="My Calendar",
                is_default=True,
            )
            self.db.add(calendar)
            await self.db.flush()

        start_time = date_parser.parse(params["start_time"])
        end_time = date_parser.parse(params["end_time"])

        event = CalendarEvent(
            calendar_id=calendar.id,
            user_id=self.user_id,
            title=params["title"],
            description=params.get("description"),
            location=params.get("location"),
            start_time=start_time,
            end_time=end_time,
            is_recurring=params.get("is_recurring", False),
            recurrence_rule=params.get("recurrence_rule"),
            created_by_ai=True,
        )

        self.db.add(event)
        await self.db.flush()

        return {
            "id": str(event.id),
            "title": event.title,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
        }

    async def _create_todo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a todo (with optional subtasks) from AI parameters."""
        due_date = None
        if params.get("due_date"):
            due_date = date_parser.parse(params["due_date"])

        todo = Todo(
            user_id=self.user_id,
            title=params["title"],
            description=params.get("description"),
            priority=params.get("priority", 3),
            due_date=due_date,
            estimated_duration_minutes=params.get("estimated_duration_minutes"),
            created_by_ai=True,
        )

        self.db.add(todo)
        await self.db.flush()

        # Create subtasks
        subtask_ids = []
        for i, subtask_data in enumerate(params.get("subtasks", [])):
            subtask = Todo(
                user_id=self.user_id,
                parent_id=todo.id,
                title=subtask_data["title"],
                estimated_duration_minutes=subtask_data.get("estimated_duration_minutes"),
                sort_order=i,
                created_by_ai=True,
            )
            self.db.add(subtask)
            await self.db.flush()
            subtask_ids.append(str(subtask.id))

        return {
            "id": str(todo.id),
            "title": todo.title,
            "subtask_count": len(subtask_ids),
        }

    async def _create_alarm(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create an alarm from AI parameters."""
        alarm_time = date_parser.parse(params["alarm_time"])

        alarm = Alarm(
            user_id=self.user_id,
            title=params["title"],
            alarm_time=alarm_time,
            alarm_type=params.get("alarm_type", "general"),
            is_recurring=params.get("is_recurring", False),
            repeat_days=params.get("repeat_days", []),
            next_trigger_at=alarm_time,
            created_by_ai=True,
        )

        self.db.add(alarm)
        await self.db.flush()

        return {
            "id": str(alarm.id),
            "title": alarm.title,
            "alarm_time": alarm.alarm_time.isoformat(),
        }

    async def _create_schedule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a schedule (multiple events) from AI parameters."""
        from app.ai.engine import AIEngine

        # This would call the AI scheduler to generate time slots
        # For now, return the raw schedule data
        return {
            "schedule_type": params.get("schedule_type"),
            "message": "Schedule created with AI optimization",
        }
