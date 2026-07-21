# app/services/schedule_utils.py
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES_SHORT_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
_CLOSED_VALUES = ("выходной", "closed", "day off", "")

# Запись открыта на 2 месяца вперёд от сегодняшнего дня.
MAX_BOOKING_DAYS_AHEAD = 60


def format_working_hours_summary(working_hours_json: Optional[str]) -> str:
    """Человекочитаемая сводка режима работы салона из JSON вида
    {"mon": "10:00-20:00", ..., "sun": "closed"} — соседние дни с
    одинаковым режимом группируются («Пн–Пт 10:00–20:00, Сб–Вс выходной»).
    Пустой/битый JSON → нейтральный дефолт (как было раньше)."""
    default = "Пн–Вс: 10:00 — 21:00"
    if not working_hours_json:
        return default
    try:
        hours = json.loads(working_hours_json)
    except (ValueError, TypeError):
        return default
    if not isinstance(hours, dict):
        return default

    day_values = []
    for day in DAY_NAMES:
        raw = (hours.get(day) or "").strip().lower()
        day_values.append("выходной" if raw in _CLOSED_VALUES else raw.replace("-", "–"))

    groups: list[tuple[int, int, str]] = []  # (start_idx, end_idx, value)
    for i, value in enumerate(day_values):
        if groups and groups[-1][2] == value:
            groups[-1] = (groups[-1][0], i, value)
        else:
            groups.append((i, i, value))

    parts = []
    for start, end, value in groups:
        if start == end:
            days_label = DAY_NAMES_SHORT_RU[start]
        else:
            days_label = f"{DAY_NAMES_SHORT_RU[start]}–{DAY_NAMES_SHORT_RU[end]}"
        parts.append(f"{days_label} {value}")

    return ", ".join(parts) if parts else default


def get_salon_work_hours(
    working_hours_json: Optional[str], target_date: datetime
) -> Optional[Tuple[datetime, datetime]]:
    """
    Парсит Salon.working_hours (JSON вида {"mon": "09:00-21:00", "tue": "выходной", ...})
    и возвращает (work_start, work_end) для дня target_date, либо None — если
    график не задан/повреждён или салон в этот день не работает.
    """
    if not working_hours_json:
        return None
    try:
        working_hours = json.loads(working_hours_json)
    except (ValueError, TypeError):
        return None

    day_name = DAY_NAMES[target_date.weekday()]
    time_range = working_hours.get(day_name)
    if not time_range or time_range in ("выходной", "closed", "day off"):
        return None

    try:
        start_str, end_str = time_range.split("-")
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
    except (ValueError, AttributeError):
        return None

    work_start = target_date.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    work_end = target_date.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    return work_start, work_end


def is_within_booking_window(target_date: datetime) -> bool:
    """Дата не дальше MAX_BOOKING_DAYS_AHEAD дней от сегодня."""
    horizon = datetime.now().date() + timedelta(days=MAX_BOOKING_DAYS_AHEAD)
    return target_date.date() <= horizon


async def get_effective_work_hours(
    db: AsyncSession, salon, master_id: int, target_date: datetime
) -> Optional[Tuple[datetime, datetime]]:
    """Единая точка правды о доступности дня для записи: сочетает окно
    в 2 месяца, недельный график салона (get_salon_work_hours) и закрытые
    даты (ScheduleClosure — на весь салон или на конкретного мастера).
    None — в этот день записаться нельзя ни по какой из причин."""
    from app.models.models import ScheduleClosure  # локальный импорт — без цикла с models.py

    if not is_within_booking_window(target_date):
        return None

    hours = get_salon_work_hours(salon.working_hours, target_date)
    if hours is None:
        return None

    closed = await db.execute(
        select(ScheduleClosure.id).where(
            ScheduleClosure.salon_id == salon.id,
            ScheduleClosure.date == target_date.date(),
            (ScheduleClosure.master_id.is_(None)) | (ScheduleClosure.master_id == master_id),
        )
    )
    if closed.first() is not None:
        return None

    return hours
