# app/services/notifications.py
"""Уведомления о записях в Telegram (бот @rumi_beauty_bot + очередь ARQ).

Кому и что:
- бизнесу (создателю салона) и мастеру — «новая запись» сразу;
- клиенту — подтверждение сразу и напоминание за REMINDER_BEFORE до визита
  (отложенная задача send_booking_reminder, статус проверяется при отправке).

Приходят только тем, у кого привязан Telegram (users.tg_chat_id — ставится
ботом при подтверждении номера или через /start). Любая ошибка здесь
глотается с логом: уведомления — сервис вежливости, они не имеют права
ломать создание или отмену записи.
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.worker import get_arq_pool
from app.models.models import (
    Booking, Equipment, InventoryItem, Master, Salon, SalonMember, Service, User,
    WarehouseRequest, WarehouseRequestType,
)

logger = logging.getLogger(__name__)

REMINDER_BEFORE = timedelta(hours=2)


def reminder_eta_utc(start_naive: datetime, salon_tz: str) -> datetime | None:
    """UTC-момент напоминания (за REMINDER_BEFORE до начала), либо None.

    start_time хранится naive в местном времени салона — локализуем через
    zoneinfo и переводим в UTC; если момент уже в прошлом, напоминание
    не ставим (запись «на через час» получает только подтверждение).
    """
    tz = ZoneInfo(salon_tz or "Europe/Moscow")
    aware = start_naive.replace(tzinfo=tz)
    eta = aware.astimezone(timezone.utc) - REMINDER_BEFORE
    return eta if eta > datetime.now(timezone.utc) else None


async def _booking_context(db: AsyncSession, booking: Booking) -> dict:
    """Все стороны записи одним заходом (явные select — без ленивой подгрузки)."""
    master = (
        await db.execute(select(Master).where(Master.id == booking.master_id))
    ).scalar_one()
    salon = (
        await db.execute(select(Salon).where(Salon.id == master.salon_id))
    ).scalar_one()
    service = (
        await db.execute(select(Service).where(Service.id == booking.service_id))
    ).scalar_one_or_none()
    client = (
        await db.execute(select(User).where(User.id == booking.client_id))
    ).scalar_one_or_none()
    master_user = (
        await db.execute(select(User).where(User.id == master.user_id))
    ).scalar_one_or_none()
    owner = (
        await db.execute(
            select(User)
            .join(SalonMember, SalonMember.user_id == User.id)
            .where(
                SalonMember.salon_id == salon.id,
                SalonMember.is_creator == True,  # noqa: E712
                SalonMember.is_active == True,  # noqa: E712
            )
        )
    ).scalars().first()
    return {
        "master": master, "salon": salon, "service": service,
        "client": client, "master_user": master_user, "owner": owner,
    }


async def _enqueue(chat_id: int, text: str, **kwargs) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job("send_tg_message", chat_id, text, **kwargs)


async def notify_booking_created(db: AsyncSession, booking: Booking) -> None:
    if not settings.TG_NOTIFY_ENABLED:
        return
    try:
        ctx = await _booking_context(db, booking)
        salon, service, client = ctx["salon"], ctx["service"], ctx["client"]
        when = booking.start_time.strftime("%d.%m в %H:%M")
        service_name = service.name if service else "услуга"
        client_name = (client.full_name or "клиент") if client else "клиент"

        master_name = (
            ctx["master_user"].full_name if ctx["master_user"] and ctx["master_user"].full_name
            else "мастер"
        )
        business_text = (
            f"📅 Новая запись: {client_name} — {service_name}\n"
            f"{when}, мастер {master_name}"
        )
        # мастеру и владельцу (если это разные привязанные люди)
        notified: set[int] = set()
        for person in (ctx["master_user"], ctx["owner"]):
            if person and person.tg_chat_id and person.tg_chat_id not in notified:
                await _enqueue(person.tg_chat_id, business_text)
                notified.add(person.tg_chat_id)

        if client and client.tg_chat_id:
            await _enqueue(
                client.tg_chat_id,
                f"✅ Вы записаны: {service_name} в «{salon.name}»\n"
                f"{when}, мастер {master_name}\n"
                f"Адрес: {salon.address or 'уточните у салона'}",
            )
            eta = reminder_eta_utc(booking.start_time, salon.timezone)
            if eta:
                pool = await get_arq_pool()
                await pool.enqueue_job(
                    "send_booking_reminder", booking.id,
                    _defer_until=eta,
                    _job_id=f"booking-reminder:{booking.id}",
                )
    except Exception:
        logger.exception("notify_booking_created(%s): уведомления не поставлены", booking.id)


async def notify_booking_cancelled(db: AsyncSession, booking: Booking) -> None:
    if not settings.TG_NOTIFY_ENABLED:
        return
    try:
        ctx = await _booking_context(db, booking)
        when = booking.start_time.strftime("%d.%m в %H:%M")
        service_name = ctx["service"].name if ctx["service"] else "услуга"

        notified: set[int] = set()
        for person in (ctx["master_user"], ctx["owner"]):
            if person and person.tg_chat_id and person.tg_chat_id not in notified:
                await _enqueue(
                    person.tg_chat_id,
                    f"❌ Запись отменена: {service_name}, {when}",
                )
                notified.add(person.tg_chat_id)

        client = ctx["client"]
        if client and client.tg_chat_id:
            await _enqueue(
                client.tg_chat_id,
                f"❌ Ваша запись отменена: {service_name} в «{ctx['salon'].name}», {when}",
            )
    except Exception:
        logger.exception("notify_booking_cancelled(%s): уведомления не поставлены", booking.id)


async def notify_warehouse_request_created(db: AsyncSession, request: WarehouseRequest) -> None:
    """Пуш владельцу/админам салона: мастер сообщил, что расходник
    заканчивается или техника сломалась. Получают только те, у кого личный
    тумблер SalonMember.notify_warehouse_requests включён (по умолчанию да)
    и привязан Telegram — как и остальные уведомления, сервис вежливости,
    не имеет права ломать создание заявки."""
    if not settings.TG_NOTIFY_ENABLED:
        return
    try:
        salon = (await db.execute(select(Salon).where(Salon.id == request.salon_id))).scalar_one_or_none()
        if not salon:
            return

        if request.type == WarehouseRequestType.CONSUMABLE_LOW:
            target_name = "расходник"
            if request.item_id:
                item = (await db.execute(select(InventoryItem).where(InventoryItem.id == request.item_id))).scalar_one_or_none()
                if item:
                    target_name = item.name
            text = f"⚠️ Заканчивается: {target_name}"
        else:
            target_name = "техника"
            if request.equipment_id:
                equipment = (await db.execute(select(Equipment).where(Equipment.id == request.equipment_id))).scalar_one_or_none()
                if equipment:
                    target_name = equipment.name
            text = f"🔧 Сломалась техника: {target_name}"

        if request.comment:
            text += f"\n«{request.comment}»"
        text += f"\nСалон «{salon.name}»"

        recipients = (await db.execute(
            select(User)
            .join(SalonMember, SalonMember.user_id == User.id)
            .where(
                SalonMember.salon_id == salon.id,
                SalonMember.is_active == True,
                SalonMember.notify_warehouse_requests == True,
            )
        )).scalars().all()

        notified: set[int] = set()
        for person in recipients:
            if person.tg_chat_id and person.tg_chat_id not in notified:
                await _enqueue(person.tg_chat_id, text)
                notified.add(person.tg_chat_id)
    except Exception:
        logger.exception("notify_warehouse_request_created(%s): уведомление не поставлено", request.id)
