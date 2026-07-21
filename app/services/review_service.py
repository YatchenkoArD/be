# app/services/review_service.py
"""Единая бизнес-логика отзывов.

Отзыв можно оставить только по факту реального визита: сервер сам (не со
слов клиента) проверяет, была ли у него COMPLETED-запись к этому мастеру/в
этом салоне через Руми, и без неё отклоняет создание отзыва — это и есть
единственный гейт. is_verified при этом всегда True (поле оставлено для
обратной совместимости со старыми записями и для бейджа в UI). Дёргается
из единственного эндпоинта (дубль в bookings.py удалён).
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Review, ReviewTargetType, Salon, Master, SalonMember, Booking, BookingStatus,
)


class ReviewError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


class ReviewService:
    @staticmethod
    async def _find_verifying_booking(
        db: AsyncSession, client_id: int, salon_id: int,
        target_type: ReviewTargetType, master_id: int | None,
    ) -> Booking | None:
        query = (
            select(Booking)
            .join(Master, Master.id == Booking.master_id)
            .where(
                Booking.client_id == client_id,
                Booking.status == BookingStatus.COMPLETED,
                Master.salon_id == salon_id,
            )
        )
        if target_type == ReviewTargetType.MASTER:
            query = query.where(Booking.master_id == master_id)
        result = await db.execute(query.order_by(Booking.start_time.desc()))
        return result.scalars().first()

    @staticmethod
    async def _already_reviewed(
        db: AsyncSession, client_id: int, target_type: ReviewTargetType,
        salon_id: int, master_id: int | None, staff_user_id: int | None,
    ) -> bool:
        query = select(func.count(Review.id)).where(
            Review.client_id == client_id, Review.target_type == target_type,
        )
        if target_type == ReviewTargetType.MASTER:
            query = query.where(Review.master_id == master_id)
        elif target_type == ReviewTargetType.STAFF:
            query = query.where(Review.staff_user_id == staff_user_id)
        else:
            query = query.where(Review.salon_id == salon_id)
        result = await db.execute(query)
        return (result.scalar() or 0) > 0

    @staticmethod
    async def create_review(
        db: AsyncSession,
        *,
        client_id: int,
        salon_id: int,
        target_type: ReviewTargetType,
        rating: int,
        comment: str = "",
        master_id: int | None = None,
        staff_user_id: int | None = None,
        booking_id: int | None = None,
    ) -> Review:
        if rating < 1 or rating > 5:
            raise ReviewError("Оценка должна быть от 1 до 5", status=400)

        salon = (await db.execute(select(Salon).where(Salon.id == salon_id))).scalar_one_or_none()
        if not salon:
            raise ReviewError("Салон не найден", status=404)

        master = None
        if target_type == ReviewTargetType.MASTER:
            if not master_id:
                raise ReviewError("Не указан мастер", status=400)
            master = (await db.execute(select(Master).where(Master.id == master_id))).scalar_one_or_none()
            if not master or master.salon_id != salon_id:
                raise ReviewError("Мастер не найден в этом салоне", status=400)
            staff_user_id = None
        elif target_type == ReviewTargetType.STAFF:
            if not staff_user_id:
                raise ReviewError("Не указан сотрудник", status=400)
            member = (await db.execute(
                select(SalonMember).where(
                    SalonMember.salon_id == salon_id,
                    SalonMember.user_id == staff_user_id,
                    SalonMember.is_active == True,
                )
            )).scalar_one_or_none()
            if not member:
                raise ReviewError("Сотрудник не найден в этом салоне", status=400)
            master_id = None
        else:
            master_id = None
            staff_user_id = None

        if await ReviewService._already_reviewed(db, client_id, target_type, salon_id, master_id, staff_user_id):
            raise ReviewError("Вы уже оставляли отзыв на эту цель", status=409)

        verifying_booking = None
        if booking_id:
            booking = (await db.execute(select(Booking).where(Booking.id == booking_id))).scalar_one_or_none()
            if booking and booking.client_id == client_id and booking.status == BookingStatus.COMPLETED:
                verifying_booking = booking
        if verifying_booking is None:
            verifying_booking = await ReviewService._find_verifying_booking(
                db, client_id, salon_id, target_type, master_id,
            )
        if verifying_booking is None:
            raise ReviewError(
                "Отзыв можно оставить только после завершённого визита, оформленного записью через Руми",
                status=403,
            )

        review = Review(
            client_id=client_id,
            salon_id=salon_id,
            target_type=target_type,
            master_id=master_id,
            staff_user_id=staff_user_id,
            rating=rating,
            comment=comment,
            is_verified=True,
            booking_id=verifying_booking.id,
        )
        db.add(review)
        await db.flush()

        if master is not None:
            avg_master = await db.execute(
                select(func.avg(Review.rating)).where(
                    Review.master_id == master_id,
                    Review.target_type == ReviewTargetType.MASTER,
                    Review.is_verified == True,
                )
            )
            master.rating = round(float(avg_master.scalar() or 0.0), 1)

        # Рейтинг салона считается по ВСЕМ подтверждённым отзывам (про мастера,
        # помещение, сотрудника) — все они отражают опыт визита в этот салон.
        # Только is_verified: непроверенные (в т.ч. старые, оставленные до
        # введения гейта) не должны влиять на рейтинг — иначе при выключенном
        # OTP это открытая дыра для накрутки. Заново от факта, не инкрементом —
        # не расходится при рассинхроне.
        count_salon = await db.execute(
            select(func.count(Review.id)).where(Review.salon_id == salon_id, Review.is_verified == True)
        )
        salon.reviews_count = count_salon.scalar() or 0
        avg_salon = await db.execute(
            select(func.avg(Review.rating)).where(Review.salon_id == salon_id, Review.is_verified == True)
        )
        salon.rating = round(float(avg_salon.scalar() or 0.0), 1)

        await db.commit()
        await db.refresh(review)
        return review