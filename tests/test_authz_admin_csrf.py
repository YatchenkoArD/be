# tests/test_authz_admin_csrf.py
"""Права: админ-эндпоинты только для роли ADMIN (cookie), CSRF по Origin."""
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.models import User, UserRole
from tests.conftest import register_user

ADMIN_PHONE = "+79995550301"
CLIENT_PHONE = "+79995550302"
VICTIM_PHONE = "+79995550303"


async def _make_admin(db_session, phone: str = ADMIN_PHONE) -> User:
    async with db_session() as db:
        admin = User(
            phone=phone,
            full_name="Тест Админ",
            hashed_password=get_password_hash("Adminpass1"),
            role=UserRole.ADMIN,
            # Смена роли пользователя — действие старшего модератора
            # (see app/api/v1/endpoints/admin.py: _get_senior_admin).
            is_senior_admin=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return admin


async def _login_cookie(client, phone: str, password: str) -> None:
    r = await client.post("/api/v1/auth/login", json={"phone": phone, "password": password})
    assert r.status_code == 200, r.text
    client.cookies.set("access_token", r.json()["access_token"])


async def test_admin_can_change_role(client, db_session):
    await _make_admin(db_session)
    victim = await register_user(client, VICTIM_PHONE)
    await _login_cookie(client, ADMIN_PHONE, "Adminpass1")

    r = await client.post(
        f"/api/v1/admin/users/{victim['user']['id']}/role", data={"role": "business"}
    )
    assert r.status_code == 302 and "ok=" in r.headers["location"]

    async with db_session() as db:
        target = (await db.execute(select(User).where(User.phone == VICTIM_PHONE))).scalar_one()
        assert target.role == UserRole.BUSINESS


async def test_client_cannot_use_admin_endpoints(client, db_session):
    """Обычный клиент с валидной cookie получает redirect на /login, а не действие."""
    victim = await register_user(client, VICTIM_PHONE)
    await register_user(client, CLIENT_PHONE, password="Clientpass1")
    await _login_cookie(client, CLIENT_PHONE, "Clientpass1")

    r = await client.post(
        f"/api/v1/admin/users/{victim['user']['id']}/role", data={"role": "admin"}
    )
    assert r.status_code == 302 and r.headers["location"].startswith("/login")

    async with db_session() as db:
        target = (await db.execute(select(User).where(User.phone == VICTIM_PHONE))).scalar_one()
        assert target.role == UserRole.CLIENT  # роль не изменилась


async def test_admin_cannot_demote_self(client, db_session):
    admin = await _make_admin(db_session)
    await _login_cookie(client, ADMIN_PHONE, "Adminpass1")
    r = await client.post(f"/api/v1/admin/users/{admin.id}/role", data={"role": "client"})
    assert r.status_code == 302 and "err=" in r.headers["location"]


async def test_csrf_blocks_foreign_origin(client, db_session):
    """Cookie-мутация с чужим Origin режется middleware'ом (403)."""
    await _make_admin(db_session)
    await _login_cookie(client, ADMIN_PHONE, "Adminpass1")
    r = await client.post(
        "/api/v1/admin/users/1/role",
        data={"role": "business"},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


async def test_csrf_blocks_missing_origin_and_referer(client, db_session):
    await _make_admin(db_session)
    await _login_cookie(client, ADMIN_PHONE, "Adminpass1")
    # убираем дефолтный Origin клиента; Referer тоже не шлём
    r = await client.post(
        "/api/v1/admin/users/1/role",
        data={"role": "business"},
        headers={"Origin": ""},
    )
    assert r.status_code == 403
