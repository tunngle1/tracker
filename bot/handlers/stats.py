"""
Обработчики для статистики привычек.
"""
import logging
from datetime import datetime

import pytz
from aiogram import Router, F
from aiogram.types import Message

from bot.config import config
from bot.database import (
    get_session,
    get_or_create_user,
    get_habits,
    get_logs_for_habit,
)
from bot.services.streak import get_habit_stats

logger = logging.getLogger(__name__)
router = Router()


def get_user_today(timezone: str) -> datetime:
    """Получить текущую дату в таймзоне пользователя."""
    try:
        tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.timezone(config.default_timezone)
    
    return datetime.now(tz).date()


@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message) -> None:
    """Показать статистику по всем привычкам."""
    user_id = message.from_user.id
    
    async with get_session() as session:
        user = await get_or_create_user(session, user_id)
        habits = await get_habits(session, user_id)
        
        if not habits:
            await message.answer(
                "📊 <b>Статистика</b>\n\n"
                "У тебя пока нет привычек.\n"
                "Создай первую, чтобы получить статистику!",
                parse_mode="HTML",
            )
            return
        
        today = get_user_today(user.timezone)
        
        stats_text = "📊 <b>Статистика привычек</b>\n\n"
        
        for habit in habits:
            # Получаем все логи привычки
            logs = await get_logs_for_habit(session, habit.id)
            
            # Вычисляем статистику
            stats = get_habit_stats(
                logs=logs,
                schedule_type=habit.schedule_type,
                weekly_target=habit.weekly_target,
                today=today,
            )
            
            # Формируем текст
            status_icon = "🟢" if habit.is_active else "🔴"
            schedule_emoji = "📅" if habit.schedule_type.value == "daily" else "📆"
            
            stats_text += f"{status_icon} <b>{habit.name}</b>\n"
            stats_text += f"   {schedule_emoji} "
            
            if habit.schedule_type.value == "daily":
                stats_text += "Ежедневно\n"
            else:
                stats_text += f"{habit.weekly_target}x в неделю\n"
            
            stats_text += f"   🔥 Текущая серия: <b>{stats.current_streak}</b>\n"
            stats_text += f"   🏆 Лучшая серия: <b>{stats.best_streak}</b>\n"
            stats_text += f"   ✅ За 7 дней: {stats.done_7_days}\n"
            stats_text += f"   ✅ За 30 дней: {stats.done_30_days}\n"
            stats_text += f"   📈 Всего выполнено: {stats.total_done}\n\n"
        
        await message.answer(stats_text, parse_mode="HTML")
