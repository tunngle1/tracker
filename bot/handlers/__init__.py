# Handlers package
from bot.handlers.start import router as start_router
from bot.handlers.habits import router as habits_router
from bot.handlers.tracking import router as tracking_router
from bot.handlers.stats import router as stats_router
from bot.handlers.settings import router as settings_router

__all__ = [
    "start_router",
    "habits_router",
    "tracking_router",
    "stats_router",
    "settings_router",
]
