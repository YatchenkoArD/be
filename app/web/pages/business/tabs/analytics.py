# app/web/pages/business/tabs/analytics.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.models import Booking, Service, BookingStatus
from app.web.components.hint import hint as _hint


async def render_analytics_tab(db: AsyncSession, salon, master_ids):
    """Вкладка Аналитика."""
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    # Выручка по дням недели (текущая неделя)
    revenue_data = {}
    for i in range(7):
        day = today - timedelta(days=today.weekday()) + timedelta(days=i)
        day_end = day + timedelta(days=1)
        if master_ids:
            rev = await db.execute(
                select(func.coalesce(func.sum(Booking.final_price), 0))
                .where(
                    Booking.master_id.in_(master_ids),
                    Booking.start_time >= day,
                    Booking.start_time < day_end,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED])
                )
            )
            revenue_data[i] = rev.scalar() or 0
        else:
            revenue_data[i] = 0
    
    # Выручка за прошлую неделю
    prev_revenue_data = {}
    for i in range(7):
        day = today - timedelta(days=today.weekday() + 7) + timedelta(days=i)
        day_end = day + timedelta(days=1)
        if master_ids:
            rev = await db.execute(
                select(func.coalesce(func.sum(Booking.final_price), 0))
                .where(
                    Booking.master_id.in_(master_ids),
                    Booking.start_time >= day,
                    Booking.start_time < day_end,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED])
                )
            )
            prev_revenue_data[i] = rev.scalar() or 0
        else:
            prev_revenue_data[i] = 0
    
    # График выручки
    max_revenue = max(max(revenue_data.values()) if revenue_data else 1, 1)
    revenue_bars = ""
    for i in range(7):
        height = int(revenue_data[i] / max_revenue * 160) if max_revenue > 0 else 5
        prev_height = int(prev_revenue_data[i] / max_revenue * 160) if max_revenue > 0 else 5
        is_highest = revenue_data[i] == max(revenue_data.values())
        rev_val = f"{revenue_data[i]}".replace(",", " ")
        prev_val = f"{prev_revenue_data[i]}".replace(",", " ")
        revenue_bars += f"""
        <div class="chart-column" onclick="showDayDetails({i}, '{days[i]}', {revenue_data[i]}, {prev_revenue_data[i]})" style="cursor:pointer">
            <div class="chart-value">{rev_val} ₽</div>
            <div class="chart-fill {'highest' if is_highest else ''}" style="height:{max(height, 5)}px"></div>
            <div class="chart-fill prev" style="height:{max(prev_height, 5)}px;opacity:0.4"></div>
            <div class="chart-label">{days[i]}</div>
        </div>"""
    
    total_revenue = sum(revenue_data.values())
    prev_total_revenue = sum(prev_revenue_data.values())
    revenue_diff = total_revenue - prev_total_revenue
    revenue_trend = "▲" if revenue_diff > 0 else "▼" if revenue_diff < 0 else "—"
    revenue_color = "#22c55e" if revenue_diff > 0 else "#ef4444" if revenue_diff < 0 else "var(--color-muted)"
    
    # Считаем общее количество записей за неделю (все статусы) и оплачиваемых
    # (подтверждённые/завершённые — для среднего чека, чтобы отменённые не занижали его)
    week_total = 0
    week_paid_total = 0
    for i in range(7):
        day = today - timedelta(days=today.weekday()) + timedelta(days=i)
        day_end = day + timedelta(days=1)
        if master_ids:
            cnt = await db.execute(select(func.count(Booking.id)).where(
                Booking.master_id.in_(master_ids),
                Booking.start_time >= day,
                Booking.start_time < day_end
            ))
            week_total += cnt.scalar() or 0

            paid_cnt = await db.execute(select(func.count(Booking.id)).where(
                Booking.master_id.in_(master_ids),
                Booking.start_time >= day,
                Booking.start_time < day_end,
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED])
            ))
            week_paid_total += paid_cnt.scalar() or 0
    
    # Топ услуг
    top_services = []
    if master_ids:
        top_svc = await db.execute(
            select(Service.name, func.count(Booking.id).label("cnt"), func.sum(Booking.final_price).label("total"))
            .join(Booking, Booking.service_id == Service.id)
            .where(Booking.master_id.in_(master_ids), Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]))
            .group_by(Service.name)
            .order_by(func.sum(Booking.final_price).desc())
            .limit(5)
        )
        top_services = top_svc.all()
    
    top_services_rows = ""
    for name, cnt, total in top_services:
        total_val = f"{total or 0}".replace(",", " ")
        cnt_val = f"{cnt}".replace(",", " ")
        top_services_rows += f"""
        <tr>
            <td>{name}</td>
            <td>{cnt_val}</td>
            <td><strong>{total_val} ₽</strong></td>
        </tr>"""
    
    return f"""
    <div id="tab-analytics" class="tab-content">
        <div class="analytics-kpi">
            <div class="kpi-card">
                <div class="kpi-label">Выручка за неделю {_hint("Сумма подтверждённых и завершённых записей за текущую неделю (Пн—Вс).")}</div>
                <div class="kpi-value">{total_revenue:,} ₽</div>
                <div class="kpi-trend" style="color:{revenue_color}">{revenue_trend} {abs(revenue_diff):,} ₽ vs прошлая</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Средний чек {_hint("Выручка за неделю, делённая на число подтверждённых и завершённых записей (отменённые и ожидающие в расчёт не входят).")}</div>
                <div class="kpi-value">{total_revenue // max(week_paid_total, 1):,} ₽</div>
                <div class="kpi-trend" style="color:var(--color-muted)">за неделю</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Всего записей {_hint("Все записи за неделю к мастерам салона — включая отменённые и ещё не подтверждённые.")}</div>
                <div class="kpi-value">{week_total}</div>
                <div class="kpi-trend" style="color:var(--color-muted)">за неделю</div>
            </div>
        </div>

        <div class="card" style="margin-bottom:1.5rem">
            <h3 style="margin-bottom:0.5rem">💰 Выручка по дням {_hint("Столбики — выручка по подтверждённым/завершённым записям каждого дня: сплошной — эта неделя, бледный — прошлая, для сравнения.")}</h3>
            <div class="legend">
                <span><span class="legend-dot" style="background:linear-gradient(to top,var(--color-primary),var(--color-accent))"></span> Эта неделя</span>
                <span><span class="legend-dot" style="background:var(--color-border)"></span> Прошлая неделя</span>
            </div>
            <div class="chart-bar">{revenue_bars}</div>
            <p style="font-size:0.75rem;color:var(--color-muted);text-align:center;margin-top:0.5rem">Нажмите на столбец, чтобы увидеть детали</p>
        </div>
        
        <div class="card">
            <h3 style="margin-bottom:1rem">🏆 Топ услуг по выручке {_hint("Топ-5 услуг за всё время (не только за неделю) по сумме подтверждённых и завершённых записей.")}</h3>
            <table>
                <thead>
                    <tr><th>Услуга</th><th>Записей</th><th>Выручка</th></tr>
                </thead>
                <tbody>
                    {top_services_rows or '<tr><td colspan="3" style="text-align:center;padding:2rem;color:var(--color-muted)">Нет данных</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>"""