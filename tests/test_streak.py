"""
Unit-тесты для расчёта streak.
"""
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

# Создаём mock LogStatus для тестов без импорта БД
class MockLogStatus:
    DONE = "done"
    NOT_DONE = "not_done"
    SKIPPED = "skipped"


class MockScheduleType:
    DAILY = "daily"
    WEEKLY = "weekly"


def create_mock_log(log_date: date, status: str):
    """Создать mock лога."""
    log = MagicMock()
    log.date = log_date
    log.status = status
    return log


# === Тесты для Daily Streak ===

class TestDailyStreak:
    """Тесты для расчёта daily streak."""
    
    def test_consecutive_done_streak(self):
        """Тест: последовательные done дают правильный streak."""
        from bot.services.streak import calculate_daily_streak
        from bot.database.models import LogStatus
        
        today = date(2024, 1, 15)
        logs = [
            create_mock_log(today - timedelta(days=2), LogStatus.DONE),
            create_mock_log(today - timedelta(days=1), LogStatus.DONE),
            create_mock_log(today, LogStatus.DONE),
        ]
        
        current, best = calculate_daily_streak(logs, today)
        
        assert current == 3
        assert best == 3
    
    def test_reset_on_not_done(self):
        """Тест: streak сбрасывается при not_done."""
        from bot.services.streak import calculate_daily_streak
        from bot.database.models import LogStatus
        
        today = date(2024, 1, 15)
        logs = [
            create_mock_log(today - timedelta(days=3), LogStatus.DONE),
            create_mock_log(today - timedelta(days=2), LogStatus.DONE),
            create_mock_log(today - timedelta(days=1), LogStatus.NOT_DONE),
            create_mock_log(today, LogStatus.DONE),
        ]
        
        current, best = calculate_daily_streak(logs, today)
        
        assert current == 1  # Только сегодня
        assert best == 2     # До not_done было 2
    
    def test_skipped_preserves_streak(self):
        """Тест: skipped не сбрасывает streak."""
        from bot.services.streak import calculate_daily_streak
        from bot.database.models import LogStatus
        
        today = date(2024, 1, 15)
        logs = [
            create_mock_log(today - timedelta(days=3), LogStatus.DONE),
            create_mock_log(today - timedelta(days=2), LogStatus.DONE),
            create_mock_log(today - timedelta(days=1), LogStatus.SKIPPED),
            create_mock_log(today, LogStatus.DONE),
        ]
        
        current, best = calculate_daily_streak(logs, today)
        
        assert current == 3  # skipped не прерывает
        assert best == 3
    
    def test_empty_logs(self):
        """Тест: пустой список логов даёт нулевой streak."""
        from bot.services.streak import calculate_daily_streak
        
        today = date(2024, 1, 15)
        logs = []
        
        current, best = calculate_daily_streak(logs, today)
        
        assert current == 0
        assert best == 0
    
    def test_no_today_log(self):
        """Тест: без отметки за сегодня streak продолжается с вчера."""
        from bot.services.streak import calculate_daily_streak
        from bot.database.models import LogStatus
        
        today = date(2024, 1, 15)
        logs = [
            create_mock_log(today - timedelta(days=2), LogStatus.DONE),
            create_mock_log(today - timedelta(days=1), LogStatus.DONE),
            # Сегодня нет отметки - streak продолжается (пользователь ещё не отметил)
        ]
        
        current, best = calculate_daily_streak(logs, today)
        
        # Streak продолжается с вчера (лучше для UX - утром видно streak)
        assert current == 2
        assert best == 2


# === Тесты для Weekly Streak ===

class TestWeeklyStreak:
    """Тесты для расчёта weekly streak."""
    
    def test_successful_weeks(self):
        """Тест: последовательные успешные недели."""
        from bot.services.streak import calculate_weekly_streak
        from bot.database.models import LogStatus
        
        # Создаём логи для 3 успешных недель (цель = 3 раза в неделю)
        # ISO недели 2024: неделя 3 (15-21 янв), неделя 2 (8-14 янв), неделя 1 (1-7 янв)
        today = date(2024, 1, 21)  # Воскресенье, неделя 3
        logs = []
        
        # Неделя 3 (текущая, 15-21 янв): 3 done
        logs.append(create_mock_log(date(2024, 1, 15), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 16), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 17), LogStatus.DONE))
        
        # Неделя 2 (8-14 янв): 3 done
        logs.append(create_mock_log(date(2024, 1, 8), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 9), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 10), LogStatus.DONE))
        
        # Неделя 1 (1-7 янв): 3 done
        logs.append(create_mock_log(date(2024, 1, 1), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 2), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 3), LogStatus.DONE))
        
        current, best = calculate_weekly_streak(logs, weekly_target=3, today=today)
        
        assert current == 3
        assert best == 3
    
    def test_failed_week_resets_streak(self):
        """Тест: неуспешная неделя сбрасывает streak."""
        from bot.services.streak import calculate_weekly_streak
        from bot.database.models import LogStatus
        
        today = date(2024, 1, 21)  # Воскресенье
        logs = []
        
        # Неделя 1 (этой неделя): 3 done - успешная
        logs.append(create_mock_log(date(2024, 1, 15), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 16), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 17), LogStatus.DONE))
        
        # Неделя 2 (прошлая): только 2 done - неуспешная при цели 3
        logs.append(create_mock_log(date(2024, 1, 8), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 9), LogStatus.DONE))
        
        current, best = calculate_weekly_streak(logs, weekly_target=3, today=today)
        
        assert current == 1  # Только текущая неделя
    
    def test_skipped_does_not_count_as_done(self):
        """Тест: skipped не считается как done."""
        from bot.services.streak import calculate_weekly_streak
        from bot.database.models import LogStatus
        
        today = date(2024, 1, 21)
        logs = []
        
        # 2 done + 1 skipped = только 2 done
        logs.append(create_mock_log(date(2024, 1, 15), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 16), LogStatus.DONE))
        logs.append(create_mock_log(date(2024, 1, 17), LogStatus.SKIPPED))
        
        current, best = calculate_weekly_streak(logs, weekly_target=3, today=today)
        
        # Неделя неуспешна (цель 3, выполнено 2)
        assert current == 0
    
    def test_empty_logs_weekly(self):
        """Тест: пустой список логов даёт нулевой weekly streak."""
        from bot.services.streak import calculate_weekly_streak
        
        today = date(2024, 1, 15)
        logs = []
        
        current, best = calculate_weekly_streak(logs, weekly_target=3, today=today)
        
        assert current == 0
        assert best == 0


# === Тесты для HabitStats ===

class TestHabitStats:
    """Тесты для получения полной статистики."""
    
    def test_stats_includes_7_30_days(self):
        """Тест: статистика включает done за 7 и 30 дней."""
        from bot.services.streak import get_habit_stats
        from bot.database.models import LogStatus, ScheduleType
        
        today = date(2024, 1, 31)
        logs = []
        
        # 5 done за последние 7 дней
        for i in range(5):
            logs.append(create_mock_log(today - timedelta(days=i), LogStatus.DONE))
        
        # Ещё 10 done за последние 30 дней (но не в последние 7)
        for i in range(8, 18):
            logs.append(create_mock_log(today - timedelta(days=i), LogStatus.DONE))
        
        stats = get_habit_stats(
            logs=logs,
            schedule_type=ScheduleType.DAILY,
            weekly_target=7,
            today=today,
        )
        
        assert stats.done_7_days == 5
        assert stats.done_30_days == 15
        assert stats.total_done == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
