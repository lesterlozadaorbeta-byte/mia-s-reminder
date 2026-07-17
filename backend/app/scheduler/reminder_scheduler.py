"""Reminder scheduler - handles persistent reminders and recurring schedules."""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.reminder import Reminder
from app.models.alarm import Alarm

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_reminders():
    """Check for reminders that need to be triggered."""
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # Find active reminders that are due
        result = await db.execute(
            select(Reminder).where(
                Reminder.status.in_(["active", "snoozed"]),
                Reminder.remind_at <= now,
            )
        )
        reminders = result.scalars().all()

        for reminder in reminders:
            # Check if snoozed reminder is ready
            if reminder.status == "snoozed" and reminder.snoozed_until:
                if reminder.snoozed_until > now:
                    continue
                # Snooze period is over, reactivate
                reminder.status = "active"

            # Check persistent reminder logic
            if reminder.is_persistent:
                await _handle_persistent_reminder(reminder, now, db)
            else:
                # Non-persistent: just send notification once
                await _send_reminder_notification(reminder)
                if not reminder.is_recurring:
                    reminder.status = "completed"
                    reminder.completed_at = now
                else:
                    _advance_recurring_reminder(reminder)

            reminder.last_notified_at = now

        await db.commit()


async def _handle_persistent_reminder(reminder: Reminder, now: datetime, db: AsyncSession):
    """Handle persistent reminder logic - keep reminding until done."""
    # Start persistence tracking if first trigger
    if not reminder.persistence_started_at:
        reminder.persistence_started_at = now

    # Check if max duration exceeded
    elapsed = (now - reminder.persistence_started_at).total_seconds() / 60
    if elapsed >= reminder.max_persistence_duration_minutes:
        reminder.status = "expired"
        logger.info(f"Reminder {reminder.id} expired after {elapsed} minutes")
        return

    # Check if enough time passed since last notification
    if reminder.last_notified_at:
        since_last = (now - reminder.last_notified_at).total_seconds() / 60
        if since_last < reminder.persistence_interval_minutes:
            return  # Not time yet

    # Send notification
    await _send_reminder_notification(reminder)


async def _send_reminder_notification(reminder: Reminder):
    """Send reminder notification via configured channels."""
    from app.notifications.notification_service import NotificationService

    notification_service = NotificationService()

    notification_data = {
        "reminder_id": str(reminder.id),
        "title": reminder.title,
        "description": reminder.description or "",
        "priority": reminder.priority,
        "remind_at": reminder.remind_at.isoformat(),
        "is_persistent": reminder.is_persistent,
        "actions": [
            {"label": "Done", "action": "done"},
            {"label": "Snooze 5m", "action": "snooze_5"},
            {"label": "Snooze 10m", "action": "snooze_10"},
            {"label": "Snooze 30m", "action": "snooze_30"},
        ],
    }

    if reminder.notify_push:
        await notification_service.send_push(
            user_id=str(reminder.user_id),
            title=f"Reminder: {reminder.title}",
            body=reminder.description or "You have a pending reminder",
            data=notification_data,
        )

    if reminder.notify_telegram:
        await notification_service.send_telegram(
            user_id=str(reminder.user_id),
            reminder_data=notification_data,
        )


def _advance_recurring_reminder(reminder: Reminder):
    """Calculate next occurrence for recurring reminder."""
    from dateutil.relativedelta import relativedelta

    if reminder.recurrence_type == "daily":
        reminder.remind_at += timedelta(days=1)
    elif reminder.recurrence_type == "weekly":
        reminder.remind_at += timedelta(weeks=1)
    elif reminder.recurrence_type == "monthly":
        reminder.remind_at += relativedelta(months=1)
    elif reminder.recurrence_type == "yearly":
        reminder.remind_at += relativedelta(years=1)

    # Reset persistence tracking
    reminder.persistence_started_at = None
    reminder.snooze_count = 0
    reminder.last_notified_at = None

    # Check if past recurrence end
    if reminder.recurrence_end and reminder.remind_at > reminder.recurrence_end:
        reminder.status = "completed"


async def check_alarms():
    """Check for alarms that need to trigger."""
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Alarm).where(
                Alarm.is_active == True,
                Alarm.next_trigger_at <= now,
            )
        )
        alarms = result.scalars().all()

        for alarm in alarms:
            await _trigger_alarm(alarm, now)
            alarm.last_triggered_at = now

            # Calculate next trigger
            if alarm.is_recurring and alarm.repeat_days:
                _advance_recurring_alarm(alarm, now)
            else:
                alarm.is_active = False

        await db.commit()


async def _trigger_alarm(alarm: Alarm, now: datetime):
    """Trigger an alarm notification."""
    from app.notifications.notification_service import NotificationService

    service = NotificationService()
    await service.send_push(
        user_id=str(alarm.user_id),
        title=f"Alarm: {alarm.title}",
        body=alarm.description or "Your alarm is ringing!",
        data={
            "alarm_id": str(alarm.id),
            "type": "alarm",
            "sound": alarm.sound_file,
            "vibration": alarm.vibration_enabled,
        },
    )


def _advance_recurring_alarm(alarm: Alarm, now: datetime):
    """Calculate next trigger time for recurring alarm."""
    # Find next day in repeat_days
    current_day = now.weekday()
    repeat_days = sorted(alarm.repeat_days)

    next_day = None
    for day in repeat_days:
        if day > current_day:
            next_day = day
            break

    if next_day is None:
        next_day = repeat_days[0]
        days_ahead = 7 - current_day + next_day
    else:
        days_ahead = next_day - current_day

    next_date = now + timedelta(days=days_ahead)
    alarm.next_trigger_at = next_date.replace(
        hour=alarm.alarm_time.hour,
        minute=alarm.alarm_time.minute,
        second=0,
        microsecond=0,
    )
    alarm.current_snooze_count = 0


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        check_reminders,
        IntervalTrigger(seconds=30),
        id="check_reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        check_alarms,
        IntervalTrigger(seconds=15),
        id="check_alarms",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Background scheduler stopped")
