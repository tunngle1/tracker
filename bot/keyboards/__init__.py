# Keyboards package
from bot.keyboards.reply import get_main_menu_keyboard
from bot.keyboards.inline import (
    get_habits_tracking_keyboard,
    get_habit_management_keyboard,
    get_habit_actions_keyboard,
    get_timezone_keyboard,
    get_settings_keyboard,
    get_schedule_type_keyboard,
    get_weekly_target_keyboard,
    get_confirmation_keyboard,
)

__all__ = [
    "get_main_menu_keyboard",
    "get_habits_tracking_keyboard",
    "get_habit_management_keyboard",
    "get_habit_actions_keyboard",
    "get_timezone_keyboard",
    "get_settings_keyboard",
    "get_schedule_type_keyboard",
    "get_weekly_target_keyboard",
    "get_confirmation_keyboard",
]
