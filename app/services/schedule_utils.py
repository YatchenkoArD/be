# app/services/schedule_utils.py
import json
from datetime import datetime
from typing import Optional, Tuple

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


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
