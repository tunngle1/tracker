"""
Сервис расчёта streak (серии) для привычек.

Правила:
- Daily: streak увеличивается, если сегодня done. Если вчера not_done — сброс. skipped не сбрасывает.
- Weekly N: неделя успешна, если done >= N. streak = успешные недели подряд. skipped не штрафует.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Sequence

from bot.database.models import HabitLog, LogStatus, ScheduleType


@dataclass
class HabitStats:
    """Статистика привычки."""
    current_streak: int
    best_streak: int
    done_7_days: int
    done_30_days: int
    total_done: int


def calculate_daily_streak(logs: Sequence[HabitLog], today: date) -> tuple[int, int]:
    """
    Рассчитать текущий и лучший streak для daily привычки.
    
    Args:
        logs: Список логов привычки (отсортированный по дате)
        today: Текущая дата в TZ пользователя
    
    Returns:
        (current_streak, best_streak)
    """
    if not logs:
        return 0, 0
    
    # Преобразуем в dict для быстрого доступа
    log_by_date: Dict[date, LogStatus] = {log.date: log.status for log in logs}
    
    current_streak = 0
    best_streak = 0
    streak = 0
    
    # Идём от сегодня назад
    check_date = today
    
    # Проверяем текущий streak
    while True:
        status = log_by_date.get(check_date)
        
        if status == LogStatus.DONE:
            streak += 1
            check_date -= timedelta(days=1)
        elif status == LogStatus.SKIPPED:
            # Skipped не ломает streak, продолжаем проверять
            check_date -= timedelta(days=1)
        elif status == LogStatus.NOT_DONE:
            # Not done — сброс
            break
        else:
            # Нет записи — если это не сегодня, считаем что не делали
            if check_date < today:
                break
            # Сегодня ещё не отметили — проверяем вчера
            check_date -= timedelta(days=1)
    
    current_streak = streak
    
    # Рассчитываем лучший streak по всем логам
    sorted_logs = sorted(logs, key=lambda x: x.date)
    streak = 0
    prev_date = None
    
    for log in sorted_logs:
        if log.status == LogStatus.DONE:
            if prev_date is None:
                streak = 1
            elif log.date == prev_date + timedelta(days=1):
                streak += 1
            elif log.date == prev_date:
                pass  # Та же дата
            else:
                # Проверяем, были ли пропущенные дни только skipped
                gap_ok = True
                for i in range(1, (log.date - prev_date).days):
                    gap_date = prev_date + timedelta(days=i)
                    gap_status = log_by_date.get(gap_date)
                    if gap_status != LogStatus.SKIPPED:
                        gap_ok = False
                        break
                
                if gap_ok:
                    streak += 1
                else:
                    streak = 1
            
            prev_date = log.date
            best_streak = max(best_streak, streak)
        elif log.status == LogStatus.SKIPPED:
            # Skipped не прерывает серию, но и не увеличивает
            if prev_date is not None:
                prev_date = log.date
        else:  # NOT_DONE
            streak = 0
            prev_date = None
    
    return current_streak, best_streak


def calculate_weekly_streak(
    logs: Sequence[HabitLog],
    weekly_target: int,
    today: date,
) -> tuple[int, int]:
    """
    Рассчитать текущий и лучший streak для weekly привычки.
    
    Args:
        logs: Список логов привычки
        weekly_target: Сколько раз в неделю нужно выполнить
        today: Текущая дата в TZ пользователя
    
    Returns:
        (current_streak, best_streak)
    """
    if not logs:
        return 0, 0
    
    # Группируем по неделям (ISO неделя)
    weeks: Dict[tuple, List[LogStatus]] = {}
    
    for log in logs:
        week_key = (log.date.isocalendar()[0], log.date.isocalendar()[1])
        if week_key not in weeks:
            weeks[week_key] = []
        weeks[week_key].append(log.status)
    
    # Проверяем, успешна ли неделя
    def is_week_success(statuses: List[LogStatus]) -> bool:
        done_count = sum(1 for s in statuses if s == LogStatus.DONE)
        return done_count >= weekly_target
    
    # Получаем все недели в порядке
    sorted_weeks = sorted(weeks.keys())
    
    if not sorted_weeks:
        return 0, 0
    
    # Рассчитываем текущий streak (идём от текущей недели назад)
    current_streak = 0
    current_week = (today.isocalendar()[0], today.isocalendar()[1])
    
    check_week = current_week
    while check_week in weeks:
        if is_week_success(weeks[check_week]):
            current_streak += 1
            check_week = get_previous_week(check_week)
        else:
            break
    
    # Рассчитываем лучший streak (последовательные успешные недели)
    best_streak = 0
    streak = 0
    
    for i, week in enumerate(sorted_weeks):
        if is_week_success(weeks[week]):
            if i == 0:
                streak = 1
            else:
                prev_week = sorted_weeks[i - 1]
                expected_prev = get_previous_week(week)
                if prev_week == expected_prev and is_week_success(weeks[prev_week]):
                    streak += 1
                else:
                    streak = 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0
    
    return current_streak, best_streak


def get_previous_week(week: tuple) -> tuple:
    """Получить предыдущую ISO неделю."""
    year, week_num = week
    if week_num == 1:
        # Последняя неделя предыдущего года
        prev_year = year - 1
        # Получаем последнюю неделю года
        last_day = date(prev_year, 12, 31)
        return (prev_year, last_day.isocalendar()[1])
    return (year, week_num - 1)


def get_next_week(week: tuple) -> tuple:
    """Получить следующую ISO неделю."""
    year, week_num = week
    # Получаем последнюю неделю года
    last_day = date(year, 12, 31)
    max_week = last_day.isocalendar()[1]
    
    if week_num >= max_week:
        return (year + 1, 1)
    return (year, week_num + 1)


def get_habit_stats(
    logs: Sequence[HabitLog],
    schedule_type: ScheduleType,
    weekly_target: int,
    today: date,
) -> HabitStats:
    """
    Получить полную статистику привычки.
    
    Args:
        logs: Список логов привычки
        schedule_type: Тип расписания (daily/weekly)
        weekly_target: Цель для weekly (игнорируется для daily)
        today: Текущая дата в TZ пользователя
    
    Returns:
        HabitStats с текущим streak, лучшим streak, done за 7/30 дней
    """
    if schedule_type == ScheduleType.DAILY:
        current_streak, best_streak = calculate_daily_streak(logs, today)
    else:
        current_streak, best_streak = calculate_weekly_streak(logs, weekly_target, today)
    
    # Считаем done за 7 и 30 дней
    done_7_days = 0
    done_30_days = 0
    total_done = 0
    
    for log in logs:
        if log.status == LogStatus.DONE:
            total_done += 1
            days_ago = (today - log.date).days
            if days_ago <= 7:
                done_7_days += 1
            if days_ago <= 30:
                done_30_days += 1
    
    return HabitStats(
        current_streak=current_streak,
        best_streak=best_streak,
        done_7_days=done_7_days,
        done_30_days=done_30_days,
        total_done=total_done,
    )
