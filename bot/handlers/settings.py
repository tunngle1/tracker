"""
Обработчики для настроек пользователя.
"""
import logging
import re
from datetime import time

import pytz
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.config import config
from bot.database import get_session, get_or_create_user, get_user, update_user
from bot.keyboards.reply import get_main_menu_keyboard, get_cancel_keyboard
from bot.keyboards.inline import get_settings_keyboard, get_timezone_keyboard
from bot.services.scheduler import scheduler_service

logger = logging.getLogger(__name__)
router = Router()


class SettingsStates(StatesGroup):
    """Состояния настроек."""
    waiting_reminder_time = State()
    waiting_custom_timezone = State()


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message) -> None:
    """Показать настройки пользователя."""
    user_id = message.from_user.id
    
    async with get_session() as session:
        user = await get_or_create_user(session, user_id)
        
        reminder_status = "выключены 🔕"
        if user.reminders_enabled and user.reminder_time:
            reminder_status = f"включены 🔔 в {user.reminder_time.strftime('%H:%M')}"
        elif user.reminders_enabled:
            reminder_status = "включены 🔔 (время не задано)"
        
        await message.answer(
            "⚙️ <b>Настройки</b>\n\n"
            f"🌍 Часовой пояс: <b>{user.timezone}</b>\n"
            f"🔔 Напоминания: {reminder_status}\n",
            parse_mode="HTML",
            reply_markup=get_settings_keyboard(user.reminders_enabled),
        )


# === Время напоминания ===

@router.callback_query(F.data == "settings:reminder_time")
async def ask_reminder_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить новое время напоминания."""
    await callback.message.edit_text(
        "🕐 Введи новое время напоминания в формате <b>ЧЧ:ММ</b>\n"
        "(например, 09:00 или 21:30):",
        parse_mode="HTML",
    )
    await state.set_state(SettingsStates.waiting_reminder_time)
    await callback.answer()


@router.message(SettingsStates.waiting_reminder_time)
async def process_reminder_time(message: Message, state: FSMContext) -> None:
    """Обработка нового времени напоминания."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Изменение отменено.", reply_markup=get_main_menu_keyboard())
        return
    
    time_text = message.text.strip()
    
    # Валидация формата HH:MM
    pattern = r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$"
    match = re.match(pattern, time_text)
    
    if not match:
        await message.answer(
            "❌ Неверный формат! Введи время в формате <b>ЧЧ:ММ</b>\n"
            "Например: 09:00, 21:30, 08:45",
            parse_mode="HTML",
        )
        return
    
    hours, minutes = int(match.group(1)), int(match.group(2))
    reminder_time = time(hours, minutes)
    
    user_id = message.from_user.id
    
    async with get_session() as session:
        user = await update_user(
            session,
            user_id=user_id,
            reminder_time=reminder_time,
            reminders_enabled=True,
        )
        
        # Обновляем job в планировщике
        scheduler_service.add_reminder_job(
            user_id=user_id,
            reminder_time=reminder_time,
            timezone=user.timezone,
        )
    
    await state.clear()
    await message.answer(
        f"✅ Время напоминания установлено: <b>{time_text}</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )


# === Часовой пояс ===

@router.callback_query(F.data == "settings:timezone")
async def show_timezone_options(callback: CallbackQuery) -> None:
    """Показать выбор часового пояса."""
    await callback.message.edit_text(
        "🌍 Выбери часовой пояс:",
        reply_markup=get_timezone_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tz:"))
async def process_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора часового пояса."""
    timezone = callback.data.split(":", 1)[1]
    
    if timezone == "custom":
        # Ручной ввод
        await callback.message.edit_text(
            "⌨️ Введи название часового пояса в формате IANA\n"
            "(например: Europe/London, Asia/Tokyo, America/New_York):\n\n"
            "Список зон: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
        )
        await state.set_state(SettingsStates.waiting_custom_timezone)
        await callback.answer()
        return
    
    # Проверяем валидность таймзоны
    try:
        pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        await callback.answer("Неизвестный часовой пояс", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    async with get_session() as session:
        user = await update_user(session, user_id=user_id, timezone=timezone)
        
        # Если есть напоминания, обновляем job с новой таймзоной
        if user.reminder_time and user.reminders_enabled:
            scheduler_service.add_reminder_job(
                user_id=user_id,
                reminder_time=user.reminder_time,
                timezone=timezone,
            )
    
    await callback.message.edit_text(
        f"✅ Часовой пояс установлен: <b>{timezone}</b>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SettingsStates.waiting_custom_timezone)
async def process_custom_timezone(message: Message, state: FSMContext) -> None:
    """Обработка ручного ввода часового пояса."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Изменение отменено.", reply_markup=get_main_menu_keyboard())
        return
    
    timezone = message.text.strip()
    
    # Проверяем валидность таймзоны
    try:
        pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        await message.answer(
            f"❌ Часовой пояс <b>{timezone}</b> не найден.\n"
            "Проверь правильность написания.\n\n"
            "Примеры: Europe/London, Asia/Tokyo, America/New_York",
            parse_mode="HTML",
        )
        return
    
    user_id = message.from_user.id
    
    async with get_session() as session:
        user = await update_user(session, user_id=user_id, timezone=timezone)
        
        # Если есть напоминания, обновляем job с новой таймзоной
        if user.reminder_time and user.reminders_enabled:
            scheduler_service.add_reminder_job(
                user_id=user_id,
                reminder_time=user.reminder_time,
                timezone=timezone,
            )
    
    await state.clear()
    await message.answer(
        f"✅ Часовой пояс установлен: <b>{timezone}</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )


# === Вкл/выкл напоминаний ===

@router.callback_query(F.data == "settings:reminders_on")
async def enable_reminders(callback: CallbackQuery) -> None:
    """Включить напоминания."""
    user_id = callback.from_user.id
    
    async with get_session() as session:
        user = await update_user(session, user_id=user_id, reminders_enabled=True)
        
        if user.reminder_time:
            # Добавляем job если время задано
            scheduler_service.add_reminder_job(
                user_id=user_id,
                reminder_time=user.reminder_time,
                timezone=user.timezone,
            )
            await callback.message.edit_text(
                f"🔔 Напоминания включены!\n"
                f"Время: {user.reminder_time.strftime('%H:%M')}",
                reply_markup=get_settings_keyboard(True),
            )
        else:
            await callback.message.edit_text(
                "🔔 Напоминания включены!\n"
                "⚠️ Не забудь установить время напоминания.",
                reply_markup=get_settings_keyboard(True),
            )
    
    await callback.answer("Напоминания включены 🔔")


@router.callback_query(F.data == "settings:reminders_off")
async def disable_reminders(callback: CallbackQuery) -> None:
    """Выключить напоминания."""
    user_id = callback.from_user.id
    
    async with get_session() as session:
        await update_user(session, user_id=user_id, reminders_enabled=False)
        
        # Удаляем job
        scheduler_service.remove_reminder_job(user_id)
    
    await callback.message.edit_text(
        "🔕 Напоминания выключены.",
        reply_markup=get_settings_keyboard(False),
    )
    await callback.answer("Напоминания выключены 🔕")
