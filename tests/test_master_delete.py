# tests/test_master_delete.py
"""Удаление мастера должно чистить RESTRICT-зависимости (Service/Schedule/
Booking/Favorite.master_id) — иначе db.delete(master) роняет 500."""
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.models import (
    User, UserRole, Salon, SalonMember, SalonRole, Master, Service,
    Booking, BookingStatus, Favorite,
)


async def _login_web(client, phone, password="Testpass1"):
    r = await client.post("/api/v1/auth/login-web", data={"phone": phone, "password": password})
    assert r.status_code == 302


async def _setup_master_with_deps(db_session) -> int:
    async with db_session() as db:
        salon = Salon(name="S", address="a", phone="+70000000070",
                      latitude=1.0, longitude=1.0, timezone="Europe/Moscow")
        db.add(salon)
        await db.commit()
        await db.refresh(salon)

        owner = User(phone="+79993330070", full_name="Owner",
                     hashed_password=get_password_hash("Testpass1"), role=UserRole.BUSINESS)
        muser = User(phone="+79993330071", full_name="Master",
                     hashed_password=get_password_hash("Testpass1"), role=UserRole.CLIENT)
        client_u = User(phone="+79993330072", full_name="Client",
                        hashed_password=get_password_hash("Testpass1"), role=UserRole.CLIENT)
        db.add_all([owner, muser, client_u])
        await db.commit()
        await db.refresh(owner)
        await db.refresh(muser)
        await db.refresh(client_u)

        db.add(SalonMember(salon_id=salon.id, user_id=owner.id, role=SalonRole.OWNER,
                           is_creator=True, permissions={"manage_masters": True}, is_active=True))
        master = Master(salon_id=salon.id, user_id=muser.id, specialization="Барбер")
        db.add(master)
        await db.commit()
        await db.refresh(master)

        svc = Service(master_id=master.id, name="Стрижка", price=1000, duration_minutes=60)
        db.add(svc)
        await db.commit()
        await db.refresh(svc)

        start = datetime.now() + timedelta(days=1)
        db.add(Booking(client_id=client_u.id, master_id=master.id, service_id=svc.id,
                       start_time=start, end_time=start + timedelta(minutes=60),
                       status=BookingStatus.PENDING, final_price=1000))
        db.add(Favorite(user_id=client_u.id, master_id=master.id))
        await db.commit()
        return master.id


async def test_delete_master_with_dependencies(client, db_session):
    """Мягкое удаление: не 500 на зависимостях; мастер скрыт, история цела."""
    master_id = await _setup_master_with_deps(db_session)
    await _login_web(client, "+79993330070")
    r = await client.post(f"/api/v1/master/{master_id}/delete")
    assert r.status_code == 302 and "deleted=1" in r.headers["location"], r.headers.get("location")
    async with db_session() as db:
        m = (await db.execute(select(Master).where(Master.id == master_id))).scalar_one()
        assert m.is_active is False  # скрыт, но не удалён физически
        # история сохранена: услуга и бронь на месте
        assert (await db.execute(select(Service).where(Service.master_id == master_id))).scalar_one_or_none() is not None
        assert (await db.execute(select(Booking).where(Booking.master_id == master_id))).scalar_one_or_none() is not None
        # и записаться к нему больше нельзя (исчез из записи)
        from app.api.v1.endpoints.bookings import _salon_bookable
        assert await _salon_bookable(db, master_id) is False
