# app/web/pages/admin_panel.py
"""Рендер админ-панели (/admin). Вкладки: обзор, пользователи, салоны, отзывы, аудит.
Самодостаточная страница в стиле проекта; действия постят на /api/v1/admin/*."""
import html
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    User, UserRole, Salon, Master, Service, Booking, Review, BookingStatus, AdminAudit,
)
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.styles import get_base_styles

ROLE_RU = {
    "client": "Клиент", "model": "Модель", "master": "Мастер",
    "business": "Бизнес", "admin": "Админ",
}


def _esc(v) -> str:
    return html.escape(str(v if v is not None else ""), quote=True)


def _badge(text, color):
    return f'<span style="display:inline-block;border-radius:2rem;padding:0.1rem 0.6rem;font-size:0.7rem;font-weight:700;color:#fff;background:{color}">{text}</span>'


def _active_badge(is_active):
    return _badge("активен", "#16a34a") if is_active else _badge("заблокирован", "#dc2626")


# ── ВКЛАДКА: ОБЗОР ───────────────────────────────────────────────────────────
async def _overview(db, users):
    by_role = {}
    blocked = 0
    for u in users:
        by_role[u.role.value] = by_role.get(u.role.value, 0) + 1
        if not u.is_active:
            blocked += 1

    salons_total = (await db.execute(select(func.count(Salon.id)))).scalar() or 0
    salons_active = (await db.execute(select(func.count(Salon.id)).where(Salon.is_active == True))).scalar() or 0
    bookings_total = (await db.execute(select(func.count(Booking.id)))).scalar() or 0
    reviews_total = (await db.execute(select(func.count(Review.id)))).scalar() or 0

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    b_today = (await db.execute(select(func.count(Booking.id)).where(Booking.start_time >= today))).scalar() or 0
    b_month = (await db.execute(select(func.count(Booking.id)).where(Booking.start_time >= month))).scalar() or 0
    revenue = (await db.execute(
        select(func.coalesce(func.sum(Booking.final_price), 0)).where(Booking.status == BookingStatus.COMPLETED)
    )).scalar() or 0

    def card(value, label):
        return f'<div class="stat-card"><div class="stat-value">{value}</div><div class="stat-label">{label}</div></div>'

    roles_cards = "".join(
        card(by_role.get(r, 0), ROLE_RU[r]) for r in ["client", "model", "master", "business", "admin"]
    )
    return f"""
    <div class="tab-content active" id="tab-overview">
        <h2 style="margin-bottom:1rem">Платформа</h2>
        <div class="stat-grid">
            {card(len(users), "Пользователей")}
            {card(blocked, "Заблокировано")}
            {card(f"{salons_active}/{salons_total}", "Салонов (актив/всего)")}
            {card(bookings_total, "Записей всего")}
            {card(b_today, "Записей сегодня")}
            {card(b_month, "Записей за месяц")}
            {card(f"{revenue:,}".replace(",", " ") + " ₽", "Выручка (COMPLETED)")}
            {card(reviews_total, "Отзывов")}
        </div>
        <h3 style="margin:1.5rem 0 0.75rem">Пользователи по ролям</h3>
        <div class="stat-grid">{roles_cards}</div>
    </div>
    """


