# Database package
from bot.database.models import User, Habit, HabitLog, ScheduleType, LogStatus
from bot.database.session import get_session, init_db, async_session_factory
from bot.database.crud import (
    get_or_create_user,
    get_user,
    update_user,
    create_habit,
    get_habits,
    get_active_habits,
    get_habit,
    update_habit,
    delete_habit,
    get_or_create_log,
    get_logs_for_habit,
    get_logs_for_date_range,
    get_all_users_with_reminders,
)

__all__ = [
    "User",
    "Habit",
    "HabitLog",
    "ScheduleType",
    "LogStatus",
    "get_session",
    "init_db",
    "async_session_factory",
    "get_or_create_user",
    "get_user",
    "update_user",
    "create_habit",
    "get_habits",
    "get_active_habits",
    "get_habit",
    "update_habit",
    "delete_habit",
    "get_or_create_log",
    "get_logs_for_habit",
    "get_logs_for_date_range",
    "get_all_users_with_reminders",
]
