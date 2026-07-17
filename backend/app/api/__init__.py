"""API router configuration."""

from fastapi import APIRouter

from app.api.endpoints import auth, chat, calendar, todos, reminders, alarms, dashboard, usage, admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Chat"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(todos.router, prefix="/todos", tags=["Todos"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
api_router.include_router(alarms.router, prefix="/alarms", tags=["Alarms"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(usage.router, prefix="/usage", tags=["Usage"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