# ── ВКЛАДКА: ПОЛЬЗОВАТЕЛИ ────────────────────────────────────────────────────
def _users_tab(users, me_id):
    rows = ""
    for u in users:
        opts = "".join(
            f'<option value="{r}"{" selected" if u.role.value == r else ""}>{ROLE_RU[r]}</option>'
            for r in ["client", "model", "business", "admin"]
        )
        is_self = u.id == me_id
        role_form = (
            f'<form method="post" action="/api/v1/admin/users/{u.id}/role" style="display:inline-flex;gap:0.25rem">'
            f'<select name="role" {"disabled" if is_self else ""}>{opts}</select>'
            f'<button class="btn-mini" {"disabled" if is_self else ""}>OK</button></form>'
            if u.role.value != "master" else '<span class="text-muted">мастер</span>'
        )
        toggle = (
            f'<form method="post" action="/api/v1/admin/users/{u.id}/toggle-active" style="display:inline">'
            f'<button class="btn-mini" {"disabled" if is_self else ""}>{"Разблок." if not u.is_active else "Блок."}</button></form>'
        )
        reset = (
            f'<form method="post" action="/api/v1/admin/users/{u.id}/reset-password" style="display:inline">'
            f'<button class="btn-mini">Сброс пароля</button></form>'
        )
        delete = (
            f'<form method="post" action="/api/v1/admin/users/{u.id}/delete" style="display:inline" '
            f'onsubmit="return confirm(\'Удалить {_esc(u.phone)}?\')">'
            f'<button class="btn-mini btn-danger" {"disabled" if is_self else ""}>Удалить</button></form>'
        )
        me_mark = ' <span class="text-muted">(вы)</span>' if is_self else ""
        rows += f"""<tr>
            <td>{u.id}</td>
            <td>{_esc(u.phone)}{me_mark}</td>
            <td>{_esc(u.full_name) or "—"}</td>
            <td>{role_form}</td>
            <td>{_active_badge(u.is_active)}</td>
            <td style="white-space:nowrap">{toggle} {reset} {delete}</td>
        </tr>"""
    return f"""
    <div class="tab-content" id="tab-users">
        <h2 style="margin-bottom:1rem">Пользователи ({len(users)})</h2>
        <input id="userFilter" onkeyup="filterTable('userFilter','usersTable')" placeholder="Поиск по телефону/имени…"
               style="width:100%;max-width:360px;padding:0.5rem 0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;margin-bottom:1rem">
        <div style="overflow-x:auto"><table id="usersTable">
            <thead><tr><th>ID</th><th>Телефон</th><th>Имя</th><th>Роль</th><th>Статус</th><th>Действия</th></tr></thead>
            <tbody>{rows}</tbody>
        </table></div>
    </div>
    """


# ── ВКЛАДКА: САЛОНЫ ──────────────────────────────────────────────────────────
def _salons_tab(salons, owner_phone_by_id):
    rows = ""
    for s in salons:
        owner = owner_phone_by_id.get(s.creator_id, "—") if s.creator_id else "нет"
        owner_form = (
            f'<form method="post" action="/api/v1/admin/salons/{s.id}/owner" style="display:inline-flex;gap:0.25rem">'
            f'<input name="owner_phone" placeholder="+7… (пусто = снять)" value="" '
            f'style="padding:0.3rem 0.5rem;border:1px solid var(--color-border);border-radius:0.4rem;width:150px">'
            f'<button class="btn-mini">Сменить</button></form>'
        )
        toggle = (
            f'<form method="post" action="/api/v1/admin/salons/{s.id}/toggle-active" style="display:inline">'
            f'<button class="btn-mini">{"Деактив." if s.is_active else "Активир."}</button></form>'
        )
        delete = (
            f'<form method="post" action="/api/v1/admin/salons/{s.id}/delete" style="display:inline" '
            f'onsubmit="return confirm(\'Удалить салон «{_esc(s.name)}»?\')">'
            f'<button class="btn-mini btn-danger">Удалить</button></form>'
        )
        rows += f"""<tr>
            <td>{s.id}</td>
            <td>{_esc(s.name)}</td>
            <td>{_esc(owner)}</td>
            <td>⭐ {s.rating} ({s.reviews_count})</td>
            <td>{_active_badge(s.is_active)}</td>
            <td style="white-space:nowrap">{owner_form} {toggle} {delete}</td>
        </tr>"""
    return f"""
    <div class="tab-content" id="tab-salons">
        <h2 style="margin-bottom:1rem">Салоны ({len(salons)})</h2>
        <div style="overflow-x:auto"><table>
            <thead><tr><th>ID</th><th>Название</th><th>Владелец</th><th>Рейтинг</th><th>Статус</th><th>Действия</th></tr></thead>
            <tbody>{rows}</tbody>
        </table></div>
    </div>
    """


