"""Database models - import order matters for relationships."""

from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.calendar import CalendarEvent, Calendar
from app.models.todo import Todo, TodoCategory
from app.models.reminder import Reminder
from app.models.alarm import Alarm

# Force relationship resolution
from sqlalchemy.orm import configure_mappers
configure_mappers()

__all__ = [
    "User",
    "Conversation",
    "Message",
    "CalendarEvent",
    "Calendar",
    "Todo",
    "TodoCategory",
    "Reminder",
    "Alarm",
]
