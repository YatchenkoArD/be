# app/web/pages/business/tabs/overview.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.models import Booking, Service


async def render_overview_tab(db: AsyncSession, salon, masters, master_ids, services_count, promotions, today_bookings):
    """Вкладка Обзор."""
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Записи за неделю (для графика)
    week_data = {}
    for i in range(7):
        day = today - timedelta(days=today.weekday()) + timedelta(days=i)
        day_end = day + timedelta(days=1)
        if master_ids:
            count = await db.execute(select(func.count(Booking.id)).where(
                Booking.master_id.in_(master_ids), 
                Booking.start_time >= day, 
                Booking.start_time < day_end
            ))
            week_data[i] = count.scalar() or 0
        else:
            week_data[i] = 0
    
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    max_val = max(week_data.values()) if week_data else 1
    chart_bars = ""
    for i in range(7):
        height = int(week_data[i] / max_val * 160) if max_val > 0 else 5
        chart_bars += f'<div class="chart-column"><div class="chart-value">{week_data[i]}</div><div class="chart-fill" style="height:{max(height, 5)}px"></div><div class="chart-label">{days[i]}</div></div>'
    
    return f"""
    <div id="tab-overview" class="tab-content active">
        <div class="grid-3" style="margin-bottom:2rem">
            <div class="stat-card"><div class="stat-value">{len(masters)}</div><div class="stat-label">Мастеров</div></div>
            <div class="stat-card"><div class="stat-value">{services_count}</div><div class="stat-label">Услуг</div></div>
            <div class="stat-card"><div class="stat-value">{today_bookings}</div><div class="stat-label">Записей сегодня</div></div>
            <div class="stat-card"><div class="stat-value">{len(promotions)}</div><div class="stat-label">Акций</div></div>
            <div class="stat-card"><div class="stat-value">⭐ {salon.rating}</div><div class="stat-label">Рейтинг</div></div>
            <div class="stat-card"><div class="stat-value">{salon.reviews_count}</div><div class="stat-label">Отзывов</div></div>
        </div>
        <div class="card" style="margin-bottom:2rem">
            <h3 style="margin-bottom:1rem">📊 Записи за неделю</h3>
            <div class="chart-bar">{chart_bars}</div>
        </div>
    </div>"""