# ── ВКЛАДКА: ОТЗЫВЫ ──────────────────────────────────────────────────────────
def _reviews_tab(reviews, client_by_id, master_name_by_id, salon_name_by_id):
    rows = ""
    for r in reviews:
        stars = "⭐" * int(r.rating or 0)
        delete = (
            f'<form method="post" action="/api/v1/admin/reviews/{r.id}/delete" style="display:inline" '
            f'onsubmit="return confirm(\'Удалить отзыв #{r.id}?\')">'
            f'<button class="btn-mini btn-danger">Удалить</button></form>'
        )
        rows += f"""<tr>
            <td>{r.id}</td>
            <td>{_esc(client_by_id.get(r.client_id, "—"))}</td>
            <td>{_esc(master_name_by_id.get(r.master_id, "—"))}</td>
            <td>{_esc(salon_name_by_id.get(r.salon_id, "—"))}</td>
            <td>{stars}</td>
            <td>{_esc(r.comment) or "—"}</td>
            <td>{delete}</td>
        </tr>"""
    return f"""
    <div class="tab-content" id="tab-reviews">
        <h2 style="margin-bottom:1rem">Отзывы ({len(reviews)})</h2>
        <div style="overflow-x:auto"><table>
            <thead><tr><th>ID</th><th>Клиент</th><th>Мастер</th><th>Салон</th><th>Оценка</th><th>Комментарий</th><th></th></tr></thead>
            <tbody>{rows}</tbody>
        </table></div>
    </div>
    """


# ── ВКЛАДКА: АУДИТ ───────────────────────────────────────────────────────────
def _audit_tab(audits, actor_by_id):
    rows = ""
    for a in audits:
        when = a.created_at.strftime("%d.%m.%Y %H:%M") if a.created_at else ""
        rows += f"""<tr>
            <td style="white-space:nowrap">{when}</td>
            <td>{_esc(actor_by_id.get(a.actor_id, "#"+str(a.actor_id)))}</td>
            <td>{_esc(a.action)}</td>
            <td>{_esc(a.target_type)} #{a.target_id if a.target_id is not None else "—"}</td>
            <td>{_esc(a.detail)}</td>
        </tr>"""
    body = rows or '<tr><td colspan="5" class="text-muted">Пока нет записей</td></tr>'
    return f"""
    <div class="tab-content" id="tab-audit">
        <h2 style="margin-bottom:1rem">Аудит действий ({len(audits)})</h2>
        <div style="overflow-x:auto"><table>
            <thead><tr><th>Когда</th><th>Админ</th><th>Действие</th><th>Объект</th><th>Детали</th></tr></thead>
            <tbody>{body}</tbody>
        </table></div>
    </div>
    """


def _banner(q):
    ok = q.get("ok"); err = q.get("err")
    temp_pw = q.get("temp_pw"); temp_for = q.get("temp_for")
    out = ""
    if err:
        out += f'<div class="alert alert-err">⚠️ {_esc(err)}</div>'
    if ok:
        out += f'<div class="alert alert-ok">✅ {_esc(ok)}</div>'
    if temp_pw:
        out += (f'<div class="alert alert-ok">🔑 Временный пароль для {_esc(temp_for)}: '
                f'<code style="font-weight:700">{_esc(temp_pw)}</code> — передайте пользователю, он виден один раз.</div>')
    return out


