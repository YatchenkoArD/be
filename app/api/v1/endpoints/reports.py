# app/api/v1/endpoints/reports.py
"""Жалобы на фото (портфолио мастера или отзыв) — создание и модерация.

Модерирует владелец/админ салона, которому принадлежит фото (право
manage_reviews), либо платформенный админ — над любым фото."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_salon_permission, get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import (
    Master, MasterPhoto, PhotoReport, PhotoReportStatus, Review, ReviewPhoto, User, UserRole,
)
from app.services.uploads import delete_stored

router = APIRouter()


async def _photo_and_salon_id(db: AsyncSession, report: PhotoReport):
    """Возвращает (url фото, salon_id владельца фото) для отчёта — фото
    может быть либо из портфолио мастера, либо из отзыва."""
    if report.master_photo_id:
        row = (await db.execute(
            select(MasterPhoto, Master)
            .join(Master, Master.id == MasterPhoto.master_id)
            .where(MasterPhoto.id == report.master_photo_id)
        )).first()
        if not row:
            return None, None
        photo, master = row
        return photo.url, master.salon_id
    row = (await db.execute(
        select(ReviewPhoto, Review)
        .join(Review, Review.id == ReviewPhoto.review_id)
        .where(ReviewPhoto.id == report.review_photo_id)
    )).first()
    if not row:
        return None, None
    photo, review = row
    return photo.url, review.salon_id


@router.post("/photo")
@limiter.limit("10/hour")  # лимит по IP — против спама жалобами
async def create_photo_report(
    request: Request,
    reason: str = Form(""),
    master_photo_id: int = Form(None),
    review_photo_id: int = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Жалоба на фото — доступна любому авторизованному пользователю."""
    if bool(master_photo_id) == bool(review_photo_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Укажите ровно одно фото")

    if master_photo_id:
        exists = (await db.execute(select(MasterPhoto).where(MasterPhoto.id == master_photo_id))).scalar_one_or_none()
    else:
        exists = (await db.execute(select(ReviewPhoto).where(ReviewPhoto.id == review_photo_id))).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фото не найдено")

    report = PhotoReport(
        master_photo_id=master_photo_id,
        review_photo_id=review_photo_id,
        reporter_id=current_user.id,
        reason=reason or None,
    )
    db.add(report)
    await db.commit()

    from app.services.notifications import notify_admins, notify_photo_report
    _, report_salon_id = await _photo_and_salon_id(db, report)
    await notify_photo_report(db, report_salon_id)
    await notify_admins(db, "Новая жалоба на фото",
                        f"Причина: {reason}" if reason else "Загляните в модерацию (админ-панель → Жалобы).")
    return {"status": "reported"}


async def _require_moderator(db: AsyncSession, user: User, report: PhotoReport) -> None:
    if user.role == UserRole.ADMIN:
        return
    _, salon_id = await _photo_and_salon_id(db, report)
    if salon_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фото уже удалено")
    await check_salon_permission(db, user, salon_id, "manage_reviews")


@router.post("/{report_id}/resolve")
async def resolve_photo_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Жалоба обоснована — фото удаляется, жалоба закрывается."""
    report = (await db.execute(select(PhotoReport).where(PhotoReport.id == report_id))).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Жалоба не найдена")
    if report.status != PhotoReportStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Жалоба уже обработана")

    await _require_moderator(db, current_user, report)
    url, _ = await _photo_and_salon_id(db, report)

    if report.master_photo_id:
        photo = (await db.execute(select(MasterPhoto).where(MasterPhoto.id == report.master_photo_id))).scalar_one_or_none()
    else:
        photo = (await db.execute(select(ReviewPhoto).where(ReviewPhoto.id == report.review_photo_id))).scalar_one_or_none()
    if photo:
        await db.delete(photo)

    report.status = PhotoReportStatus.RESOLVED
    report.resolved_by_id = current_user.id
    report.resolved_at = datetime.now(timezone.utc)
    await db.commit()

    if url and url.startswith("/uploads/"):
        delete_stored(url)
    return {"status": "resolved"}


@router.post("/{report_id}/dismiss")
async def dismiss_photo_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Жалоба необоснована — фото остаётся, жалоба закрывается."""
    report = (await db.execute(select(PhotoReport).where(PhotoReport.id == report_id))).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Жалоба не найдена")
    if report.status != PhotoReportStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Жалоба уже обработана")

    await _require_moderator(db, current_user, report)

    report.status = PhotoReportStatus.DISMISSED
    report.resolved_by_id = current_user.id
    report.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "dismissed"}
