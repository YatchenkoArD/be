# tests/test_auth_yandex.py
"""Вход через Яндекс ID: state-CSRF, связка по проверенному номеру."""
import httpx
import pytest
from sqlalchemy import select

import app.api.v1.endpoints.auth_yandex as ya
import app.services.otp as otp_mod
from app.models.models import User
from tests.conftest import register_user

settings = otp_mod.settings  # тот же общий инстанс, что у приложения

PHONE = "+79996667788"


@pytest.fixture()
def yandex_on(monkeypatch):
    monkeypatch.setattr(settings, "YANDEX_OAUTH_ENABLED", True)
    monkeypatch.setattr(settings, "YANDEX_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "YANDEX_CLIENT_SECRET", "test-secret")


def _mock_yandex(monkeypatch, profile: dict | None, token_ok: bool = True):
    async def fake_exchange(code, redirect_uri):
        return "fake-token" if token_ok else None

    async def fake_profile(access_token):
        return profile

    monkeypatch.setattr(ya, "_exchange_code", fake_exchange)
    monkeypatch.setattr(ya, "_fetch_profile", fake_profile)


async def _start_and_get_state(client: httpx.AsyncClient) -> str:
    r = await client.get("/api/v1/auth/yandex/start")
    assert r.status_code == 302
    location = r.headers["location"]
    assert location.startswith("https://oauth.yandex.ru/authorize")
    from urllib.parse import parse_qs, urlparse

    return parse_qs(urlparse(location).query)["state"][0]


async def test_disabled_redirects_to_login(client):
    r = await client.get("/api/v1/auth/yandex/start")
    assert r.status_code == 302 and r.headers["location"] == "/login"


async def test_callback_rejects_unknown_state(client, yandex_on, monkeypatch):
    _mock_yandex(monkeypatch, {"default_phone": {"number": PHONE}})
    r = await client.get(
        "/api/v1/auth/yandex/callback", params={"code": "c", "state": "чужой"}
    )
    assert r.status_code == 302 and "error=yandex" in r.headers["location"]


async def test_new_user_created_from_verified_phone(client, db_session, yandex_on, monkeypatch):
    _mock_yandex(monkeypatch, {
        "id": "42", "default_phone": {"number": "79996667788"},
        "real_name": "Яндекс Пользователь",
    })
    state = await _start_and_get_state(client)
    r = await client.get(
        "/api/v1/auth/yandex/callback", params={"code": "c", "state": state}
    )
    assert r.status_code == 302 and r.headers["location"] == "/profile"
    assert "access_token" in r.cookies or "access_token" in r.headers.get("set-cookie", "")

    async with db_session() as db:
        user = (await db.execute(select(User).where(User.phone == PHONE))).scalar_one()
        assert user.full_name == "Яндекс Пользователь"
        assert user.role.value == "client"

    # state одноразовый: повтор с тем же state — отказ
    r = await client.get(
        "/api/v1/auth/yandex/callback", params={"code": "c", "state": state}
    )
    assert "error=yandex" in r.headers["location"]


async def test_existing_user_logged_in_by_phone(client, db_session, yandex_on, monkeypatch):
    data = await register_user(client, PHONE)
    _mock_yandex(monkeypatch, {"default_phone": {"number": "79996667788"}})
    state = await _start_and_get_state(client)
    r = await client.get(
        "/api/v1/auth/yandex/callback", params={"code": "c", "state": state}
    )
    assert r.status_code == 302 and r.headers["location"] == "/profile"

    async with db_session() as db:
        users = (await db.execute(select(User).where(User.phone == PHONE))).scalars().all()
        assert len(users) == 1  # вошли в существующий, дубль не создан
        assert users[0].id == data["user"]["id"]


async def test_no_phone_goes_to_register(client, yandex_on, monkeypatch):
    _mock_yandex(monkeypatch, {"id": "42", "default_email": "a@b.ru"})
    state = await _start_and_get_state(client)
    r = await client.get(
        "/api/v1/auth/yandex/callback", params={"code": "c", "state": state}
    )
    assert "register?error=yandex_no_phone" in r.headers["location"]
