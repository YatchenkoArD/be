# app/services/otp_client.py
"""Клиент отдельного микросервиса otp-service (см. его README про деплой)."""
import httpx

from app.core.config import settings


class OTPServiceError(Exception):
    """otp-service недоступен или ответил ошибкой."""


def _mask_phone(phone: str) -> str:
    return phone[:-4] + "**" + phone[-2:] if len(phone) > 6 else phone


async def send_code(phone: str) -> dict:
    """Просит otp-service отправить код и возвращает {request_id, masked_phone, expires_in_seconds}."""
    if not settings.OTP_ENABLED:
        # Временный обход (см. Settings.OTP_ENABLED) — SMS/otp-service ещё не подключены.
        return {"request_id": "otp-disabled", "masked_phone": _mask_phone(phone), "expires_in_seconds": 600}

    url = f"{settings.OTP_SERVICE_URL}/api/v1/otp/send"
    headers = {"Authorization": f"Bearer {settings.OTP_SERVICE_API_KEY}"}
    payload = {"phone": phone, "method": settings.OTP_METHOD}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as e:
        raise OTPServiceError(f"otp-service недоступен: {e}") from e

    if response.status_code != 200:
        raise OTPServiceError(f"otp-service вернул {response.status_code}: {response.text}")

    return response.json()


async def verify_code(request_id: str, code: str, phone: str) -> bool:
    """Возвращает True, если код верный и ещё не был использован."""
    if not settings.OTP_ENABLED:
        # Временный обход (см. Settings.OTP_ENABLED) — SMS/otp-service ещё не подключены.
        return True

    url = f"{settings.OTP_SERVICE_URL}/api/v1/otp/verify"
    headers = {"Authorization": f"Bearer {settings.OTP_SERVICE_API_KEY}"}
    payload = {"request_id": request_id, "code": code, "phone": phone}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as e:
        raise OTPServiceError(f"otp-service недоступен: {e}") from e

    if response.status_code == 404 or response.status_code == 400:
        return False
    if response.status_code != 200:
        raise OTPServiceError(f"otp-service вернул {response.status_code}: {response.text}")

    return response.json().get("valid", False)
