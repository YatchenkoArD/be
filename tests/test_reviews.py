# tests/test_reviews.py
"""Отзывы: оставить может только тот, у кого есть COMPLETED-запись к этому
мастеру/в этом салоне через Руми — сервер проверяет это сам (не веря
клиенту на слово) и без неё отклоняет создание (403). Один отзыв на пару
клиент-цель (мастер/салон/сотрудник)."""
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.models import (
    Booking, BookingStatus, Master, Review, Salon, Service, User, UserRole,
)
from tests.conftest import register_user

CLIENT_PHONE = "+79995550401"


async def _make_salon_master_service(db_session):
    async with db_session() as db:
        master_user = User(
            phone="+79995550499", full_name="Мастер Тест",
            hashed_password=get_password_hash("Masterpass1"), role=UserRole.MASTER,
        )
        db.add(master_user)
        await db.flush()
        salon = Salon(
            name="Тест-салон", address="ул. Тестовая, 1",
            latitude=55.75, longitude=37.61, phone="+70000000000",
        )
        db.add(salon)
        await db.flush()
        master = Master(user_id=master_user.id, salon_id=salon.id, specialization="Ногти")
        db.add(master)
        await db.flush()
        service = Service(master_id=master.id, name="Маникюр", price=1500, duration_minutes=60)
        db.add(service)
        await db.commit()
        return salon.id, master.id, service.id


async def _add_booking(db_session, client_id, master_id, service_id, status):
    async with db_session() as db:
        start = datetime(2026, 7, 1, 12, 0)
        db.add(Booking(
            client_id=client_id, master_id=master_id, service_id=service_id,
            start_time=start, end_time=start + timedelta(hours=1),
            status=status, final_price=1500,
        ))
        await db.commit()


async def _login_cookie(client, phone, password="Testpass1"):
    r = await client.post("/api/v1/auth/login", json={"phone": phone, "password": password})
    client.cookies.set("access_token", r.json()["access_token"])


async def test_review_without_booking_is_rejected(client, db_session):
    salon_id, master_id, _svc = await _make_salon_master_service(db_session)
    await register_user(client, CLIENT_PHONE)
    await _login_cookie(client, CLIENT_PHONE)

    r = await client.post(
        "/api/v1/reviews/create",
        data={"master_id": master_id, "salon_id": salon_id, "rating": 5, "comment": "не был, но пишу"},
    )
    assert r.status_code == 403

    async with db_session() as db:
        reviews = (await db.execute(select(Review))).scalars().all()
        assert len(reviews) == 0


async def test_pending_booking_is_not_enough_for_verification(client, db_session):
    salon_id, master_id, svc_id = await _make_salon_master_service(db_session)
    user = await register_user(client, CLIENT_PHONE)
    await _add_booking(db_session, user["user"]["id"], master_id, svc_id, BookingStatus.PENDING)
    await _login_cookie(client, CLIENT_PHONE)

    r = await client.post(
        "/api/v1/reviews/create",
        data={"master_id": master_id, "salon_id": salon_id, "rating": 5, "comment": ""},
    )
    assert r.status_code == 403  # PENDING — не завершённый визит, не подтверждает

    async with db_session() as db:
        reviews = (await db.execute(select(Review))).scalars().all()
        assert len(reviews) == 0


async def test_review_after_completed_booking_and_only_once(client, db_session):
    salon_id, master_id, svc_id = await _make_salon_master_service(db_session)
    user = await register_user(client, CLIENT_PHONE)
    await _add_booking(db_session, user["user"]["id"], master_id, svc_id, BookingStatus.COMPLETED)
    await _login_cookie(client, CLIENT_PHONE)

    payload = {"master_id": master_id, "salon_id": salon_id, "rating": 5, "comment": "отлично"}
    r = await client.post("/api/v1/reviews/create", data=payload)
    assert r.status_code == 302 and "reviewed=1" in r.headers["location"]

    async with db_session() as db:
        reviews = (await db.execute(select(Review))).scalars().all()
        assert len(reviews) == 1
        assert reviews[0].is_verified is True  # COMPLETED-запись — реальный визит подтверждён

    # второй отзыв на ту же пару клиент-мастер — запрещён (409 Conflict)
    r = await client.post("/api/v1/reviews/create", data=payload)
    assert r.status_code == 409

    async with db_session() as db:
        reviews = (await db.execute(select(Review))).scalars().all()
        assert len(reviews) == 1


async def test_review_requires_auth(client, db_session):
    salon_id, master_id, _svc = await _make_salon_master_service(db_session)
    r = await client.post(
        "/api/v1/reviews/create",
        data={"master_id": master_id, "salon_id": salon_id, "rating": 5, "comment": ""},
    )
    assert r.status_code == 302 and r.headers["location"] == "/login"
