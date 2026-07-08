# app/services/sms_provider.py
"""Отправка кода подтверждения: SMSC.ru (осн., SMS + flash-call), резерв —
SMS.ru (только SMS). SMS_MODE=mock — код никуда не уходит, виден в логе и
в dev_code ответа /send-code (для разработки и до подключения провайдера).
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _mask_phone(phone: str) -> str:
    # Живые логи не должны быть вторым хранилищем номеров (152-ФЗ)
    return phone[:-4] + "**" + phone[-2:] if len(phone) > 6 else phone


class BaseSMSProvider:
    async def send(self, phone: str, code: str, method: str) -> bool:
        raise NotImplementedError


class MockProvider(BaseSMSProvider):
    async def send(self, phone: str, code: str, method: str) -> bool:
        logger.info("MOCK %s -> %s CODE=%s", method.upper(), phone, code)
        return True


class SMSCProvider(BaseSMSProvider):
    """SMSC.ru — SMS и flash-call (звонок, код = последние цифры номера)."""

    async def send(self, phone: str, code: str, method: str) -> bool:
        phone_clean = phone.lstrip("+")
        url = "https://smsc.ru/sys/send.php"

        if method == "flash_call":
            params = {
                "login": settings.SMSC_LOGIN,
                "psw": settings.SMSC_PASSWORD,
                "phones": phone_clean,
                "call": 1,
                "fmt": 3,
            }
        else:
            params = {
                "login": settings.SMSC_LOGIN,
                "psw": settings.SMSC_PASSWORD,
                "phones": phone_clean,
                "mes": f"Код подтверждения: {code}",
                "sender": settings.SMSC_SENDER_ID,
                "fmt": 3,
            }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, data=params)
                data = response.json()
                if "error" in data:
                    logger.error("SMSC error: %s", data)
                    return False
                logger.info("SMSC: %s отправлен на %s", method, _mask_phone(phone))
                return True
        except Exception:
            logger.exception("SMSC request failed")
            return False


class SMSRuProvider(BaseSMSProvider):
    """SMS.ru — резервный канал (только SMS, без flash-call)."""

    async def send(self, phone: str, code: str, method: str) -> bool:
        phone_clean = phone.lstrip("+")
        url = "https://sms.ru/sms/send"
        params = {
            "api_id": settings.SMSRU_API_ID,
            "to": phone_clean,
            "msg": f"Код подтверждения: {code}",
            "json": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params)
                data = response.json()
                if data.get("status") != "OK":
                    logger.error("SMS.ru error: %s", data)
                    return False
                logger.info("SMS.ru: SMS отправлен на %s", _mask_phone(phone))
                return True
        except Exception:
            logger.exception("SMS.ru request failed")
            return False


async def send_otp_code(phone: str, code: str, method: str) -> bool:
    """Отправляет код через основной канал, при сбое SMS — через резервный."""
    if settings.SMS_MODE == "mock":
        return await MockProvider().send(phone, code, method)

    if await SMSCProvider().send(phone, code, method):
        return True

    if method == "sms":
        logger.warning("SMSC недоступен, пробуем SMS.ru")
        return await SMSRuProvider().send(phone, code, method)

    return False
