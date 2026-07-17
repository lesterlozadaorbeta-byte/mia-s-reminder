"""Telegram Bot - handles commands, callbacks, and AI chat."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.reminder import Reminder
from app.models.calendar import CalendarEvent
from app.models.todo import Todo

logger = logging.getLogger(__name__)
settings = get_settings()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - link Telegram account."""
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username

    welcome_text = (
        "👋 **Welcome to Mia's Reminder!**\n\n"
        "I can help you manage your life with:\n"
        "📅 Calendar & Events\n"
        "⏰ Reminders & Alarms\n"
        "✅ To-Do Lists\n"
        "🤖 AI-powered scheduling\n\n"
        "**Commands:**\n"
        "/link <email> - Link your account\n"
        "/today - Today's schedule\n"
        "/tomorrow - Tomorrow's schedule\n"
        "/reminders - Active reminders\n"
        "/todos - Pending tasks\n"
        "/remind <text> - Create a quick reminder\n"
        "/ask <question> - Ask the AI anything\n\n"
        "Or just send me a message and I'll help you!"
    )

    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Link Telegram account to app account."""
    if not context.args:
        await update.message.reply_text("Usage: /link your@email.com")
        return

    email = context.args[0]
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            await update.message.reply_text(
                "❌ No account found with this email. Please register in the app first."
            )
            return

        user.telegram_chat_id = chat_id
        user.telegram_username = username
        await db.commit()

    await update.message.reply_text(
        f"✅ Account linked successfully!\n"
        f"You'll now receive reminders and notifications here."
    )


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's schedule."""
    chat_id = str(update.effective_chat.id)
    user = await _get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("Please link your account first: /link your@email.com")
        return

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    async with AsyncSessionLocal() as db:
        # Get events
        events_result = await db.execute(
            select(CalendarEvent)
            .where(
                CalendarEvent.user_id == user.id,
                CalendarEvent.start_time >= today_start,
                CalendarEvent.start_time < today_end,
            )
            .order_by(CalendarEvent.start_time)
        )
        events = events_result.scalars().all()

        # Get reminders
        reminders_result = await db.execute(
            select(Reminder)
            .where(
                Reminder.user_id == user.id,
                Reminder.status == "active",
                Reminder.remind_at >= today_start,
                Reminder.remind_at < today_end,
            )
            .order_by(Reminder.remind_at)
        )
        reminders = reminders_result.scalars().all()

    # Build response
    text = "📅 **Today's Schedule**\n\n"

    if events:
        text += "**Events:**\n"
        for event in events:
            time_str = event.start_time.strftime("%H:%M")
            text += f"  🗓 {time_str} - {event.title}\n"
    else:
        text += "No events today.\n"

    text += "\n"

    if reminders:
        text += "**Reminders:**\n"
        for reminder in reminders:
            time_str = reminder.remind_at.strftime("%H:%M")
            text += f"  🔔 {time_str} - {reminder.title}\n"
    else:
        text += "No reminders today.\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def tomorrow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tomorrow's schedule."""
    chat_id = str(update.effective_chat.id)
    user = await _get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("Please link your account first: /link your@email.com")
        return

    now = datetime.now(timezone.utc)
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow_start + timedelta(days=1)

    async with AsyncSessionLocal() as db:
        events_result = await db.execute(
            select(CalendarEvent)
            .where(
                CalendarEvent.user_id == user.id,
                CalendarEvent.start_time >= tomorrow_start,
                CalendarEvent.start_time < tomorrow_end,
            )
            .order_by(CalendarEvent.start_time)
        )
        events = events_result.scalars().all()

    text = "📅 **Tomorrow's Schedule**\n\n"
    if events:
        for event in events:
            time_str = event.start_time.strftime("%H:%M")
            text += f"  🗓 {time_str} - {event.title}\n"
    else:
        text += "Nothing scheduled for tomorrow.\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active reminders."""
    chat_id = str(update.effective_chat.id)
    user = await _get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("Please link your account first: /link your@email.com")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Reminder)
            .where(
                Reminder.user_id == user.id,
                Reminder.status == "active",
            )
            .order_by(Reminder.remind_at)
            .limit(10)
        )
        reminders = result.scalars().all()

    if not reminders:
        await update.message.reply_text("✅ No active reminders!")
        return

    text = "🔔 **Active Reminders**\n\n"
    for r in reminders:
        date_str = r.remind_at.strftime("%m/%d %H:%M")
        persistent = " 🔁" if r.is_persistent else ""
        text += f"  • {r.title} - {date_str}{persistent}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def todos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending todos."""
    chat_id = str(update.effective_chat.id)
    user = await _get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("Please link your account first: /link your@email.com")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Todo)
            .where(
                Todo.user_id == user.id,
                Todo.is_completed == False,
                Todo.parent_id == None,
            )
            .order_by(Todo.priority, Todo.due_date)
            .limit(10)
        )
        todos = result.scalars().all()

    if not todos:
        await update.message.reply_text("✅ All tasks completed!")
        return

    priority_emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢"}
    text = "✅ **Pending Tasks**\n\n"
    for t in todos:
        emoji = priority_emoji.get(t.priority, "⚪")
        due = f" (due {t.due_date.strftime('%m/%d')})" if t.due_date else ""
        text += f"  {emoji} {t.title}{due}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask the AI a question."""
    if not context.args:
        await update.message.reply_text("Usage: /ask <your question>")
        return

    question = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    user = await _get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("Please link your account first.")
        return

    # Process with AI
    from app.ai.engine import AIEngine

    async with AsyncSessionLocal() as db:
        engine = AIEngine(db, user)
        response_text, actions, _ = await engine.process_message(
            user_message=question,
            conversation_history=[],
            context={},
        )

        # Execute any actions
        if actions:
            from app.ai.action_executor import ActionExecutor
            executor = ActionExecutor(db, user.id)
            for action in actions:
                await executor.execute(action)
            await db.commit()

    await update.message.reply_text(response_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-form messages - route to AI."""
    await ask_command(update, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = str(update.effective_chat.id)
    user = await _get_user_by_chat_id(chat_id)

    if not user:
        await query.edit_message_text("Please link your account first.")
        return

    # Parse callback data
    if data.startswith("done_"):
        reminder_id = data.replace("done_", "")
        await _mark_reminder_done(reminder_id, user.id)
        await query.edit_message_text("✅ Reminder marked as done!")

    elif data.startswith("snooze_"):
        parts = data.split("_")
        minutes = int(parts[1])
        reminder_id = parts[2]
        await _snooze_reminder(reminder_id, user.id, minutes)
        await query.edit_message_text(f"⏳ Snoozed for {minutes} minutes.")


async def _mark_reminder_done(reminder_id: str, user_id):
    """Mark a reminder as done from Telegram."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Reminder).where(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id,
            )
        )
        reminder = result.scalar_one_or_none()
        if reminder:
            reminder.status = "completed"
            reminder.completed_at = datetime.now(timezone.utc)
            await db.commit()


async def _snooze_reminder(reminder_id: str, user_id, minutes: int):
    """Snooze a reminder from Telegram."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Reminder).where(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id,
            )
        )
        reminder = result.scalar_one_or_none()
        if reminder:
            reminder.status = "snoozed"
            reminder.snoozed_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
            reminder.snooze_count += 1
            await db.commit()


async def _get_user_by_chat_id(chat_id: str):
    """Get user by Telegram chat ID."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_chat_id == chat_id)
        )
        return result.scalar_one_or_none()


def create_telegram_app() -> Application:
    """Create and configure the Telegram bot application."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("tomorrow", tomorrow_command))
    app.add_handler(CommandHandler("reminders", reminders_command))
    app.add_handler(CommandHandler("todos", todos_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
