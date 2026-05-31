# app/web/pages/business/tabs/finances.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.models import Booking, BookingStatus, User as UserModel


async def render_finances_tab(db: AsyncSession, salon, masters, master_ids) -> str:
    """Вкладка Финансы — выручка, зарплаты, себестоимость."""
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    
    # Общая выручка за месяц
    month_revenue = 0
    if master_ids:
        rev = await db.execute(
            select(func.coalesce(func.sum(Booking.final_price), 0))
            .where(
                Booking.master_id.in_(master_ids),
                Booking.start_time >= month_start,
                Booking.status == BookingStatus.COMPLETED
            )
        )
        month_revenue = rev.scalar() or 0
    
    # Количество завершённых записей за месяц
    month_completed = 0
    if master_ids:
        cnt = await db.execute(
            select(func.count(Booking.id))
            .where(
                Booking.master_id.in_(master_ids),
                Booking.start_time >= month_start,
                Booking.status == BookingStatus.COMPLETED
            )
        )
        month_completed = cnt.scalar() or 0
    
    # Выручка по дням за последние 7 дней
    daily_revenue = {}
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_end = day + timedelta(days=1)
        if master_ids:
            rev = await db.execute(
                select(func.coalesce(func.sum(Booking.final_price), 0))
                .where(
                    Booking.master_id.in_(master_ids),
                    Booking.start_time >= day,
                    Booking.start_time < day_end,
                    Booking.status == BookingStatus.COMPLETED
                )
            )
            daily_revenue[day.strftime("%d.%m")] = rev.scalar() or 0
        else:
            daily_revenue[day.strftime("%d.%m")] = 0
    
    # График выручки по дням
    max_daily = max(daily_revenue.values()) if daily_revenue else 1
    revenue_chart = ""
    for date_str, amount in daily_revenue.items():
        height = int(amount / max_daily * 120) if max_daily > 0 else 5
        amount_str = f"{amount:,}".replace(",", " ")
        revenue_chart += f"""
        <div class="chart-column">
            <div class="chart-value" style="font-size:0.65rem">{amount_str} ₽</div>
            <div class="chart-fill" style="height:{max(height, 5)}px"></div>
            <div class="chart-label">{date_str}</div>
        </div>"""
    
    # Зарплаты мастеров (упрощённо: 40% от выручки)
    salary_rows = ""
    for m in masters:
        master_rev = 0
        if master_ids:
            rev = await db.execute(
                select(func.coalesce(func.sum(Booking.final_price), 0))
                .where(
                    Booking.master_id == m.id,
                    Booking.start_time >= month_start,
                    Booking.status == BookingStatus.COMPLETED
                )
            )
            master_rev = rev.scalar() or 0
        
        master_cnt = 0
        cnt_result = await db.execute(
            select(func.count(Booking.id))
            .where(
                Booking.master_id == m.id,
                Booking.start_time >= month_start,
                Booking.status == BookingStatus.COMPLETED
            )
        )
        master_cnt = cnt_result.scalar() or 0
        
        salary = int(master_rev * 0.4)
        
        user_result = await db.execute(select(UserModel).where(UserModel.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        master_name = master_user.full_name if master_user else "—"
        
        rev_str = f"{master_rev:,}".replace(",", " ")
        sal_str = f"{salary:,}".replace(",", " ")
        
        salary_rows += f"""
        <tr>
            <td><strong>{master_name}</strong></td>
            <td>{m.specialization}</td>
            <td>{master_cnt}</td>
            <td>{rev_str} ₽</td>
            <td><strong style="color:#22c55e">{sal_str} ₽</strong></td>
        </tr>"""
    
    total_salary = int(month_revenue * 0.4)
    profit = month_revenue - total_salary
    
    month_rev_str = f"{month_revenue:,}".replace(",", " ")
    total_sal_str = f"{total_salary:,}".replace(",", " ")
    profit_str = f"{profit:,}".replace(",", " ")
    
    return f"""
    <div id="tab-finances" class="tab-content">
        <div class="analytics-kpi">
            <div class="kpi-card">
                <div class="kpi-label">Выручка за месяц</div>
                <div class="kpi-value" style="color:#22c55e">{month_rev_str} ₽</div>
                <div class="kpi-trend">{month_completed} завершённых записей</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Зарплаты мастеров</div>
                <div class="kpi-value" style="color:#f59e0b">{total_sal_str} ₽</div>
                <div class="kpi-trend">40% от выручки</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Прибыль салона</div>
                <div class="kpi-value" style="color:var(--color-primary)">{profit_str} ₽</div>
                <div class="kpi-trend">{month_rev_str} - {total_sal_str}</div>
            </div>
        </div>
        
        <div class="card" style="margin-bottom:1.5rem">
            <h3 style="margin-bottom:1rem">📊 Выручка за последние 7 дней</h3>
            <div class="chart-bar">{revenue_chart}</div>
        </div>
        
        <div class="card">
            <h3 style="margin-bottom:1rem">👥 Зарплаты мастеров за месяц</h3>
            <table>
                <thead>
                    <tr>
                        <th>Мастер</th>
                        <th>Специализация</th>
                        <th>Записей</th>
                        <th>Выручка</th>
                        <th>Зарплата (40%)</th>
                    </tr>
                </thead>
                <tbody>
                    {salary_rows or '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--color-muted)">Нет данных за месяц</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>"""