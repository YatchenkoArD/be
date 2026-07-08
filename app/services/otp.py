# app/services/otp.py
"""Подтверждение телефона кодом (SMS/flash-call).

Код и его состояние живут только в Redis (TTL) — «положили, сравнили,
стёрли», отдельная БД/сервис для этого не нужны. Ранее логика была вынесена
в отдельный микросервис (otp-service); при единственном потребителе (это
приложение) лишний контейнер/БД/секрет только добавляли точку отказа, без
выигрыша в изоляции — поэтому код вернулся внутрь.
"""
import hashlib
import secrets
import uuid

from app.core.config import settings
from app.core.limiter import get_redis
from app.services.sms_provider import send_otp_code


class OTPError(Exception):
    """Хранилище кодов недоступно или код не удалось отправить."""


def _mask_phone(phone: str) -> str:
    return phone[:-4] + "**" + phone[-2:] if len(phone) > 6 else phone


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _key(request_id: str) -> str:
    return f"otp:{request_id}"


async def send_code(phone: str) -> dict:
    """Генерирует код, кладёт его хеш в Redis с TTL и отправляет через SMS-провайдер."""
    if not settings.OTP_ENABLED:
        # Временный обход (см. Settings.OTP_ENABLED) — провайдер ещё не подключён.
        return {
            "request_id": "otp-disabled",
            "masked_phone": _mask_phone(phone),
            "expires_in_seconds": settings.OTP_TTL_MINUTES * 60,
        }

    code = "".join(str(secrets.randbelow(10)) for _ in range(settings.OTP_LENGTH))
    request_id = str(uuid.uuid4())

    try:
        r = get_redis()
        key = _key(request_id)
        await r.hset(
            key,
            mapping={
                "phone_hash": _hash(phone),
                "code_hash": _hash(code + phone),
                "attempts": 0,
            },
        )
        await r.expire(key, settings.OTP_TTL_MINUTES * 60)
    except Exception as e:
        raise OTPError(f"Хранилище кодов недоступно: {e}") from e

    if not await send_otp_code(phone, code, settings.OTP_METHOD):
        raise OTPError("Не удалось отправить код")

    return {
        "request_id": request_id,
        "masked_phone": _mask_phone(phone),
        "expires_in_seconds": settings.OTP_TTL_MINUTES * 60,
        # Код в открытом виде — ТОЛЬКО в mock-режиме и НИКОГДА в production
        # (вторая линия к guard'у в config: иначе код на чужой номер получает
        # любой, кто его запросил). Для разработки/smoke-тестов.
        "dev_code": code
        if settings.SMS_MODE == "mock" and settings.ENVIRONMENT != "production"
        else None,
    }


async def verify_code(request_id: str, code: str, phone: str) -> bool:
    """True, если код верный, не истёк и не превышены попытки.

    Успешная проверка одноразовая — запись сразу удаляется из Redis.
    """
    if not settings.OTP_ENABLED:
        return True

    try:
        r = get_redis()
        key = _key(request_id)
        record = await r.hgetall(key)
    except Exception as e:
        raise OTPError(f"Хранилище кодов недоступно: {e}") from e

    if not record or record.get("phone_hash") != _hash(phone):
        return False  # не найден, истёк по TTL или не тот номер

    if int(record.get("attempts", 0)) >= settings.MAX_VERIFY_ATTEMPTS:
        await r.delete(key)
        return False

    if record.get("code_hash") == _hash(code + phone):
        await r.delete(key)
        return True

    await r.hincrby(key, "attempts", 1)
    return False
