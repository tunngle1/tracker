"""
Главный модуль бота - точка входа.
"""
import asyncio
import logging
from datetime import datetime

import pytz
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database import init_db, get_session, get_active_habits, get_user
from bot.database.models import LogStatus
from bot.handlers import (
    start_router,
    habits_router,
    tracking_router,
    stats_router,
    settings_router,
)
from bot.keyboards.inline import get_habits_tracking_keyboard
from bot.services.scheduler import scheduler_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def send_reminder(user_id: int) -> None:
    """
    Отправить напоминание пользователю.
    Эта функция вызывается планировщиком.
    """
    bot = scheduler_service._bot
    if bot is None:
        logger.error("Bot not set in scheduler service")
        return
    
    try:
        # Простое напоминание без запроса к БД для теста
        await bot.send_message(
            chat_id=user_id,
            text="🔔 <b>Напоминание!</b>\n\nНе забудь отметить привычки! Нажми «✅ Отметить сегодня»",
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"Sent reminder to user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to send reminder to user {user_id}: {e}")


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота."""
    logger.info("Bot starting...")
    
    # Инициализация БД
    await init_db()
    logger.info("Database initialized")
    
    # Настройка планировщика
    scheduler_service.set_bot(bot)
    scheduler_service.set_reminder_callback(send_reminder)
    scheduler_service.start()
    
    # Восстановление jobs из БД
    await scheduler_service.restore_jobs_from_db()
    
    logger.info("Bot started successfully!")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота."""
    logger.info("Bot stopping...")
    scheduler_service.shutdown()
    logger.info("Bot stopped")


async def main() -> None:
    """Главная функция запуска бота."""
    # Создаём бота
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    # Создаём dispatcher
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Регистрируем routers
    dp.include_router(start_router)
    dp.include_router(habits_router)
    dp.include_router(tracking_router)
    dp.include_router(stats_router)
    dp.include_router(settings_router)
    
    # Запускаем polling
    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
