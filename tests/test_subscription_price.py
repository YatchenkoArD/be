"""Регресс: цена с подпиской модели.

Баг (блок 10): subscription_expires_at — timestamptz (tz-aware), а сравнение
шло с наивным datetime.now() → TypeError при активной подписке. Проверяем, что
calculate_price отрабатывает без падения во всех ветках.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.booking_service import BookingService


def _service(price: int = 1000):
    return SimpleNamespace(price=price)


async def test_active_subscription_applies_discount():
    user = SimpleNamespace(
        subscription_tier="pro",  # 50%
        subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    # раньше здесь был TypeError (aware > naive)
    assert await BookingService.calculate_price(user, _service(1000)) == 500


async def test_expired_subscription_no_discount():
    user = SimpleNamespace(
        subscription_tier="premium",
        subscription_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    assert await BookingService.calculate_price(user, _service(1000)) == 1000


async def test_no_subscription_full_price():
    user = SimpleNamespace(subscription_tier=None, subscription_expires_at=None)
    assert await BookingService.calculate_price(user, _service(1000)) == 1000
