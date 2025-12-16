"""
SQLAlchemy модели для базы данных.
"""
import enum
from datetime import datetime, time
from typing import Optional, List

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class ScheduleType(str, enum.Enum):
    """Тип расписания привычки."""
    DAILY = "daily"
    WEEKLY = "weekly"


class LogStatus(str, enum.Enum):
    """Статус выполнения привычки за день."""
    DONE = "done"
    NOT_DONE = "not_done"
    SKIPPED = "skipped"


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user_id
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    reminder_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True, default=None)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    habits: Mapped[List["Habit"]] = relationship(
        "Habit", back_populates="user", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, tz={self.timezone})>"


class Habit(Base):
    """Модель привычки."""
    __tablename__ = "habits"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50))
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType), default=ScheduleType.DAILY
    )
    weekly_target: Mapped[int] = mapped_column(Integer, default=7)  # Для weekly: сколько раз в неделю
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="habits")
    logs: Mapped[List["HabitLog"]] = relationship(
        "HabitLog", back_populates="habit", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Habit(id={self.id}, name={self.name}, type={self.schedule_type})>"


class HabitLog(Base):
    """Лог выполнения привычки за день."""
    __tablename__ = "habit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    habit_id: Mapped[int] = mapped_column(Integer, ForeignKey("habits.id", ondelete="CASCADE"))
    date: Mapped[datetime] = mapped_column(Date)  # Дата в TZ пользователя
    status: Mapped[LogStatus] = mapped_column(Enum(LogStatus))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    habit: Mapped["Habit"] = relationship("Habit", back_populates="logs")
    
    def __repr__(self) -> str:
        return f"<HabitLog(habit_id={self.habit_id}, date={self.date}, status={self.status})>"
