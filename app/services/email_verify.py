# app/services/email_verify.py
"""Подтверждение смены email кодом, отправленным на НОВЫЙ адрес.

Тот же принцип, что у телефонного OTP (Redis TTL + хеш кода + лимит попыток,
см. [[app/services/otp.py]]), но канал — email: код уходит на новый адрес
через ARQ send_email, чем и подтверждается владение ящиком. Запись одноразовая.
"""
import hashlib
import secrets
import uuid

from app.core.config import settings
from app.core.limiter import get_redis
from app.core.worker import get_arq_pool


class EmailVerifyError(Exception):
    """Хранилище кодов недоступно или письмо не удалось поставить в очередь."""


def _norm(email: str) -> str:
    return (email or "").strip().lower()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _key(request_id: str) -> str:
    return f"email-otp:{request_id}"


async def send_email_code(email: str) -> dict:
    """Генерирует код, кладёт его хеш в Redis с TTL и шлёт письмо на новый адрес."""
    email = _norm(email)
    code = "".join(str(secrets.randbelow(10)) for _ in range(settings.OTP_LENGTH))
    request_id = str(uuid.uuid4())

    try:
        r = get_redis()
        key = _key(request_id)
        await r.hset(
            key,
            mapping={
                "email_hash": _hash(email),
                "code_hash": _hash(code + email),
                "attempts": 0,
            },
        )
        await r.expire(key, settings.OTP_TTL_MINUTES * 60)
    except Exception as e:
        raise EmailVerifyError(f"Хранилище кодов недоступно: {e}") from e

    try:
        pool = await get_arq_pool()
        await pool.enqueue_job(
            "send_email",
            email,
            "Код подтверждения email — Руми",
            f"Ваш код для смены email на rrumi.ru: {code}\n\n"
            f"Код действует {settings.OTP_TTL_MINUTES} минут. "
            "Если вы не меняли email — просто проигнорируйте это письмо.",
        )
    except Exception as e:
        raise EmailVerifyError(f"Не удалось отправить письмо: {e}") from e

    return {
        "request_id": request_id,
        "expires_in_seconds": settings.OTP_TTL_MINUTES * 60,
        # Код в открытом виде — ТОЛЬКО в mock и НИКОГДА в production
        # (вторая линия к guard'у: иначе код виден в ответе кому угодно).
        "dev_code": code
        if settings.EMAIL_MODE == "mock" and settings.ENVIRONMENT != "production"
        else None,
    }


async def verify_email_code(request_id: str, code: str, email: str) -> bool:
    """True, если код верный для этого адреса. Успех одноразовый (запись стёрта)."""
    email = _norm(email)
    try:
        r = get_redis()
        key = _key(request_id)
        record = await r.hgetall(key)
    except Exception as e:
        raise EmailVerifyError(f"Хранилище кодов недоступно: {e}") from e

    if not record or record.get("email_hash") != _hash(email):
        return False  # не найден, истёк по TTL или не тот адрес

    if int(record.get("attempts", 0)) >= settings.MAX_VERIFY_ATTEMPTS:
        await r.delete(key)
        return False

    if record.get("code_hash") == _hash(code + email):
        await r.delete(key)
        return True

    await r.hincrby(key, "attempts", 1)
    return False
