from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from app.core.config import settings


def get_salon_time(salon_timezone: Optional[str] = None) -> datetime:
    """Текущее время в часовом поясе салона (дефолт — зона продукта)."""
    return datetime.now(ZoneInfo(salon_timezone or settings.DEFAULT_TIMEZONE))


def localize_time(naive_dt: datetime, salon_timezone: Optional[str] = None) -> datetime:
    """Привязать наивное время к часовому поясу салона."""
    return naive_dt.replace(tzinfo=ZoneInfo(salon_timezone or settings.DEFAULT_TIMEZONE))
