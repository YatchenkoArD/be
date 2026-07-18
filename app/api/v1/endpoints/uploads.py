# app/api/v1/endpoints/uploads.py
"""Загрузка фото: аватар (за себя) и галерея салона (право manage_salon).

Мутации под cookie-аутентификацией — CSRF-щит (CSRFOriginMiddleware)
покрывает их так же, как остальные POST'ы с cookie.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_salon_permission, get_current_user
from app.db.session import get_db
from app.models.models import Salon, SalonPhoto, User
from app.services.uploads import UploadError, delete_stored, save_image

router = APIRouter()


def _safe_next(target: str, fallback: str) -> str:
    """Только внутренние пути (защита от open redirect) — как в auth_web."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return fallback
    return target


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Аватар текущего пользователя (клиент/мастер/модель/бизнес — любой).

    Отдаёт JSON: зовётся fetch'ем из profile.js, страница обновляет картинку
    без перезагрузки. Старый файл удаляется — мусор не копится.
    """
    try:
        url = await save_image(file, "avatars")
    except UploadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    old = current_user.avatar_url
    current_user.avatar_url = url
    await db.commit()
    if old and old.startswith("/uploads/"):
        delete_stored(old)
    return {"url": url}


@router.post("/salon/{salon_id}/photo")
async def upload_salon_photos(
    salon_id: int,
    files: list[UploadFile] = File(...),
    next: str = Form("/business/my-salon"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Фото в галерею салона, можно НЕСКОЛЬКО за раз. Право: manage_salon.

    Частичный успех честный: валидные файлы сохраняются, по каждому битому
    возвращается своя причина — страница показывает и то и другое.
    """
    salon = (await db.execute(select(Salon).where(Salon.id == salon_id))).scalar_one_or_none()
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Салон не найден")
    await check_salon_permission(db, current_user, salon_id, "manage_salon")

    saved, errors = [], []
    for file in files:
        try:
            url = await save_image(file, "salons")
        except UploadError as e:
            errors.append({"file": file.filename or "файл", "detail": str(e)})
            continue
        db.add(SalonPhoto(salon_id=salon_id, url=url))
        saved.append(url)
    if saved:
        await db.commit()

    if not saved and errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors[0]["detail"])
    return {"saved": saved, "errors": errors}


@router.post("/salon/{salon_id}/photo/{photo_id}/delete")
async def delete_salon_photo(
    salon_id: int,
    photo_id: int,
    next: str = Form("/business/my-salon"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_salon_permission(db, current_user, salon_id, "manage_salon")
    photo = (
        await db.execute(
            select(SalonPhoto).where(SalonPhoto.id == photo_id, SalonPhoto.salon_id == salon_id)
        )
    ).scalar_one_or_none()
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фото не найдено")

    url = photo.url
    await db.delete(photo)
    await db.commit()
    if url.startswith("/uploads/"):
        delete_stored(url)
    return RedirectResponse(url=_safe_next(next, "/business/my-salon"), status_code=302)
