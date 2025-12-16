"""
Сервис планировщика напоминаний.
Использует APScheduler для отправки ежедневных напоминаний.
"""
import logging
from datetime import datetime, time
from typing import TYPE_CHECKING, Callable, Awaitable

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor

if TYPE_CHECKING:
    from aiogram import Bot

from bot.config import config

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис для управления напоминаниями."""
    
    def __init__(self):
        # Используем AsyncIOExecutor для правильной работы с async
        executors = {
            'default': AsyncIOExecutor(),
        }
        self.scheduler = AsyncIOScheduler(executors=executors)
        self._bot: "Bot" = None
        self._send_reminder_callback: Callable[[int], Awaitable[None]] = None
    
    def set_bot(self, bot: "Bot") -> None:
        """Установить экземпляр бота."""
        self._bot = bot
    
    def set_reminder_callback(
        self, callback: Callable[[int], Awaitable[None]]
    ) -> None:
        """Установить callback для отправки напоминания."""
        self._send_reminder_callback = callback
    
    def start(self) -> None:
        """Запустить планировщик."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def shutdown(self) -> None:
        """Остановить планировщик."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
    
    def add_reminder_job(
        self,
        user_id: int,
        reminder_time: time,
        timezone: str,
    ) -> None:
        """
        Добавить или обновить job напоминания для пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            reminder_time: Время напоминания
            timezone: Таймзона пользователя (IANA string)
        """
        job_id = f"reminder_{user_id}"
        
        # Удаляем существующий job если есть
        self.remove_reminder_job(user_id)
        
        try:
            tz = pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {timezone}, using default")
            tz = pytz.timezone(config.default_timezone)
        
        # Создаём trigger для ежедневного запуска в указанное время
        trigger = CronTrigger(
            hour=reminder_time.hour,
            minute=reminder_time.minute,
            timezone=tz,
        )
        
        # Добавляем job
        self.scheduler.add_job(
            self._trigger_reminder,
            trigger=trigger,
            id=job_id,
            args=[user_id],
            replace_existing=True,
            name=f"Reminder for user {user_id}",
        )
        
        logger.info(
            f"Added reminder job for user {user_id} at {reminder_time} ({timezone})"
        )
    
    def remove_reminder_job(self, user_id: int) -> None:
        """Удалить job напоминания для пользователя."""
        job_id = f"reminder_{user_id}"
        
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed reminder job for user {user_id}")
        except Exception:
            pass  # Job не существует
    
    async def _trigger_reminder(self, user_id: int) -> None:
        """Триггер напоминания — вызывает callback."""
        if self._send_reminder_callback:
            try:
                await self._send_reminder_callback(user_id)
                logger.info(f"Sent reminder to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user_id}: {e}")
        else:
            logger.warning("Reminder callback not set")
    
    async def restore_jobs_from_db(self) -> None:
        """
        Восстановить все jobs из базы данных при старте.
        Должен вызываться после инициализации БД и установки callback.
        """
        from bot.database import get_session, get_all_users_with_reminders
        
        async with get_session() as session:
            users = await get_all_users_with_reminders(session)
            
            for user in users:
                if user.reminder_time:
                    self.add_reminder_job(
                        user_id=user.id,
                        reminder_time=user.reminder_time,
                        timezone=user.timezone,
                    )
            
            logger.info(f"Restored {len(users)} reminder jobs from database")


# Глобальный экземпляр сервиса
scheduler_service = SchedulerService()
