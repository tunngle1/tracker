"""
CRUD операции для работы с базой данных.
"""
from datetime import date, time
from typing import List, Optional, Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Habit, HabitLog, User, ScheduleType, LogStatus


# === User CRUD ===

async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    timezone: str = "Europe/Moscow",
) -> User:
    """Получить пользователя или создать нового."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        user = User(id=user_id, timezone=timezone)
        session.add(user)
        await session.flush()
    
    return user


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Получить пользователя по ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(
    session: AsyncSession,
    user_id: int,
    timezone: Optional[str] = None,
    reminder_time: Optional[time] = None,
    reminders_enabled: Optional[bool] = None,
) -> Optional[User]:
    """Обновить данные пользователя."""
    user = await get_user(session, user_id)
    if user is None:
        return None
    
    if timezone is not None:
        user.timezone = timezone
    if reminder_time is not None:
        user.reminder_time = reminder_time
    if reminders_enabled is not None:
        user.reminders_enabled = reminders_enabled
    
    await session.flush()
    return user


async def get_all_users_with_reminders(session: AsyncSession) -> Sequence[User]:
    """Получить всех пользователей с включёнными напоминаниями."""
    result = await session.execute(
        select(User).where(
            and_(
                User.reminders_enabled == True,
                User.reminder_time.isnot(None),
            )
        )
    )
    return result.scalars().all()


# === Habit CRUD ===

async def create_habit(
    session: AsyncSession,
    user_id: int,
    name: str,
    schedule_type: ScheduleType = ScheduleType.DAILY,
    weekly_target: int = 7,
) -> Habit:
    """Создать новую привычку."""
    habit = Habit(
        user_id=user_id,
        name=name,
        schedule_type=schedule_type,
        weekly_target=weekly_target,
    )
    session.add(habit)
    await session.flush()
    return habit


async def get_habits(session: AsyncSession, user_id: int) -> Sequence[Habit]:
    """Получить все привычки пользователя с предзагрузкой логов."""
    result = await session.execute(
        select(Habit)
        .where(Habit.user_id == user_id)
        .options(selectinload(Habit.logs))
        .order_by(Habit.created_at)
    )
    return result.scalars().all()


async def get_active_habits(session: AsyncSession, user_id: int) -> Sequence[Habit]:
    """Получить активные привычки пользователя с предзагрузкой логов."""
    result = await session.execute(
        select(Habit)
        .where(and_(Habit.user_id == user_id, Habit.is_active == True))
        .options(selectinload(Habit.logs))
        .order_by(Habit.created_at)
    )
    return result.scalars().all()


async def get_habit(session: AsyncSession, habit_id: int) -> Optional[Habit]:
    """Получить привычку по ID."""
    result = await session.execute(select(Habit).where(Habit.id == habit_id))
    return result.scalar_one_or_none()


async def update_habit(
    session: AsyncSession,
    habit_id: int,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    schedule_type: Optional[ScheduleType] = None,
    weekly_target: Optional[int] = None,
) -> Optional[Habit]:
    """Обновить привычку."""
    habit = await get_habit(session, habit_id)
    if habit is None:
        return None
    
    if name is not None:
        habit.name = name
    if is_active is not None:
        habit.is_active = is_active
    if schedule_type is not None:
        habit.schedule_type = schedule_type
    if weekly_target is not None:
        habit.weekly_target = weekly_target
    
    await session.flush()
    return habit


async def delete_habit(session: AsyncSession, habit_id: int) -> bool:
    """Удалить привычку."""
    habit = await get_habit(session, habit_id)
    if habit is None:
        return False
    
    await session.delete(habit)
    await session.flush()
    return True


# === HabitLog CRUD ===

async def get_or_create_log(
    session: AsyncSession,
    habit_id: int,
    log_date: date,
    status: LogStatus,
) -> HabitLog:
    """Получить или создать лог привычки за дату. Idempotent: обновляет статус если лог существует."""
    result = await session.execute(
        select(HabitLog).where(
            and_(HabitLog.habit_id == habit_id, HabitLog.date == log_date)
        )
    )
    log = result.scalar_one_or_none()
    
    if log is None:
        log = HabitLog(habit_id=habit_id, date=log_date, status=status)
        session.add(log)
    else:
        log.status = status
    
    await session.flush()
    return log


async def get_logs_for_habit(
    session: AsyncSession,
    habit_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Sequence[HabitLog]:
    """Получить логи привычки за период."""
    query = select(HabitLog).where(HabitLog.habit_id == habit_id)
    
    if start_date:
        query = query.where(HabitLog.date >= start_date)
    if end_date:
        query = query.where(HabitLog.date <= end_date)
    
    query = query.order_by(HabitLog.date)
    result = await session.execute(query)
    return result.scalars().all()


async def get_logs_for_date_range(
    session: AsyncSession,
    habit_id: int,
    start_date: date,
    end_date: date,
) -> Sequence[HabitLog]:
    """Получить логи привычки за диапазон дат."""
    result = await session.execute(
        select(HabitLog).where(
            and_(
                HabitLog.habit_id == habit_id,
                HabitLog.date >= start_date,
                HabitLog.date <= end_date,
            )
        ).order_by(HabitLog.date)
    )
    return result.scalars().all()
