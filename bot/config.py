"""
Конфигурация бота.
Загружает настройки из переменных окружения.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Конфигурация приложения."""
    bot_token: str
    database_url: str
    default_timezone: str
    
    # Популярные таймзоны для быстрого выбора
    popular_timezones: tuple = (
        "Europe/Moscow",
        "Europe/Kiev",
        "Europe/Minsk",
        "Asia/Almaty",
        "Asia/Yekaterinburg",
    )
    
    # Лимиты валидации
    max_habit_name_length: int = 50
    min_weekly_target: int = 1
    max_weekly_target: int = 7


def get_config() -> Config:
    """Получить конфигурацию из переменных окружения."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN не задан в .env файле")
    
    return Config(
        bot_token=bot_token,
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./habits.db"),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow"),
    )


config = get_config()
