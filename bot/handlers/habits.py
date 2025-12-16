"""
Обработчики для управления привычками.
"""
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.config import config
from bot.database import (
    get_session,
    get_or_create_user,
    create_habit,
    get_habits,
    get_habit,
    update_habit,
    delete_habit,
    ScheduleType,
)
from bot.keyboards.reply import get_main_menu_keyboard, get_cancel_keyboard
from bot.keyboards.inline import (
    get_habit_management_keyboard,
    get_habit_actions_keyboard,
    get_confirmation_keyboard,
    get_schedule_type_keyboard,
    get_weekly_target_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


class AddHabitStates(StatesGroup):
    """Состояния добавления привычки."""
    waiting_name = State()
    waiting_schedule_type = State()
    waiting_weekly_target = State()


class RenameHabitStates(StatesGroup):
    """Состояния переименования привычки."""
    waiting_new_name = State()


# === Мои привычки ===

@router.message(F.text == "📋 Мои привычки")
async def show_my_habits(message: Message) -> None:
    """Показать список привычек с управлением."""
    user_id = message.from_user.id
    
    async with get_session() as session:
        await get_or_create_user(session, user_id)
        habits = await get_habits(session, user_id)
    
    if not habits:
        await message.answer(
            "📋 У тебя пока нет привычек.\n\n"
            "Нажми «➕ Добавить привычку» чтобы создать первую!",
        )
        return
    
    await message.answer(
        "📋 <b>Твои привычки:</b>\n\n"
        "🟢 — активна, 🔴 — выключена\n"
        "Нажми на привычку для управления:",
        parse_mode="HTML",
        reply_markup=get_habit_management_keyboard(habits),
    )


@router.callback_query(F.data == "back_to_habits")
async def back_to_habits(callback: CallbackQuery) -> None:
    """Вернуться к списку привычек."""
    user_id = callback.from_user.id
    
    async with get_session() as session:
        habits = await get_habits(session, user_id)
    
    await callback.message.edit_text(
        "📋 <b>Твои привычки:</b>\n\n"
        "🟢 — активна, 🔴 — выключена\n"
        "Нажми на привычку для управления:",
        parse_mode="HTML",
        reply_markup=get_habit_management_keyboard(habits),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manage:"))
async def manage_habit(callback: CallbackQuery) -> None:
    """Показать действия для привычки."""
    habit_id = int(callback.data.split(":")[1])
    
    async with get_session() as session:
        habit = await get_habit(session, habit_id)
        
        if habit is None:
            await callback.answer("Привычка не найдена", show_alert=True)
            return
        
        schedule_info = ""
        if habit.schedule_type == ScheduleType.WEEKLY:
            schedule_info = f"\n📆 Частота: {habit.weekly_target} раз(а) в неделю"
        else:
            schedule_info = "\n📅 Частота: ежедневно"
        
        status = "🟢 Активна" if habit.is_active else "🔴 Выключена"
        
        await callback.message.edit_text(
            f"<b>{habit.name}</b>\n\n"
            f"Статус: {status}{schedule_info}",
            parse_mode="HTML",
            reply_markup=get_habit_actions_keyboard(habit_id, habit.is_active),
        )
    
    await callback.answer()


# === Вкл/выкл привычки ===

@router.callback_query(F.data.startswith("toggle:"))
async def toggle_habit(callback: CallbackQuery) -> None:
    """Включить/выключить привычку."""
    parts = callback.data.split(":")
    habit_id = int(parts[1])
    action = parts[2]  # on или off
    
    new_status = action == "on"
    
    async with get_session() as session:
        habit = await update_habit(session, habit_id, is_active=new_status)
        
        if habit is None:
            await callback.answer("Привычка не найдена", show_alert=True)
            return
        
        status_text = "включена 🟢" if new_status else "выключена 🔴"
        await callback.answer(f"Привычка {status_text}")
        
        # Обновляем сообщение
        schedule_info = ""
        if habit.schedule_type == ScheduleType.WEEKLY:
            schedule_info = f"\n📆 Частота: {habit.weekly_target} раз(а) в неделю"
        else:
            schedule_info = "\n📅 Частота: ежедневно"
        
        status = "🟢 Активна" if habit.is_active else "🔴 Выключена"
        
        await callback.message.edit_text(
            f"<b>{habit.name}</b>\n\n"
            f"Статус: {status}{schedule_info}",
            parse_mode="HTML",
            reply_markup=get_habit_actions_keyboard(habit_id, habit.is_active),
        )


# === Удаление привычки ===

@router.callback_query(F.data.startswith("delete:"))
async def confirm_delete_habit(callback: CallbackQuery) -> None:
    """Подтверждение удаления привычки."""
    habit_id = int(callback.data.split(":")[1])
    
    async with get_session() as session:
        habit = await get_habit(session, habit_id)
        
        if habit is None:
            await callback.answer("Привычка не найдена", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"⚠️ Ты уверен, что хочешь удалить привычку <b>{habit.name}</b>?\n\n"
            "Вся статистика будет потеряна!",
            parse_mode="HTML",
            reply_markup=get_confirmation_keyboard("delete", habit_id),
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def do_delete_habit(callback: CallbackQuery) -> None:
    """Удаление привычки."""
    habit_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    async with get_session() as session:
        success = await delete_habit(session, habit_id)
        
        if not success:
            await callback.answer("Привычка не найдена", show_alert=True)
            return
        
        await callback.answer("Привычка удалена 🗑")
        
        # Показываем обновлённый список
        habits = await get_habits(session, user_id)
        
        if habits:
            await callback.message.edit_text(
                "📋 <b>Твои привычки:</b>\n\n"
                "🟢 — активна, 🔴 — выключена\n"
                "Нажми на привычку для управления:",
                parse_mode="HTML",
                reply_markup=get_habit_management_keyboard(habits),
            )
        else:
            await callback.message.edit_text(
                "📋 У тебя больше нет привычек.\n\n"
                "Нажми «➕ Добавить привычку» чтобы создать новую!",
            )


# === Переименование привычки ===

@router.callback_query(F.data.startswith("rename:"))
async def start_rename_habit(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать переименование привычки."""
    habit_id = int(callback.data.split(":")[1])
    
    await state.update_data(rename_habit_id=habit_id)
    await state.set_state(RenameHabitStates.waiting_new_name)
    
    await callback.message.edit_text(
        "✏️ Введи новое название привычки (до 50 символов):",
    )
    await callback.answer()


@router.message(RenameHabitStates.waiting_new_name)
async def process_rename_habit(message: Message, state: FSMContext) -> None:
    """Обработка нового названия привычки."""
    new_name = message.text.strip()
    
    if new_name == "❌ Отмена":
        await state.clear()
        await message.answer("Переименование отменено.", reply_markup=get_main_menu_keyboard())
        return
    
    # Валидация
    if len(new_name) > config.max_habit_name_length:
        await message.answer(
            f"❌ Название слишком длинное! Максимум {config.max_habit_name_length} символов.\n"
            "Попробуй ещё раз:"
        )
        return
    
    if len(new_name) < 1:
        await message.answer("❌ Название не может быть пустым. Попробуй ещё раз:")
        return
    
    data = await state.get_data()
    habit_id = data.get("rename_habit_id")
    
    async with get_session() as session:
        habit = await update_habit(session, habit_id, name=new_name)
        
        if habit is None:
            await message.answer("Привычка не найдена.")
            await state.clear()
            return
    
    await state.clear()
    await message.answer(
        f"✅ Привычка переименована в <b>{new_name}</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )


# === Добавление привычки ===

@router.message(F.text == "➕ Добавить привычку")
async def start_add_habit(message: Message, state: FSMContext) -> None:
    """Начать добавление новой привычки."""
    await message.answer(
        "➕ Введи название новой привычки (до 50 символов):",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(AddHabitStates.waiting_name)


@router.callback_query(F.data == "add_habit_inline")
async def start_add_habit_inline(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать добавление новой привычки (из inline кнопки)."""
    await callback.message.edit_text(
        "➕ Введи название новой привычки (до 50 символов):",
    )
    await state.set_state(AddHabitStates.waiting_name)
    await callback.answer()


@router.message(AddHabitStates.waiting_name)
async def process_new_habit_name(message: Message, state: FSMContext) -> None:
    """Обработка названия новой привычки."""
    habit_name = message.text.strip()
    
    if habit_name == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=get_main_menu_keyboard())
        return
    
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
    
    await state.update_data(habit_name=habit_name)
    
    await message.answer(
        f"✅ Привычка: <b>{habit_name}</b>\n\n"
        "Выбери частоту:",
        parse_mode="HTML",
        reply_markup=get_schedule_type_keyboard(),
    )
    await state.set_state(AddHabitStates.waiting_schedule_type)


@router.callback_query(F.data.startswith("schedule:"), AddHabitStates.waiting_schedule_type)
async def process_new_habit_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора типа расписания для новой привычки."""
    schedule_type = callback.data.split(":")[1]
    await state.update_data(schedule_type=schedule_type)
    
    if schedule_type == "weekly":
        await callback.message.edit_text(
            "📆 Сколько раз в неделю нужно выполнять?",
            reply_markup=get_weekly_target_keyboard(),
        )
        await state.set_state(AddHabitStates.waiting_weekly_target)
    else:
        # Сразу создаём привычку
        await create_new_habit(callback, state, weekly_target=7)
    
    await callback.answer()


@router.callback_query(F.data.startswith("weekly_target:"), AddHabitStates.waiting_weekly_target)
async def process_new_habit_weekly_target(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора количества раз в неделю для новой привычки."""
    target = int(callback.data.split(":")[1])
    await create_new_habit(callback, state, weekly_target=target)
    await callback.answer()


async def create_new_habit(
    callback: CallbackQuery,
    state: FSMContext,
    weekly_target: int,
) -> None:
    """Создание новой привычки."""
    data = await state.get_data()
    habit_name = data["habit_name"]
    schedule_type = data.get("schedule_type", "daily")
    user_id = callback.from_user.id
    
    async with get_session() as session:
        await get_or_create_user(session, user_id)
        habit = await create_habit(
            session,
            user_id=user_id,
            name=habit_name,
            schedule_type=ScheduleType.DAILY if schedule_type == "daily" else ScheduleType.WEEKLY,
            weekly_target=weekly_target,
        )
    
    await state.clear()
    
    schedule_text = "ежедневно" if schedule_type == "daily" else f"{weekly_target} раз(а) в неделю"
    
    await callback.message.edit_text(
        f"🎉 Привычка <b>{habit_name}</b> создана!\n"
        f"📅 Частота: {schedule_text}",
        parse_mode="HTML",
    )
    
    # Отправляем сообщение с меню
    await callback.message.answer(
        "Используй меню для управления.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "no_habits")
async def no_habits_callback(callback: CallbackQuery) -> None:
    """Обработка нажатия на пустой список привычек."""
    await callback.answer("Нажми «➕ Добавить привычку» чтобы создать первую!")
