"""Модерация жалоб на фото из админ-панели: resolve (удалить фото) / dismiss."""
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.models import (
    User, UserRole, Salon, SalonModerationStatus, Master, MasterPhoto,
    PhotoReport, PhotoReportStatus,
)

ADMIN_PHONE = "+79995552001"


async def _setup_report(db_session):
    """Создаёт салон+мастера+фото+жалобу, возвращает id жалобы и id фото."""
    async with db_session() as db:
        owner = User(phone="+79995552010", full_name="В",
                     hashed_password=get_password_hash("Pw1passw"), role=UserRole.BUSINESS)
        reporter = User(phone="+79995552011", full_name="Ж",
                        hashed_password=get_password_hash("Pw1passw"), role=UserRole.CLIENT)
        mu = User(phone="+79995552012", full_name="М",
                  hashed_password=get_password_hash("Pw1passw"), role=UserRole.CLIENT)
        db.add_all([owner, reporter, mu])
        await db.commit()
        salon = Salon(name="С", description="", address="Т", latitude=56.5, longitude=84.9,
                      phone="+79990000000", rating=0.0, reviews_count=0, is_active=True,
                      moderation_status=SalonModerationStatus.APPROVED, creator_id=owner.id)
        db.add(salon)
        await db.commit()
        master = Master(user_id=mu.id, salon_id=salon.id, specialization="м")
        db.add(master)
        await db.commit()
        photo = MasterPhoto(master_id=master.id, url="/x.jpg")  # НЕ /uploads/ → без delete_stored
        db.add(photo)
        await db.commit()
        rep = PhotoReport(master_photo_id=photo.id, reporter_id=reporter.id, reason="плохое")
        db.add(rep)
        await db.commit()
        return rep.id, photo.id


async def _admin_login(client, db_session):
    async with db_session() as db:
        db.add(User(phone=ADMIN_PHONE, full_name="А",
                    hashed_password=get_password_hash("Adminpass1"), role=UserRole.ADMIN))
        await db.commit()
    r = await client.post("/api/v1/auth/login", json={"phone": ADMIN_PHONE, "password": "Adminpass1"})
    client.cookies.set("access_token", r.json()["access_token"])


async def test_admin_resolve_deletes_photo(client, db_session):
    rid, pid = await _setup_report(db_session)
    await _admin_login(client, db_session)
    r = await client.post(f"/api/v1/admin/reports/{rid}/resolve")
    assert r.status_code == 302 and "ok=" in r.headers["location"]
    async with db_session() as db:
        rep = (await db.execute(select(PhotoReport).where(PhotoReport.id == rid))).scalar_one()
        assert rep.status == PhotoReportStatus.RESOLVED
        assert (await db.execute(select(MasterPhoto).where(MasterPhoto.id == pid))).scalar_one_or_none() is None


async def test_admin_dismiss_keeps_photo(client, db_session):
    rid, pid = await _setup_report(db_session)
    await _admin_login(client, db_session)
    r = await client.post(f"/api/v1/admin/reports/{rid}/dismiss")
    assert r.status_code == 302
    async with db_session() as db:
        rep = (await db.execute(select(PhotoReport).where(PhotoReport.id == rid))).scalar_one()
        assert rep.status == PhotoReportStatus.DISMISSED
        assert (await db.execute(select(MasterPhoto).where(MasterPhoto.id == pid))).scalar_one_or_none() is not None
