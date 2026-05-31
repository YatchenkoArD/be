# app/web/pages/business/dashboard.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.models import Salon, Master, Service, Promotion, Booking, Review, BookingStatus, User as UserModel
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.web.pages.business.utils import get_masters_data, get_master_ids
from app.web.pages.business.tabs.overview import render_overview_tab
from app.web.pages.business.tabs.analytics import render_analytics_tab
from app.web.pages.business.tabs.masters import render_masters_tab
from app.web.pages.business.tabs.promos import render_promos_tab
from app.web.pages.business.tabs.reviews import render_reviews_tab
from app.web.pages.business.tabs.schedule import render_schedule_tab
from app.web.pages.business.tabs.employees import render_employees_tab
from app.web.pages.business.tabs.services import render_services_tab
from app.web.pages.business.tabs.finances import render_finances_tab


async def render_business_dashboard(db: AsyncSession, user, salon: Salon) -> str:
    """Бизнес-панель с аналитикой."""
    
    # Общие данные
    masters, masters_rows = await get_masters_data(db, salon.id)
    master_ids = get_master_ids(masters)
    
    services_count = 0
    if master_ids:
        svc = await db.execute(select(func.count(Service.id)).where(Service.master_id.in_(master_ids)))
        services_count = svc.scalar() or 0
    
    promos_result = await db.execute(select(Promotion).where(Promotion.salon_id == salon.id))
    promotions = promos_result.scalars().all()
    
    reviews_result = await db.execute(
        select(Review).where(Review.salon_id == salon.id).order_by(Review.created_at.desc())
    )
    reviews = reviews_result.scalars().all()
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    today_bookings = 0
    if master_ids:
        tb = await db.execute(select(func.count(Booking.id)).where(
            Booking.master_id.in_(master_ids), 
            Booking.start_time >= today, 
            Booking.start_time < tomorrow
        ))
        today_bookings = tb.scalar() or 0
    
    # Рендерим вкладки
    overview_html = await render_overview_tab(db, salon, masters, master_ids, services_count, promotions, today_bookings)
    analytics_html = await render_analytics_tab(db, salon, master_ids)
    schedule_html = await render_schedule_tab(db, salon, masters)
    employees_html = await render_employees_tab(db, salon, masters)
    services_tab_html = await render_services_tab(db, salon, masters)
    finances_html = await render_finances_tab(db, salon, masters, master_ids)
    masters_tab_html = render_masters_tab(masters_rows)
    promos_tab_html = render_promos_tab(promotions)
    reviews_tab_html = await render_reviews_tab(db, reviews, salon)
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Бизнес-панель — {salon.name} — руми</title>
    {get_base_styles()}
    <style>
        .tab-nav {{ display:flex; gap:0.25rem; border-bottom:1px solid var(--color-border); margin-bottom:2rem; flex-wrap:wrap }}
        .tab-btn {{ padding:0.75rem 1.5rem; border:none; background:transparent; cursor:pointer; font-size:0.875rem; font-weight:500; color:var(--color-muted); border-bottom:2px solid transparent; transition:all 0.2s; white-space:nowrap }}
        .tab-btn.active {{ color:var(--color-primary); border-bottom-color:var(--color-primary) }}
        .tab-content {{ display:none }}
        .tab-content.active {{ display:block }}
        .stat-card {{ background:var(--color-surface); border:1px solid var(--color-border); border-radius:1rem; padding:1.5rem; text-align:center }}
        .stat-value {{ font-size:2rem; font-weight:700; color:var(--color-primary) }}
        .stat-label {{ font-size:0.85rem; color:var(--color-muted); margin-top:0.25rem }}
        .promo-badge {{ display:inline-block; border-radius:2rem; padding:0.125rem 0.5rem; font-size:0.625rem; font-weight:700; color:white; background:linear-gradient(135deg,var(--color-primary),var(--color-accent)) }}
        table {{ width:100%; border-collapse:collapse }}
        th {{ text-align:left; padding:0.75rem; border-bottom:2px solid var(--color-border); font-weight:600; color:var(--color-heading); white-space:nowrap }}
        td {{ padding:0.75rem; border-bottom:1px solid var(--color-border) }}
        .chart-bar {{ height:200px; display:flex; align-items:flex-end; gap:1rem; padding:1rem 0 }}
        .chart-column {{ flex:1; display:flex; flex-direction:column; align-items:center; gap:0.25rem; min-width:40px }}
        .chart-fill {{ width:100%; max-width:3.5rem; border-radius:0.5rem 0.5rem 0 0; background:linear-gradient(to top,var(--color-primary),var(--color-accent)); transition:height 0.3s }}
        .chart-fill.highest {{ background:linear-gradient(to top,#22c55e,#4ade80) }}
        .chart-fill.prev {{ background:var(--color-border) }}
        .chart-label {{ font-size:0.75rem; color:var(--color-muted) }}
        .chart-value {{ font-size:0.7rem; font-weight:600; color:var(--color-heading); white-space:nowrap }}
        .rating-summary {{ display:flex; gap:1rem; align-items:center; margin-bottom:1.5rem; flex-wrap:wrap }}
        .rating-big {{ font-size:3rem; font-weight:800; color:var(--color-primary); line-height:1 }}
        .analytics-kpi {{ display:flex; gap:1rem; margin-bottom:1.5rem; flex-wrap:wrap }}
        .kpi-card {{ background:var(--color-surface); border:1px solid var(--color-border); border-radius:1rem; padding:1.25rem 1.5rem; flex:1; min-width:150px }}
        .kpi-value {{ font-size:1.75rem; font-weight:700; color:var(--color-heading) }}
        .kpi-label {{ font-size:0.8rem; color:var(--color-muted) }}
        .kpi-trend {{ font-size:0.85rem; font-weight:600 }}
        .legend {{ display:flex; gap:1.5rem; align-items:center; margin-bottom:1rem; font-size:0.85rem }}
        .legend-dot {{ width:12px; height:12px; border-radius:3px; display:inline-block }}
    </style>
</head>
<body>
    {render_header("business", user)}
    {render_sidebar("business")}
    
    <main style="margin-right:16rem;padding-top:2rem">
        <div class="section-container">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
                <div>
                    <h1 class="text-display" style="font-size:2rem">{salon.name}</h1>
                    <p class="text-muted">Панель управления · ⭐ {salon.rating} ({salon.reviews_count} отзывов)</p>
                </div>
                <a href="/business/my-salon" class="btn-outline">✏️ Редактировать салон</a>
            </div>
            
            <!-- Вкладки -->
            <div class="tab-nav">
                <button class="tab-btn active" onclick="switchTab('overview')">📊 Обзор</button>
                <button class="tab-btn" onclick="switchTab('analytics')">📈 Аналитика</button>
                <button class="tab-btn" onclick="switchTab('schedule')">📅 Расписание</button>
                <button class="tab-btn" onclick="switchTab('employees')">👥 Сотрудники ({len(masters)})</button>
                <button class="tab-btn" onclick="switchTab('services')">💇 Услуги</button>
                <button class="tab-btn" onclick="switchTab('finances')">💰 Финансы</button>
                <button class="tab-btn" onclick="switchTab('masters')">👤 Мастера ({len(masters)})</button>
                <button class="tab-btn" onclick="switchTab('promos')">🎉 Акции ({len(promotions)})</button>
                <button class="tab-btn" onclick="switchTab('reviews')">💬 Отзывы ({len(reviews)})</button>
            </div>
            
            {overview_html}
            {analytics_html}
            {schedule_html}
            {employees_html}
            {services_tab_html}
            {finances_html}
            {masters_tab_html}
            {promos_tab_html}
            {reviews_tab_html}
        </div>
    </main>
    
    {render_footer()}
    
    <script>
        function switchTab(tabName) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById('tab-' + tabName).classList.add('active');
            event.target.classList.add('active');
        }}
        
        function showDayDetails(index, dayName, revenue, prevRevenue) {{
            const diff = revenue - prevRevenue;
            const trend = diff > 0 ? '▲' : diff < 0 ? '▼' : '—';
            alert(`${{dayName}}\\nВыручка: ${{revenue.toLocaleString()}} ₽\\nПрошлая неделя: ${{prevRevenue.toLocaleString()}} ₽\\n${{trend}} ${{Math.abs(diff).toLocaleString()}} ₽`);
        }}
    </script>
</body>
</html>"""
    
    return html