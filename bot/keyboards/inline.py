"""
Inline-клавиатуры для бота.
"""
from typing import Sequence

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import config
from bot.database.models import Habit, HabitLog, LogStatus


def get_habits_tracking_keyboard(
    habits: Sequence[Habit],
    logs_today: dict[int, LogStatus],
) -> InlineKeyboardMarkup:
    """
    Клавиатура для отметки привычек за сегодня.
    
    Args:
        habits: Список активных привычек
        logs_today: Словарь {habit_id: status} для уже отмеченных сегодня
    """
    builder = InlineKeyboardBuilder()
    
    for habit in habits:
        current_status = logs_today.get(habit.id)
        
        # Формируем название с индикатором текущего статуса
        status_icon = ""
        if current_status == LogStatus.DONE:
            status_icon = "✅ "
        elif current_status == LogStatus.NOT_DONE:
            status_icon = "❌ "
        elif current_status == LogStatus.SKIPPED:
            status_icon = "⏭ "
        
        habit_name = f"{status_icon}{habit.name}"
        
        # Кнопки статуса
        builder.row(
            InlineKeyboardButton(
                text=habit_name,
                callback_data=f"habit_info:{habit.id}",
            ),
        )
        builder.row(
            InlineKeyboardButton(
                text="✅ Выполнено",
                callback_data=f"track:{habit.id}:done",
            ),
            InlineKeyboardButton(
                text="❌ Не сделал",
                callback_data=f"track:{habit.id}:not_done",
            ),
            InlineKeyboardButton(
                text="⏭ Пропуск",
                callback_data=f"track:{habit.id}:skipped",
            ),
        )
    
    if not habits:
        builder.row(
            InlineKeyboardButton(
                text="➕ Создать первую привычку",
                callback_data="add_habit_inline",
            )
        )
    
    return builder.as_markup()


def get_habit_management_keyboard(habits: Sequence[Habit]) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления привычками.
    
    Args:
        habits: Список всех привычек пользователя
    """
    builder = InlineKeyboardBuilder()
    
    for habit in habits:
        status_icon = "🟢" if habit.is_active else "🔴"
        schedule_info = ""
        if habit.schedule_type.value == "weekly":
            schedule_info = f" ({habit.weekly_target}x/нед)"
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} {habit.name}{schedule_info}",
                callback_data=f"manage:{habit.id}",
            )
        )
    
    if not habits:
        builder.row(
            InlineKeyboardButton(
                text="У вас пока нет привычек",
                callback_data="no_habits",
            )
        )
    
    return builder.as_markup()


def get_habit_actions_keyboard(habit_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура действий с конкретной привычкой.
    
    Args:
        habit_id: ID привычки
        is_active: Активна ли привычка
    """
    builder = InlineKeyboardBuilder()
    
    # Вкл/выкл
    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="🔴 Выключить",
                callback_data=f"toggle:{habit_id}:off",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🟢 Включить",
                callback_data=f"toggle:{habit_id}:on",
            )
        )
    
    # Переименовать и удалить
    builder.row(
        InlineKeyboardButton(
            text="✏️ Переименовать",
            callback_data=f"rename:{habit_id}",
        ),
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"delete:{habit_id}",
        ),
    )
    
    # Назад
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_to_habits",
        )
    )
    
    return builder.as_markup()


def get_confirmation_keyboard(action: str, habit_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Да",
            callback_data=f"confirm_{action}:{habit_id}",
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data=f"manage:{habit_id}",
        ),
    )
    
    return builder.as_markup()


def get_schedule_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа расписания."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📅 Ежедневно",
            callback_data="schedule:daily",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="📆 N раз в неделю",
            callback_data="schedule:weekly",
        ),
    )
    
    return builder.as_markup()


def get_weekly_target_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора количества раз в неделю."""
    builder = InlineKeyboardBuilder()
    
    for i in range(1, 8):
        builder.add(
            InlineKeyboardButton(
                text=str(i),
                callback_data=f"weekly_target:{i}",
            )
        )
    
    builder.adjust(4, 3)  # 4 кнопки в первом ряду, 3 во втором
    
    return builder.as_markup()


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора таймзоны."""
    builder = InlineKeyboardBuilder()
    
    tz_display = {
        "Europe/Moscow": "🇷🇺 Москва (UTC+3)",
        "Europe/Kiev": "🇺🇦 Киев (UTC+2)",
        "Europe/Minsk": "🇧🇾 Минск (UTC+3)",
        "Asia/Almaty": "🇰🇿 Алматы (UTC+6)",
        "Asia/Yekaterinburg": "🇷🇺 Екатеринбург (UTC+5)",
    }
    
    for tz in config.popular_timezones:
        builder.row(
            InlineKeyboardButton(
                text=tz_display.get(tz, tz),
                callback_data=f"tz:{tz}",
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="⌨️ Ввести вручную",
            callback_data="tz:custom",
        )
    )
    
    return builder.as_markup()


def get_settings_keyboard(reminders_enabled: bool) -> InlineKeyboardMarkup:
    """Клавиатура настроек."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🕐 Время напоминания",
            callback_data="settings:reminder_time",
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🌍 Часовой пояс",
            callback_data="settings:timezone",
        )
    )
    
    # Вкл/выкл напоминания
    if reminders_enabled:
        builder.row(
            InlineKeyboardButton(
                text="🔕 Выключить напоминания",
                callback_data="settings:reminders_off",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🔔 Включить напоминания",
                callback_data="settings:reminders_on",
            )
        )
    
    return builder.as_markup()
