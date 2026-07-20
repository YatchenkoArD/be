"""Мониторинг и логи (блок 05): Sentry/GlitchTip + структурные JSON-логи.

Оба слоя включаются через окружение и по умолчанию НЕ меняют поведение:
- ``SENTRY_DSN`` пуст → ``sentry_sdk`` не инициализируется (полный no-op);
- ``LOG_FORMAT=text`` (дефолт) → привычные текстовые логи; ``json`` → по
  строке-JSON на событие (удобно для сбора в проде).

Телефоны — ПДн (152-ФЗ), поэтому маскируем их и в логах, и в телеметрии,
уходящей в GlitchTip.
"""
import json
import logging
import re
import sys
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger("observability")

# +7XXXXXXXXXX → маскируем в исходящей телеметрии и JSON-логах.
_PHONE_RE = re.compile(r"\+7\d{10}")


def _mask_phones(text):
    return _PHONE_RE.sub("+7**********", text) if isinstance(text, str) else text


class JsonLogFormatter(logging.Formatter):
    """Одно событие лога = одна строка JSON (для агрегации в проде)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": _mask_phones(record.getMessage()),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_logging_configured = False


def setup_logging() -> None:
    """Единая настройка корневого логгера (идемпотентна)."""
    global _logging_configured
    if _logging_configured:
        return
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT.lower() == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    _logging_configured = True


def _before_send(event, hint):
    """Не выпускаем ПДн наружу: маскируем телефоны в сообщении и исключениях."""
    try:
        entry = event.get("logentry")
        if entry and entry.get("message"):
            entry["message"] = _mask_phones(entry["message"])
        for exc in (event.get("exception") or {}).get("values", []):
            if exc.get("value"):
                exc["value"] = _mask_phones(exc["value"])
    except Exception:  # телеметрия не должна ронять приложение
        pass
    return event


_sentry_inited = False


def init_sentry() -> None:
    """Инициализировать Sentry/GlitchTip, если задан DSN (иначе no-op)."""
    global _sentry_inited
    if _sentry_inited or not settings.SENTRY_DSN:
        return
    import sentry_sdk  # локальный импорт: без DSN пакет вообще не нужен

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # send_default_pii=False: НЕ слать cookie/заголовки/тело запроса/IP.
        send_default_pii=False,
        before_send=_before_send,
    )
    _sentry_inited = True
    logger.info("Sentry/GlitchTip включён (env=%s, release=%s)",
                settings.ENVIRONMENT, settings.VERSION)
