# app/web/pages/bookings.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.models.models import Booking, BookingStatus, Master, Service, Salon, User
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.web.components.icons import (
    ICON_CALENDAR_BIG,
    ICON_MAP_PIN,
    ICON_PHONE,
)

async def render_bookings_page(db: AsyncSession, user) -> str:
    """Страница 'Мои записи' для клиента."""
    
    bookings_result = await db.execute(
        select(Booking).where(
            Booking.client_id == user.id
        ).order_by(Booking.start_time.desc())
    )
    bookings = bookings_result.scalars().all()

    now = datetime.now()

    upcoming = []
    completed = []
    cancelled = []

    for b in bookings:
        if b.status == BookingStatus.CANCELLED:
            cancelled.append(b)
        elif b.status == BookingStatus.COMPLETED:
            completed.append(b)
        elif b.start_time > now and b.status in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            upcoming.append(b)
        else:
            completed.append(b)

    async def render_booking_card(booking):
        master = None
        if booking.master_id:
            master = (await db.execute(select(Master).where(Master.id == booking.master_id))).scalar_one_or_none()
        service = None
        if booking.service_id:
            service = (await db.execute(select(Service).where(Service.id == booking.service_id))).scalar_one_or_none()
        
        master_name = "Мастер"
        service_name = "Услуга"
        salon_name = "Салон"
        salon_address = ""
        salon_phone = ""
        
        if master:
            master_user = (await db.execute(select(User).where(User.id == master.user_id))).scalar_one_or_none()
            master_name = master_user.full_name if master_user else "Мастер"
            if master.salon_id:
                salon = (await db.execute(select(Salon).where(Salon.id == master.salon_id))).scalar_one_or_none()
                if salon:
                    salon_name = salon.name
                    salon_address = salon.address or ""
                    salon_phone = salon.phone or ""
        
        if service:
            service_name = service.name

        status_label = {
            BookingStatus.PENDING: "Ожидает",
            BookingStatus.CONFIRMED: "Подтверждено",
            BookingStatus.COMPLETED: "Завершено",
            BookingStatus.CANCELLED: "Отменено",
        }.get(booking.status, "—")
        
        cancel_btn = ""
        if booking in upcoming and booking.status != BookingStatus.CANCELLED:
            cancel_btn = f'<div class="booking-actions"><button class="btn-outline" style="color:var(--color-danger, #ef4444); border-color:var(--color-danger, #ef4444);" onclick="cancelBooking({booking.id})">Отменить</button></div>'
        
        date_str = booking.start_time.replace(tzinfo=None).strftime('%d.%m.%Y в %H:%M')
        
        return f"""
        <div class="booking-card">
            <div class="booking-header">
                <span class="service-name">{service_name}</span>
                <span class="booking-status">{status_label}</span>
            </div>
            <div class="booking-body">
                <p><span class="label">📅 Дата:</span> {date_str}</p>
                <p><span class="label">💇 Мастер:</span> {master_name}</p>
                <p><span class="label">🏢 Салон:</span> {salon_name}</p>
                {f'<p><span class="label">{ICON_MAP_PIN} Адрес:</span> {salon_address}</p>' if salon_address else ''}
                {f'<p><span class="label">{ICON_PHONE} Телефон:</span> {salon_phone}</p>' if salon_phone else ''}
                <p><span class="label">💰 Цена:</span> {booking.final_price or '—'} ₽</p>
            </div>
            {cancel_btn}
        </div>
        """

    async def render_category(bookings_list, empty_message, empty_detail, show_salon_button=False):
        if bookings_list:
            cards = ""
            for b in bookings_list:
                cards += await render_booking_card(b)
            return cards
        else:
            button_html = f'<a href="/salons" class="btn-primary">Выбрать салон</a>' if show_salon_button else ''
            return f"""
            <div class="empty-state">
                <div class="empty-icon">{ICON_CALENDAR_BIG}</div>
                <h3>{empty_message}</h3>
                <p>{empty_detail}</p>
                {button_html}
            </div>
            """

    upcoming_html = await render_category(upcoming, "Нет предстоящих записей", "Выберите салон и запишитесь к мастеру — запись появится здесь", show_salon_button=True)
    completed_html = await render_category(completed, "Нет завершённых записей", "Здесь будут отображаться завершённые записи")
    cancelled_html = await render_category(cancelled, "Нет отменённых записей", "Здесь будут отображаться отменённые записи")

    upcoming_count = len(upcoming)
    completed_count = len(completed)
    cancelled_count = len(cancelled)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Мои записи — руми</title>
    {get_base_styles()}
</head>
<body>
    {render_header("bookings")}
    {render_sidebar("bookings", user)}
    
    <main class="bookings-main">
        <div class="section-container">
            <div class="bookings-header">
                <h1>Мои записи</h1>
                <p>Все ваши записи в салоны красоты</p>
            </div>

            <div class="bookings-tabs">
                <button class="tab-btn active" data-tab="upcoming">Предстоящие</button>
                <button class="tab-btn" data-tab="completed">Завершённые <span class="badge">{completed_count}</span></button>
                <button class="tab-btn" data-tab="cancelled">Отменённые <span class="badge">{cancelled_count}</span></button>
            </div>

            <div id="tab-upcoming" class="tab-content active">
                {upcoming_html}
            </div>
            <div id="tab-completed" class="tab-content">
                {completed_html}
            </div>
            <div id="tab-cancelled" class="tab-content">
                {cancelled_html}
            </div>
        </div>
    </main>

    {render_footer()}
</body>
</html>"""
    return html