"""Блок 05: JSON-логи, маскирование ПДн, no-op Sentry без DSN."""
import json
import logging

from app.core import observability as obs


def test_mask_phones():
    assert obs._mask_phones("клиент +79991234567 записан") == "клиент +7********** записан"
    assert obs._mask_phones("нет номера") == "нет номера"
    assert obs._mask_phones(12345) == 12345  # не строка — как есть


def test_json_formatter_valid_and_masks():
    rec = logging.LogRecord("t", logging.INFO, __file__, 1,
                            "звонок +79990001122", None, None)
    line = obs.JsonLogFormatter().format(rec)
    data = json.loads(line)  # валидный JSON
    assert data["level"] == "INFO"
    assert data["logger"] == "t"
    assert data["msg"] == "звонок +7**********"
    assert "ts" in data


def test_json_formatter_includes_exception():
    try:
        raise ValueError("boom +79990001122")
    except ValueError:
        import sys
        rec = logging.LogRecord("t", logging.ERROR, __file__, 1, "упало", None,
                                sys.exc_info())
    data = json.loads(obs.JsonLogFormatter().format(rec))
    assert "exc" in data and "ValueError" in data["exc"]


def test_before_send_scrubs_pii():
    event = {
        "logentry": {"message": "сбой у +79991112233"},
        "exception": {"values": [{"value": "no user +79994445566"}]},
    }
    out = obs._before_send(event, None)
    assert out["logentry"]["message"] == "сбой у +7**********"
    assert out["exception"]["values"][0]["value"] == "no user +7**********"


def test_init_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.setattr(obs.settings, "SENTRY_DSN", "")
    obs._sentry_inited = False
    obs.init_sentry()  # не должно бросать и не должно инициализировать
    assert obs._sentry_inited is False
