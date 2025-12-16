"""
Обработчики /start и /help команд.
Включает онбординг для новых пользователей.
"""
import logging
import re
from datetime import time

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.config import config
from bot.database import (
    get_session,
    get_or_create_user,
    get_user,
    create_habit,
    update_user,
    ScheduleType,
)
from bot.keyboards.reply import get_main_menu_keyboard, get_cancel_keyboard
from bot.keyboards.inline import (
    get_schedule_type_keyboard,
    get_weekly_target_keyboard,
)
from bot.services.scheduler import scheduler_service

logger = logging.getLogger(__name__)
router = Router()


class OnboardingStates(StatesGroup):
    """Состояния онбординга."""
    waiting_habit_name = State()
    waiting_schedule_type = State()
    waiting_weekly_target = State()
    waiting_reminder_time = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start - начало онбординга."""
    user_id = message.from_user.id
    
    async with get_session() as session:
        user = await get_user(session, user_id)
        
        if user is not None:
            # Пользователь уже существует
            await message.answer(
                "👋 С возвращением! Используй меню для управления привычками.",
                reply_markup=get_main_menu_keyboard(),
            )
            await state.clear()
            return
        
        # Создаём нового пользователя с дефолтной таймзоной
        await get_or_create_user(session, user_id, config.default_timezone)
    
    # Начинаем онбординг
    await message.answer(
        "👋 Привет! Я помогу тебе отслеживать привычки.\n\n"
        "Давай создадим твою первую привычку! 💪\n\n"
        "Напиши название привычки (до 50 символов):",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(OnboardingStates.waiting_habit_name)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help."""
    await message.answer(
        "📚 <b>Справка по боту</b>\n\n"
        "🎯 <b>Как это работает:</b>\n"
        "1. Создай привычки, которые хочешь отслеживать\n"
        "2. Каждый день отмечай выполнение в 1 клик\n"
        "3. Следи за своим прогрессом в статистике\n\n"
        "📊 <b>Streak (серия):</b>\n"
        "• Daily: считает дни подряд с выполнением\n"
        "• Weekly: считает недели, где цель достигнута\n"
        "• 'Пропуск' не ломает серию!\n\n"
        "⚙️ <b>Настройки:</b>\n"
        "• Время напоминания — когда бот напомнит отметить\n"
        "• Часовой пояс — для правильного определения 'сегодня'\n\n"
        "🔧 <b>Команды:</b>\n"
        "/start — начать сначала\n"
        "/help — эта справка",
        parse_mode="HTML",
    )


# === Онбординг: создание первой привычки ===

@router.message(F.text == "❌ Отмена", StateFilter("*"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """Отмена текущего действия."""
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(OnboardingStates.waiting_habit_name)
async def process_habit_name(message: Message, state: FSMContext) -> None:
    """Обработка названия привычки."""
    habit_name = message.text.strip()
    
    # Валидация
    if len(habit_name) > config.max_habit_name_length:
        await message.answer(
            f"❌ Название слишком длинное! Максимум {config.max_habit_name_length} символов.\n"
            "Попробуй ещё раз:"
        )
        return
    
    if len(habit_name) < 1:
        await message.answer("❌ Название не может быть пустым. Попробуй ещё раз:")
        return
    
    # Сохраняем в состоянии
    await state.update_data(habit_name=habit_name)
    
    await message.answer(
        f"✅ Отлично! Привычка: <b>{habit_name}</b>\n\n"
        "Выбери частоту:",
        parse_mode="HTML",
        reply_markup=get_schedule_type_keyboard(),
    )
    await state.set_state(OnboardingStates.waiting_schedule_type)


@router.callback_query(F.data.startswith("schedule:"), OnboardingStates.waiting_schedule_type)
async def process_schedule_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора типа расписания."""
    schedule_type = callback.data.split(":")[1]
    await state.update_data(schedule_type=schedule_type)
    
    if schedule_type == "weekly":
        await callback.message.edit_text(
            "📆 Сколько раз в неделю нужно выполнять?",
            reply_markup=get_weekly_target_keyboard(),
        )
        await state.set_state(OnboardingStates.waiting_weekly_target)
    else:
        await state.update_data(weekly_target=7)
        await ask_reminder_time(callback.message, state)
    
    await callback.answer()


@router.callback_query(F.data.startswith("weekly_target:"), OnboardingStates.waiting_weekly_target)
async def process_weekly_target(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора количества раз в неделю."""
    target = int(callback.data.split(":")[1])
    await state.update_data(weekly_target=target)
    
    await ask_reminder_time(callback.message, state)
    await callback.answer()


async def ask_reminder_time(message: Message, state: FSMContext) -> None:
    """Запрос времени напоминания."""
    await message.edit_text(
        "🕐 В какое время присылать напоминание?\n\n"
        "Введи время в формате <b>ЧЧ:ММ</b> (например, 09:00 или 21:30):",
        parse_mode="HTML",
    )
    await state.set_state(OnboardingStates.waiting_reminder_time)


@router.message(OnboardingStates.waiting_reminder_time)
async def process_reminder_time(message: Message, state: FSMContext) -> None:
    """Обработка времени напоминания."""
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
    
    # Получаем данные из состояния
    data = await state.get_data()
    habit_name = data["habit_name"]
    schedule_type = data["schedule_type"]
    weekly_target = data.get("weekly_target", 7)
    
    user_id = message.from_user.id
    
    async with get_session() as session:
        # Создаём привычку
        habit = await create_habit(
            session,
            user_id=user_id,
            name=habit_name,
            schedule_type=ScheduleType.DAILY if schedule_type == "daily" else ScheduleType.WEEKLY,
            weekly_target=weekly_target,
        )
        
        # Обновляем время напоминания пользователя
        user = await update_user(
            session,
            user_id=user_id,
            reminder_time=reminder_time,
            reminders_enabled=True,
        )
        
        # Добавляем job в планировщик
        scheduler_service.add_reminder_job(
            user_id=user_id,
            reminder_time=reminder_time,
            timezone=user.timezone,
        )
    
    await state.clear()
    
    schedule_text = "ежедневно" if schedule_type == "daily" else f"{weekly_target} раз(а) в неделю"
    
    await message.answer(
        f"🎉 <b>Отлично! Всё готово!</b>\n\n"
        f"✅ Привычка: <b>{habit_name}</b>\n"
        f"📅 Частота: {schedule_text}\n"
        f"🕐 Напоминание: {time_text}\n\n"
        f"Используй меню для управления привычками. Удачи! 💪",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )
