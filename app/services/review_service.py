# app/services/review_service.py
"""Единая бизнес-логика отзывов.

Закрывает накрутку рейтинга (IDOR + business-logic flaw): отзыв можно
оставить только при наличии ЗАВЕРШЁННОЙ (COMPLETED) записи этого клиента
к этому мастеру, и не более одного отзыва на пару клиент-мастер.
Дёргается из единственного эндпоинта (дубль в bookings.py удалён).
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Review, Salon, Master, Booking, BookingStatus


class ReviewError(Exception):
    """Бизнес-ошибка отзыва. message — текст для пользователя, status — HTTP-код."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


class ReviewService:
    @staticmethod
    async def _has_completed_booking(db: AsyncSession, client_id: int, master_id: int) -> bool:
        result = await db.execute(
            select(func.count(Booking.id)).where(
                Booking.client_id == client_id,
                Booking.master_id == master_id,
                Booking.status == BookingStatus.COMPLETED,
            )
        )
        return (result.scalar() or 0) > 0

    @staticmethod
    async def _already_reviewed(db: AsyncSession, client_id: int, master_id: int) -> bool:
        result = await db.execute(
            select(func.count(Review.id)).where(
                Review.client_id == client_id,
                Review.master_id == master_id,
            )
        )
        return (result.scalar() or 0) > 0

    @staticmethod
    async def create_review(
        db: AsyncSession,
        *,
        client_id: int,
        master_id: int,
        salon_id: int,
        rating: int,
        comment: str = "",
    ) -> Review:
        if rating < 1 or rating > 5:
            raise ReviewError("Оценка должна быть от 1 до 5", status=400)

        # Мастер существует и действительно принадлежит указанному салону
        master = (await db.execute(select(Master).where(Master.id == master_id))).scalar_one_or_none()
        if not master:
            raise ReviewError("Мастер не найден", status=404)
        if master.salon_id != salon_id:
            raise ReviewError("Мастер не относится к этому салону", status=400)

        # Ключевая проверка: только после реально завершённого визита
        if not await ReviewService._has_completed_booking(db, client_id, master_id):
            raise ReviewError(
                "Отзыв можно оставить только после завершённой записи к этому мастеру",
                status=403,
            )

        # Не больше одного отзыва на пару клиент-мастер
        if await ReviewService._already_reviewed(db, client_id, master_id):
            raise ReviewError("Вы уже оставляли отзыв этому мастеру", status=409)

        review = Review(
            client_id=client_id,
            master_id=master_id,
            salon_id=salon_id,
            rating=rating,
            comment=comment,
        )
        db.add(review)

        # Пересчёт рейтинга мастера
        avg_master = await db.execute(
            select(func.avg(Review.rating)).where(Review.master_id == master_id)
        )
        master.rating = round(float(avg_master.scalar() or 0.0), 1)

        # Пересчёт рейтинга салона — оба поля считаются заново от реальных
        # отзывов (не инкремент), иначе reviews_count расходится с фактом
        # при любом рассинхроне баз (сид, ручные правки и т.п.).
        salon = (await db.execute(select(Salon).where(Salon.id == salon_id))).scalar_one_or_none()
        if salon:
            count_salon = await db.execute(
                select(func.count(Review.id)).where(Review.salon_id == salon_id)
            )
            salon.reviews_count = count_salon.scalar() or 0
            avg_salon = await db.execute(
                select(func.avg(Review.rating)).where(Review.salon_id == salon_id)
            )
            salon.rating = round(float(avg_salon.scalar() or 0.0), 1)

        await db.commit()
        return review
