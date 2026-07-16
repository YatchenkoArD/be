# app/web/pages/business/dashboard.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.models import (
    Salon, Master, Service, Promotion, Booking, Review, BookingStatus,
    SalonMember, User as UserModel,
)
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.web.pages.business.utils import get_masters_data, get_master_ids
from app.web.pages.business.tabs.overview import render_overview_tab
from app.web.pages.business.tabs.analytics import render_analytics_tab
from app.web.pages.business.tabs.promos import render_promos_tab
from app.web.pages.business.tabs.reviews import render_reviews_tab
from app.web.pages.business.tabs.schedule import render_schedule_tab
from app.web.pages.business.tabs.employees import render_employees_tab
from app.web.pages.business.tabs.services import render_services_tab
from app.web.pages.business.tabs.records import render_records_tab
from app.web.pages.business.tabs.warehouse import render_warehouse_tab
from app.web.pages.business.tabs.payroll import render_payroll_tab
from app.web.pages.business.tabs.cost import render_cost_tab
from app.web.pages.business.tabs.promo_models import render_promo_models_tab
from app.web.pages.business.tabs.chat import render_chat_tab
from app.web.pages.business.tabs.staff import render_staff_tab
from app.crm.tabs.clients import render_crm_tab


async def render_business_dashboard(db: AsyncSession, user, salon: Salon, membership: SalonMember, query_params=None) -> str:
    """Бизнес-панель с аналитикой. `membership` — активное членство текущего
    пользователя в этом салоне (owner/admin), уже проверенное вызывающим кодом.
    `query_params` — request.query_params страницы (используется вкладкой
    «Записи» для фильтров и для восстановления активной вкладки после submit)."""

    query_params = query_params or {}
    active_tab = query_params.get("tab", "overview")
    records_filters = {
        "date_from": query_params.get("date_from"),
        "date_to": query_params.get("date_to"),
        "master_id": query_params.get("master_id"),
        "status": query_params.get("status"),
    }
    warehouse_filters = {
        "audit_id": query_params.get("audit_id"),
    }
    period_raw = query_params.get("period")

    perms = {
        key: (membership.is_creator or membership.permissions.get(key, False))
        for key in (
            "manage_salon", "manage_owners", "manage_admins", "manage_masters",
            "manage_schedule", "manage_promotions", "manage_reviews",
            "view_finances", "manage_tariff", "view_audit_log",
            "manage_inventory", "manage_payroll",
        )
    }

    # Салоны, доступные пользователю — для свитчера в шапке
    other_memberships = (await db.execute(
        select(SalonMember, Salon)
        .join(Salon, Salon.id == SalonMember.salon_id)
        .where(SalonMember.user_id == user.id, SalonMember.is_active == True)
        .order_by(Salon.name)
    )).all()

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

    # Рендерим вкладки. Финансы/Аналитика (выручка) и Сотрудники — только при
    # наличии прав: рендер-функция вообще не вызывается, чтобы данные физически
    # не попадали в HTML-ответ для тех, кому нельзя (не просто скрывались JS).
    tabs_html = []
    tab_buttons = []

    tab_buttons.append(('overview', '📊 Обзор', True))
    tabs_html.append(await render_overview_tab(db, salon, masters, master_ids, services_count, promotions, today_bookings))

    tab_buttons.append(('analytics', '📈 Аналитика', perms["view_finances"]))
    if perms["view_finances"]:
        tabs_html.append(await render_analytics_tab(db, salon, master_ids))

    tab_buttons.append(('schedule', '📅 Расписание', True))
    tabs_html.append(await render_schedule_tab(db, salon, masters, perms["manage_schedule"], salon.id))

    tab_buttons.append(('employees', '💇 Мастера', True))
    tabs_html.append(await render_employees_tab(db, salon, masters))

    tab_buttons.append(('services', '✂️ Услуги', True))
    tabs_html.append(await render_services_tab(db, salon, masters))

    tab_buttons.append(('payroll', '💰 Зарплаты', perms["manage_payroll"]))
    if perms["manage_payroll"]:
        tabs_html.append(await render_payroll_tab(db, salon, masters, master_ids, period_raw))

    tab_buttons.append(('cost', '📉 Себестоимость', perms["view_finances"]))
    if perms["view_finances"]:
        tabs_html.append(await render_cost_tab(db, salon, masters, master_ids, period_raw))

    tab_buttons.append(('records', '🧾 Записи', True))
    tabs_html.append(await render_records_tab(db, salon, masters, master_ids, records_filters))

    tab_buttons.append(('warehouse', '📦 Склад', perms["manage_inventory"]))
    if perms["manage_inventory"]:
        tabs_html.append(await render_warehouse_tab(db, salon, masters, master_ids, warehouse_filters))

    tab_buttons.append(('chat', '💬 Чат', True))
    tabs_html.append(await render_chat_tab(db, salon, user))

    tab_buttons.append(('staff', '👤 Сотрудники', perms["manage_admins"] or perms["manage_owners"]))
    if perms["manage_admins"] or perms["manage_owners"]:
        tabs_html.append(await render_staff_tab(db, salon, user, membership, perms))

    tab_buttons.append(('models', '🎭 Модели', perms["manage_masters"]))
    if perms["manage_masters"]:
        tabs_html.append(await render_promo_models_tab(db, salon))

    tab_buttons.append(('promos', f'🎉 Акции ({len(promotions)})', True))
    tabs_html.append(render_promos_tab(promotions))

    tab_buttons.append(('reviews', f'⭐ Отзывы ({len(reviews)})', True))
    tabs_html.append(await render_reviews_tab(db, reviews, salon))

    tab_buttons.append(('crm', '👥 Клиенты', True))
    tabs_html.append(await render_crm_tab(db, salon, masters, master_ids))

    visible_slugs = [slug for slug, _label, visible in tab_buttons if visible]
    # Если вкладка из ?tab= недоступна (гейтится правом) или не существует —
    # откатываемся на Обзор, он есть всегда.
    if active_tab not in visible_slugs:
        active_tab = "overview"

    nav_buttons_html = "".join(
        f'<button class="tab-btn{" active" if slug == active_tab else ""}" onclick="switchTab(\'{slug}\')">{label}</button>'
        for slug, label, visible in tab_buttons if visible
    )

    # Проставляем class="active" тому <div id="tab-{active_tab}" ...>, который
    # пришёл из query-параметра ?tab= (по умолчанию — overview).
    tabs_body_html = "\n".join(tabs_html).replace(
        f'id="tab-{active_tab}" class="tab-content"',
        f'id="tab-{active_tab}" class="tab-content active"',
        1,
    )

    switcher_html = ""
    if len(other_memberships) > 1:
        options = "".join(
            f'<option value="{s.id}"{" selected" if s.id == salon.id else ""}>{s.name}</option>'
            for _, s in other_memberships
        )
        switcher_html = f"""
        <select onchange="window.location.href='/business/dashboard?salon_id=' + this.value" style="padding:0.5rem 0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;font-size:0.85rem">
            {options}
        </select>"""

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
    {render_header("business")}
    {render_sidebar("business", user)}
    <main style="margin-right:16rem;padding-top:2rem">
        <div class="section-container">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:0.75rem">
                <div>
                    <h1 class="text-display" style="font-size:2rem">{salon.name}</h1>
                    <p class="text-muted">Панель управления · ⭐ {salon.rating} ({salon.reviews_count} отзывов)</p>
                </div>
                <div style="display:flex;align-items:center;gap:0.75rem">
                    {switcher_html}
                    {f'<a href="/business/my-salon?salon_id={salon.id}" class="btn-outline">✏️ Редактировать салон</a>' if perms["manage_salon"] else ''}
                </div>
            </div>

            <!-- Вкладки -->
            <div class="tab-nav">
                {nav_buttons_html}
            </div>

            {tabs_body_html}
        </div>
    </main>

    {render_footer(user)}

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
