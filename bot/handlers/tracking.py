"""
Обработчики для отслеживания привычек (отметки за день).
"""
import logging
from datetime import datetime

import pytz
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from bot.config import config
from bot.database import (
    get_session,
    get_or_create_user,
    get_user,
    get_active_habits,
    get_or_create_log,
    LogStatus,
)
from bot.keyboards.inline import get_habits_tracking_keyboard

logger = logging.getLogger(__name__)
router = Router()


def get_user_today(timezone: str) -> datetime:
    """Получить текущую дату в таймзоне пользователя."""
    try:
        tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.timezone(config.default_timezone)
    
    return datetime.now(tz).date()


@router.message(F.text == "✅ Отметить сегодня")
async def show_today_habits(message: Message) -> None:
    """Показать список привычек для отметки за сегодня."""
    user_id = message.from_user.id
    
    async with get_session() as session:
        user = await get_or_create_user(session, user_id)
        habits = await get_active_habits(session, user_id)
        
        if not habits:
            await message.answer(
                "😕 У тебя нет активных привычек.\n\n"
                "Нажми «➕ Добавить привычку» для создания.",
            )
            return
        
        # Получаем сегодняшнюю дату в TZ пользователя
        today = get_user_today(user.timezone)
        
        # Собираем текущие статусы за сегодня
        logs_today = {}
        for habit in habits:
            for log in habit.logs:
                if log.date == today:
                    logs_today[habit.id] = log.status
                    break
        
        await message.answer(
            f"📅 <b>Отметки за {today.strftime('%d.%m.%Y')}</b>\n\n"
            "Нажми кнопку чтобы отметить статус:",
            parse_mode="HTML",
            reply_markup=get_habits_tracking_keyboard(habits, logs_today),
        )


@router.callback_query(F.data.startswith("track:"))
async def track_habit(callback: CallbackQuery) -> None:
    """Отметить статус привычки за сегодня."""
    parts = callback.data.split(":")
    habit_id = int(parts[1])
    status_str = parts[2]
    
    # Преобразуем строку в статус
    status_map = {
        "done": LogStatus.DONE,
        "not_done": LogStatus.NOT_DONE,
        "skipped": LogStatus.SKIPPED,
    }
    status = status_map.get(status_str)
    
    if status is None:
        await callback.answer("Неизвестный статус", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    async with get_session() as session:
        user = await get_user(session, user_id)
        
        if user is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Получаем сегодняшнюю дату в TZ пользователя
        today = get_user_today(user.timezone)
        
        # Idempotent: создаём или обновляем лог
        log = await get_or_create_log(session, habit_id, today, status)
        
        # Получаем все активные привычки для обновления клавиатуры
        habits = await get_active_habits(session, user_id)
        
        # Собираем обновлённые статусы
        logs_today = {}
        for habit in habits:
            for habit_log in habit.logs:
                if habit_log.date == today:
                    logs_today[habit.id] = habit_log.status
                    break
        
        # Обновляем сообщение
        await callback.message.edit_reply_markup(
            reply_markup=get_habits_tracking_keyboard(habits, logs_today),
        )
        
        # Уведомление о статусе
        status_text = {
            LogStatus.DONE: "✅ Выполнено!",
            LogStatus.NOT_DONE: "❌ Не сделал",
            LogStatus.SKIPPED: "⏭ Пропущено",
        }
        await callback.answer(status_text.get(status, "Сохранено"))


@router.callback_query(F.data.startswith("habit_info:"))
async def habit_info(callback: CallbackQuery) -> None:
    """Показать информацию о привычке (нажатие на название)."""
    habit_id = int(callback.data.split(":")[1])
    
    # Просто показываем подсказку
    await callback.answer(
        "💡 Используй кнопки ниже для отметки статуса",
        show_alert=False,
    )