# ── СБОРКА СТРАНИЦЫ ──────────────────────────────────────────────────────────
async def render_admin_panel(db: AsyncSession, user, q) -> str:
    users = (await db.execute(select(User).order_by(User.role, User.id))).scalars().all()
    salons = (await db.execute(select(Salon).order_by(Salon.id))).scalars().all()
    reviews = (await db.execute(select(Review).order_by(Review.created_at.desc()).limit(200))).scalars().all()
    masters = (await db.execute(select(Master))).scalars().all()
    audits = (await db.execute(select(AdminAudit).order_by(AdminAudit.created_at.desc()).limit(100))).scalars().all()

    user_by_id = {u.id: u for u in users}
    phone_by_id = {u.id: u.phone for u in users}
    name_by_uid = {u.id: (u.full_name or u.phone) for u in users}
    salon_name_by_id = {s.id: s.name for s in salons}
    master_name_by_id = {m.id: name_by_uid.get(m.user_id, "Мастер") for m in masters}

    overview = await _overview(db, users)
    users_tab = _users_tab(users, user.id)
    salons_tab = _salons_tab(salons, phone_by_id)
    reviews_tab = _reviews_tab(reviews, phone_by_id, master_name_by_id, salon_name_by_id)
    audit_tab = _audit_tab(audits, phone_by_id)
    _tab = q.get("tab", "overview")
    active_tab = _tab if _tab in {"overview", "users", "salons", "reviews", "audit"} else "overview"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Админ-панель — руми</title>
    {get_base_styles()}
    <style>
        .admin-main {{ max-width:1280px; margin:0 auto; padding:2rem 1.5rem }}
        .tab-nav {{ display:flex; gap:0.25rem; border-bottom:1px solid var(--color-border); margin:1rem 0 1.5rem; flex-wrap:wrap }}
        .tab-btn {{ padding:0.75rem 1.25rem; border:none; background:transparent; cursor:pointer; font-size:0.9rem; font-weight:500; color:var(--color-muted); border-bottom:2px solid transparent }}
        .tab-btn.active {{ color:var(--color-primary); border-bottom-color:var(--color-primary) }}
        .tab-content {{ display:none }}
        .tab-content.active {{ display:block }}
        .stat-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:1rem }}
        .stat-card {{ background:var(--color-surface); border:1px solid var(--color-border); border-radius:1rem; padding:1.25rem; text-align:center }}
        .stat-value {{ font-size:1.6rem; font-weight:700; color:var(--color-primary) }}
        .stat-label {{ font-size:0.8rem; color:var(--color-muted); margin-top:0.25rem }}
        table {{ width:100%; border-collapse:collapse; font-size:0.875rem }}
        th {{ text-align:left; padding:0.6rem; border-bottom:2px solid var(--color-border); font-weight:600; color:var(--color-heading); white-space:nowrap }}
        td {{ padding:0.6rem; border-bottom:1px solid var(--color-border); vertical-align:middle }}
        select, .btn-mini {{ font-size:0.8rem; padding:0.3rem 0.55rem; border:1px solid var(--color-border); border-radius:0.4rem; background:#fff; cursor:pointer }}
        .btn-mini:hover {{ border-color:var(--color-primary); color:var(--color-primary) }}
        .btn-mini:disabled {{ opacity:0.4; cursor:not-allowed }}
        .btn-danger:hover {{ border-color:#dc2626; color:#dc2626 }}
        .alert {{ padding:0.75rem 1rem; border-radius:0.5rem; margin-bottom:0.75rem; font-size:0.875rem }}
        .alert-ok {{ background:#dcfce7; color:#166534; border:1px solid #86efac }}
        .alert-err {{ background:#fee2e2; color:#991b1b; border:1px solid #fca5a5 }}
        .text-muted {{ color:var(--color-muted) }}
    </style>
</head>
<body>
    {render_header("admin")}
    <main class="admin-main">
        <h1 class="text-display" style="font-size:1.75rem">🛡️ Админ-панель</h1>
        <p class="text-muted">{_esc(user.full_name or user.phone)} · роль ADMIN</p>
        {_banner(q)}
        <div class="tab-nav">
            <button class="tab-btn" data-tab="overview" onclick="switchTab('overview')">📊 Обзор</button>
            <button class="tab-btn" data-tab="users" onclick="switchTab('users')">👥 Пользователи</button>
            <button class="tab-btn" data-tab="salons" onclick="switchTab('salons')">🏢 Салоны</button>
            <button class="tab-btn" data-tab="reviews" onclick="switchTab('reviews')">💬 Отзывы</button>
            <button class="tab-btn" data-tab="audit" onclick="switchTab('audit')">📝 Аудит</button>
        </div>
        {overview}
        {users_tab}
        {salons_tab}
        {reviews_tab}
        {audit_tab}
    </main>
    {render_footer(user)}
    <script>
        function switchTab(name) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-' + name));
            history.replaceState(null, '', '/admin?tab=' + name);
        }}
        function filterTable(inputId, tableId) {{
            var q = document.getElementById(inputId).value.toLowerCase();
            document.querySelectorAll('#' + tableId + ' tbody tr').forEach(function(tr) {{
                tr.style.display = tr.textContent.toLowerCase().indexOf(q) > -1 ? '' : 'none';
            }});
        }}
        switchTab({active_tab!r});
    </script>
</body>
</html>"""
