# app/web/pages/master/dashboard.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.models.models import Master, Booking, BookingStatus, Service as ServiceModel, User as UserModel
from app.services.inventory_service import InventoryService
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles

STATUS_LABELS = {
    BookingStatus.PENDING: ("Ожидает", "#f59e0b"),
    BookingStatus.CONFIRMED: ("Подтверждена", "#3b82f6"),
    BookingStatus.COMPLETED: ("Завершена", "#22c55e"),
    BookingStatus.CANCELLED: ("Отменена", "#9ca3af"),
    BookingStatus.NO_SHOW: ("Неявка", "#ef4444"),
}


async def render_master_dashboard(db: AsyncSession, user) -> str:
    """Кабинет мастера: записи на сегодня + напоминание списать расходники."""

    master = (await db.execute(select(Master).where(Master.user_id == user.id))).scalar_one_or_none()
    if not master:
        return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">{get_base_styles()}</head>
        <body>{render_header("master", user)}{render_sidebar("master", user)}
        <main style="margin-right:16rem;padding-top:3rem"><div class="section-container">
        <h1>Профиль мастера не найден</h1><p class="text-muted">Обратитесь к владельцу салона, чтобы он добавил вас как мастера.</p>
        </div></main>{render_footer(user)}</body></html>"""

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    today_result = await db.execute(
        select(Booking, ServiceModel)
        .join(ServiceModel, ServiceModel.id == Booking.service_id)
        .where(
            Booking.master_id == master.id,
            Booking.start_time >= today, Booking.start_time < tomorrow,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
        )
        .order_by(Booking.start_time)
    )
    today_bookings = today_result.all()

    unreported_result = await db.execute(
        select(Booking, ServiceModel)
        .join(ServiceModel, ServiceModel.id == Booking.service_id)
        .where(
            Booking.master_id == master.id,
            Booking.status == BookingStatus.COMPLETED,
            Booking.consumption_reported == False,
        )
        .order_by(Booking.start_time.desc())
        .limit(20)
    )
    unreported = unreported_result.all()

    client_ids = {b.client_id for b, s in today_bookings} | {b.client_id for b, s in unreported}
    client_names = {}
    for cid in client_ids:
        cu = (await db.execute(select(UserModel).where(UserModel.id == cid))).scalar_one_or_none()
        client_names[cid] = cu.full_name or cu.phone if cu else "—"

    today_rows = ""
    for b, s in today_bookings:
        label, color = STATUS_LABELS.get(b.status, (b.status.value, "#9ca3af"))
        action = ""
        if b.status == BookingStatus.COMPLETED and not b.consumption_reported:
            action = f'<button class="btn-outline" style="padding:0.4rem 0.9rem;font-size:0.8rem" onclick="openConsumptionModal({b.id})">Списать расходники</button>'
        today_rows += f"""
        <tr>
            <td>{b.start_time.strftime('%H:%M')}</td>
            <td>{client_names.get(b.client_id, '—')}</td>
            <td>{s.name}</td>
            <td><span style="color:{color};font-weight:600">{label}</span></td>
            <td>{action}</td>
        </tr>"""

    unreported_rows = ""
    for b, s in unreported:
        unreported_rows += f"""
        <tr>
            <td>{b.start_time.strftime('%d.%m.%Y %H:%M')}</td>
            <td>{client_names.get(b.client_id, '—')}</td>
            <td>{s.name}</td>
            <td><button class="btn-primary" style="padding:0.4rem 0.9rem;font-size:0.8rem" onclick="openConsumptionModal({b.id})">Списать расходники</button></td>
        </tr>"""

    stock = await InventoryService.get_master_stock(db, master.id)
    stock_options = "".join(
        f'<div class="consumption-line" data-item-id="{i.id}" style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.5rem">'
        f'<label style="flex:1;font-size:0.875rem">{i.name} <span class="text-muted">(остаток {i.quantity:g} {i.unit})</span></label>'
        f'<input type="number" step="0.01" min="0" class="consumption-qty" placeholder="0" style="width:6rem;padding:0.4rem;border:1px solid var(--color-border);border-radius:0.4rem">'
        f'<span class="text-muted" style="width:2.5rem">{i.unit}</span>'
        f'</div>' for i in stock
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Кабинет мастера — руми</title>
    {get_base_styles()}
    <style>
        .analytics-kpi {{ display:flex; gap:1rem; margin-bottom:1.5rem; flex-wrap:wrap }}
        .kpi-card {{ background:var(--color-surface); border:1px solid var(--color-border); border-radius:1rem; padding:1.25rem 1.5rem; flex:1; min-width:150px }}
        .kpi-value {{ font-size:1.75rem; font-weight:700; color:var(--color-heading) }}
        .kpi-label {{ font-size:0.8rem; color:var(--color-muted) }}
        table {{ width:100%; border-collapse:collapse }}
        th {{ text-align:left; padding:0.75rem; border-bottom:2px solid var(--color-border); font-weight:600; color:var(--color-heading); white-space:nowrap }}
        td {{ padding:0.75rem; border-bottom:1px solid var(--color-border) }}
        .modal-overlay {{ display:none; position:fixed; inset:0; background:rgba(0,0,0,0.5); z-index:100; align-items:center; justify-content:center }}
        .modal-overlay.open {{ display:flex }}
        .modal-box {{ background:var(--color-surface); border-radius:1rem; padding:1.5rem; max-width:480px; width:90%; max-height:80vh; overflow-y:auto }}
    </style>
</head>
<body>
    {render_header("master", user)}
    {render_sidebar("master", user)}

    <main style="margin-right:16rem;padding-top:2rem">
        <div class="section-container">
            <h1 class="text-display" style="font-size:2rem;margin-bottom:0.25rem">Кабинет мастера</h1>
            <p class="text-muted" style="margin-bottom:1.5rem">{master.specialization} · <a href="/master/inventory">Мой склад →</a></p>

            <div class="analytics-kpi">
                <div class="kpi-card"><div class="kpi-label">Записей сегодня</div><div class="kpi-value">{len(today_bookings)}</div></div>
                <div class="kpi-card"><div class="kpi-label">Не списано расходников</div><div class="kpi-value" style="color:#f59e0b">{len(unreported)}</div></div>
            </div>

            <div class="card" style="overflow-x:auto;margin-bottom:1.5rem">
                <h3 style="margin-bottom:1rem">Записи на сегодня</h3>
                <table>
                    <thead><tr><th>Время</th><th>Клиент</th><th>Услуга</th><th>Статус</th><th></th></tr></thead>
                    <tbody>{today_rows or '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--color-muted)">На сегодня записей нет</td></tr>'}</tbody>
                </table>
            </div>

            {'<div class="card" style="overflow-x:auto;border:2px solid #f59e0b">'
             '<h3 style="margin-bottom:1rem">⚠️ Требуют списания расходников</h3>'
             '<table><thead><tr><th>Дата</th><th>Клиент</th><th>Услуга</th><th></th></tr></thead>'
             f'<tbody>{unreported_rows}</tbody></table></div>' if unreported_rows else ''}
        </div>
    </main>

    {render_footer(user)}

    <div class="modal-overlay" id="consumptionModal">
        <div class="modal-box">
            <h3 style="margin-bottom:0.25rem">Списание расходников</h3>
            <p class="text-muted" style="margin-bottom:1rem;font-size:0.85rem">Укажите, сколько фактически потрачено. Пустые/нулевые позиции не списываются.</p>
            <div id="consumptionItems">{stock_options or '<p class="text-muted">На складе пока нет позиций — попросите администратора добавить номенклатуру.</p>'}</div>
            <div style="display:flex;gap:0.5rem;margin-top:1rem">
                <button class="btn-outline" style="flex:1" onclick="closeConsumptionModal()">Отмена</button>
                <button class="btn-primary" style="flex:1" onclick="submitConsumption()">Списать</button>
            </div>
        </div>
    </div>

    <script>
        let currentBookingId = null;
        function openConsumptionModal(bookingId) {{
            currentBookingId = bookingId;
            document.getElementById('consumptionModal').classList.add('open');
        }}
        function closeConsumptionModal() {{
            document.getElementById('consumptionModal').classList.remove('open');
            currentBookingId = null;
        }}
        async function submitConsumption() {{
            if (!currentBookingId) return;
            const items = [];
            document.querySelectorAll('.consumption-line').forEach(line => {{
                const qty = parseFloat(line.querySelector('.consumption-qty').value);
                if (qty > 0) {{
                    items.push({{ item_id: parseInt(line.dataset.itemId), quantity: qty }});
                }}
            }});
            if (items.length === 0) {{ alert('Укажите хотя бы одну потраченную позицию'); return; }}
            try {{
                const res = await fetch('/api/v1/inventory/my/consumption', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ booking_id: currentBookingId, items: items }})
                }});
                if (res.ok) {{
                    location.reload();
                }} else {{
                    const data = await res.json().catch(() => ({{}}));
                    alert(data.detail || 'Не удалось списать расходники');
                }}
            }} catch (err) {{
                alert('Ошибка соединения с сервером');
            }}
        }}
    </script>
</body>
</html>"""
