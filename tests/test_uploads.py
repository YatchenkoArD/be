# tests/test_uploads.py
"""Загрузка фото: валидация по содержимому, пересохранение, права."""
import io

import httpx
import pytest
from PIL import Image
from sqlalchemy import select

import app.services.uploads as uploads_mod
from app.models.models import SalonPhoto, User
from tests.conftest import register_user

PHONE = "+79994445566"


def _jpeg_bytes(size=(800, 600), color=(200, 120, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _tmp_uploads(tmp_path, monkeypatch):
    """Каждому тесту — свой каталог хранилища, репо не засоряем."""
    monkeypatch.setattr(uploads_mod.settings, "UPLOADS_DIR", str(tmp_path))
    yield tmp_path


async def _auth_client(client: httpx.AsyncClient) -> dict:
    data = await register_user(client, PHONE)
    client.headers["Authorization"] = f"Bearer {data['access_token']}"
    return data


async def test_avatar_upload_reencodes_and_saves(client, db_session, _tmp_uploads):
    await _auth_client(client)
    r = await client.post(
        "/api/v1/upload/avatar",
        files={"file": ("selfie.jpg", _jpeg_bytes((3000, 2000)), "image/jpeg")},
    )
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith("/uploads/avatars/") and url.endswith(".jpg")

    # файл существует, пересохранён и ужат до максимум 512 по большей стороне
    stored = _tmp_uploads / "avatars" / url.rsplit("/", 1)[1]
    img = Image.open(stored)
    assert max(img.size) <= 512

    async with db_session() as db:
        user = (await db.execute(select(User).where(User.phone == PHONE))).scalar_one()
        assert user.avatar_url == url


async def test_avatar_rejects_non_image(client):
    await _auth_client(client)
    r = await client.post(
        "/api/v1/upload/avatar",
        files={"file": ("evil.jpg", b"MZ\x90\x00<script>alert(1)</script>", "image/jpeg")},
    )
    assert r.status_code == 400
    assert "не является изображением" in r.json()["detail"]


async def test_avatar_rejects_oversize(client, monkeypatch):
    await _auth_client(client)
    monkeypatch.setattr(uploads_mod, "MAX_UPLOAD_BYTES", 1000)
    r = await client.post(
        "/api/v1/upload/avatar",
        files={"file": ("big.jpg", _jpeg_bytes((900, 900)), "image/jpeg")},
    )
    assert r.status_code == 400
    assert "больше" in r.json()["detail"]


async def test_avatar_requires_auth(client):
    r = await client.post(
        "/api/v1/upload/avatar",
        files={"file": ("a.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 401


async def test_salon_photo_requires_permission(client, db_session):
    """Чужак (обычный клиент) не может грузить фото в салон."""
    from app.models.models import Salon

    async with db_session() as db:
        salon = Salon(name="Ф", address="а", phone="+70000000001",
                      latitude=1.0, longitude=1.0, timezone="Europe/Moscow")
        db.add(salon)
        await db.commit()
        await db.refresh(salon)

    await _auth_client(client)
    r = await client.post(
        f"/api/v1/upload/salon/{salon.id}/photo",
        files={"files": ("s.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 403


async def test_salon_photo_upload_and_delete_by_owner(client, db_session):
    from app.models.models import (
        OWNER_DEFAULT_PERMISSIONS, Salon, SalonMember, SalonRole,
    )

    data = await _auth_client(client)
    async with db_session() as db:
        salon = Salon(name="Мой", address="а", phone="+70000000002",
                      latitude=1.0, longitude=1.0, timezone="Europe/Moscow")
        db.add(salon)
        await db.flush()
        db.add(SalonMember(salon_id=salon.id, user_id=data["user"]["id"],
                           role=SalonRole.OWNER, is_creator=True,
                           permissions=dict(OWNER_DEFAULT_PERMISSIONS), is_active=True))
        await db.commit()
        salon_id = salon.id

    # Несколько файлов за раз + честный частичный успех: битый отклоняется
    r = await client.post(
        f"/api/v1/upload/salon/{salon_id}/photo",
        files=[
            ("files", ("a.jpg", _jpeg_bytes(), "image/jpeg")),
            ("files", ("b.jpg", _jpeg_bytes((640, 480), (10, 200, 90)), "image/jpeg")),
            ("files", ("fake.jpg", b"not-an-image", "image/jpeg")),
        ],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["saved"]) == 2
    assert len(body["errors"]) == 1 and body["errors"][0]["file"] == "fake.jpg"

    async with db_session() as db:
        photo = (await db.execute(
            select(SalonPhoto).where(SalonPhoto.salon_id == salon_id)
        )).scalars().first()

    r = await client.post(
        f"/api/v1/upload/salon/{salon_id}/photo/{photo.id}/delete",
        data={"next": "/business/my-salon"},
    )
    assert r.status_code == 302
    async with db_session() as db:
        left = (await db.execute(
            select(SalonPhoto).where(SalonPhoto.salon_id == salon_id)
        )).scalars().all()
        assert len(left) == 1  # из двух загруженных удалили одно
