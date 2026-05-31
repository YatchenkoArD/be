# app/web/pages/business/tabs/schedule.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.models.models import Booking, Master, Service, User as UserModel, BookingStatus


async def render_schedule_tab(db: AsyncSession, salon, masters) -> str:
    """Вкладка Расписание с реальными записями."""
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    # Получаем записи на сегодня для всех мастеров салона
    master_ids = [m.id for m in masters]
    bookings_result = await db.execute(
        select(Booking).where(
            Booking.master_id.in_(master_ids),
            Booking.start_time >= today,
            Booking.start_time < tomorrow,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        ).order_by(Booking.start_time)
    )
    bookings = bookings_result.scalars().all()
    
    # Группируем записи по мастерам
    master_bookings = {}
    for b in bookings:
        if b.master_id not in master_bookings:
            master_bookings[b.master_id] = []
        master_bookings[b.master_id].append(b)
    
    # Генерируем временные слоты (с 9:00 до 21:00)
    hours = list(range(9, 22))
    
    # Строим таблицу
    schedule_rows = ""
    for m in masters:
        # Имя мастера
        user_result = await db.execute(select(UserModel).where(UserModel.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        master_name = master_user.full_name if master_user else "—"
        
        # Ячейки для каждого часа
        cells = ""
        for hour in hours:
            slot_start = today.replace(hour=hour, minute=0)
            slot_end = today.replace(hour=hour + 1, minute=0)
            
            # Ищем записи, попадающие в этот слот
            slot_bookings = []
            for b in master_bookings.get(m.id, []):
                b_start = b.start_time.replace(tzinfo=None) if b.start_time.tzinfo else b.start_time
                b_end = b.end_time.replace(tzinfo=None) if b.end_time.tzinfo else b.end_time
                if b_start < slot_end and b_end > slot_start:
                    # Получаем услугу и клиента
                    service = (await db.execute(select(Service).where(Service.id == b.service_id))).scalar_one_or_none()
                    client = (await db.execute(select(UserModel).where(UserModel.id == b.client_id))).scalar_one_or_none()
                    slot_bookings.append({
                        "time": f"{b_start.strftime('%H:%M')}-{b_end.strftime('%H:%M')}",
                        "service": service.name if service else "—",
                        "client": client.full_name if client else "Клиент",
                        "status": "confirmed" if b.status == BookingStatus.CONFIRMED else "pending"
                    })
            
            if slot_bookings:
                # Показываем записи в слоте
                booking_html = ""
                for sb in slot_bookings:
                    bg_color = "#dcfce7" if sb["status"] == "confirmed" else "#fef9c3"
                    booking_html += f"""
                    <div style="background:{bg_color};padding:0.25rem 0.5rem;border-radius:0.25rem;margin-bottom:0.15rem;font-size:0.7rem;cursor:pointer" 
                         title="{sb['client']} — {sb['service']} ({sb['time']})">
                        {sb['time']}<br>{sb['service'][:15]}
                    </div>"""
                cells += f'<td style="padding:0.25rem;vertical-align:top">{booking_html}</td>'
            else:
                cells += '<td style="padding:0.25rem"></td>'
        
        schedule_rows += f"""
        <tr>
            <td style="font-weight:600;white-space:nowrap;padding:0.5rem">{master_name}</td>
            <td style="font-size:0.8rem;color:var(--color-muted);padding:0.5rem">{m.specialization}</td>
            {cells}
        </tr>"""
    
    # Заголовки часов
    hour_headers = ""
    for hour in hours:
        hour_headers += f'<th style="text-align:center;font-size:0.75rem;padding:0.5rem;min-width:80px">{hour}:00</th>'
    
    return f"""
    <div id="tab-schedule" class="tab-content">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
            <h3>📅 Расписание на сегодня ({today.strftime('%d.%m.%Y')})</h3>
            <div style="display:flex;gap:0.5rem">
                <button class="btn-outline" style="font-size:0.8rem;padding:0.4rem 0.8rem" onclick="changeDate(-1)">← Вчера</button>
                <button class="btn-outline" style="font-size:0.8rem;padding:0.4rem 0.8rem" onclick="changeDate(0)">Сегодня</button>
                <button class="btn-outline" style="font-size:0.8rem;padding:0.4rem 0.8rem" onclick="changeDate(1)">Завтра →</button>
            </div>
        </div>
        
        <div class="card" style="overflow-x:auto">
            <table>
                <thead>
                    <tr>
                        <th>Мастер</th>
                        <th>Спец.</th>
                        {hour_headers}
                    </tr>
                </thead>
                <tbody>
                    {schedule_rows or '<tr><td colspan="{len(hours) + 2}" style="text-align:center;padding:2rem;color:var(--color-muted)">Нет записей на сегодня</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div style="display:flex;gap:1rem;margin-top:0.5rem;font-size:0.75rem;color:var(--color-muted)">
            <span><span style="display:inline-block;width:12px;height:12px;background:#dcfce7;border-radius:2px;margin-right:0.25rem"></span> Подтверждено</span>
            <span><span style="display:inline-block;width:12px;height:12px;background:#fef9c3;border-radius:2px;margin-right:0.25rem"></span> Ожидает</span>
        </div>
    </div>
    
    <script>
        function changeDate(offset) {{
            const today = new Date();
            today.setDate(today.getDate() + offset);
            const dateStr = today.toISOString().split('T')[0];
            window.location.href = `/business/dashboard?date=${{dateStr}}&tab=schedule`;
        }}
    </script>"""