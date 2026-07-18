# app/web/pages/business/tabs/records.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.models.models import Booking, BookingStatus, Service as ServiceModel, User as UserModel
from app.web.components.icons import (
    ICON_CALENDAR_DAYS,
    ICON_USER_CHECK,
    ICON_FILTER,
)

STATUS_LABELS = {
    BookingStatus.PENDING: ("Ожидает", "pending"),
    BookingStatus.CONFIRMED: ("Подтверждена", "confirmed"),
    BookingStatus.COMPLETED: ("Завершена", "completed"),
    BookingStatus.CANCELLED: ("Отменена", "cancelled"),
    BookingStatus.NO_SHOW: ("Неявка", "no_show"),
}


async def render_records_tab(db: AsyncSession, salon, masters, master_ids, filters: dict) -> str:
    """Вкладка «Записи» — полный список броней салона с фильтрами."""

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    default_from = today - timedelta(days=30)
    default_to = today + timedelta(days=1)

    def parse_date(value, fallback):
        if not value:
            return fallback
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return fallback

    date_from = parse_date(filters.get("date_from"), default_from)
    date_to = parse_date(filters.get("date_to"), default_to - timedelta(days=1)) + timedelta(days=1)
    filter_master_id = filters.get("master_id") or ""
    filter_status = filters.get("status") or ""

    rows_data = []
    if master_ids:
        query = (
            select(Booking, ServiceModel)
            .join(ServiceModel, ServiceModel.id == Booking.service_id)
            .where(
                Booking.master_id.in_(master_ids),
                Booking.start_time >= date_from,
                Booking.start_time < date_to,
            )
        )
        if filter_master_id.isdigit():
            query = query.where(Booking.master_id == int(filter_master_id))
        if filter_status:
            try:
                query = query.where(Booking.status == BookingStatus(filter_status))
            except ValueError:
                pass
        result = await db.execute(query.order_by(Booking.start_time.desc()).limit(200))
        rows_data = result.all()

    master_by_id = {m.id: m for m in masters}
    master_user_names = {}
    for m in masters:
        mu = (await db.execute(select(UserModel).where(UserModel.id == m.user_id))).scalar_one_or_none()
        master_user_names[m.id] = mu.full_name if mu else "—"

    client_ids = {b.client_id for b, s in rows_data}
    clients_by_id = {}
    for cid in client_ids:
        cu = (await db.execute(select(UserModel).where(UserModel.id == cid))).scalar_one_or_none()
        clients_by_id[cid] = cu.full_name or cu.phone if cu else "—"

    rows_html = ""
    for b, s in rows_data:
        label, status_class = STATUS_LABELS.get(b.status, (b.status.value, "cancelled"))
        price = f"{(b.final_price or s.price):,}".replace(",", " ")
        needs_badge = b.status == BookingStatus.COMPLETED and not b.consumption_reported
        badge = f'<span class="not-reported-badge">не списано</span>' if needs_badge else ""
        rows_html += f"""
        <tr>
            <td>{b.start_time.strftime('%d.%m.%Y %H:%M')}</td>
            <td>{clients_by_id.get(b.client_id, '—')}</td>
            <td>{master_user_names.get(b.master_id, '—')}</td>
            <td>{s.name}</td>
            <td><span class="status-badge {status_class}">{label}</span>{badge}</td>
            <td>{price} ₽</td>
        </tr>"""

    master_options = "".join(
        f'<option value="{m.id}"{" selected" if filter_master_id == str(m.id) else ""}>{master_user_names.get(m.id, "—")}</option>'
        for m in masters
    )
    status_options = "".join(
        f'<option value="{st.value}"{" selected" if filter_status == st.value else ""}>{label}</option>'
        for st, (label, _color) in STATUS_LABELS.items()
    )

    return f"""
    <div id="tab-records" class="tab-content">
        <form method="get" action="/business/dashboard" class="records-filters">
            <input type="hidden" name="salon_id" value="{salon.id}">
            <input type="hidden" name="tab" value="records">
            
            <div class="filter-group">
                <label for="date_from">С даты</label>
                <input type="date" id="date_from" name="date_from" value="{date_from.strftime('%Y-%m-%d')}">
            </div>
            <div class="filter-group">
                <label for="date_to">По дату</label>
                <input type="date" id="date_to" name="date_to" value="{(date_to - timedelta(days=1)).strftime('%Y-%m-%d')}">
            </div>
            <div class="filter-group">
                <label for="master_id">Мастер</label>
                <select id="master_id" name="master_id">
                    <option value="">Все мастера</option>
                    {master_options}
                </select>
            </div>
            <div class="filter-group">
                <label for="status">Статус</label>
                <select id="status" name="status">
                    <option value="">Все статусы</option>
                    {status_options}
                </select>
            </div>
            <button type="submit" class="btn-outline">{ICON_FILTER} Применить</button>
        </form>

        <div class="card records-table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>{ICON_CALENDAR_DAYS} Дата</th>
                        <th>{ICON_USER_CHECK} Клиент</th>
                        <th>Мастер</th>
                        <th>Услуга</th>
                        <th>Статус</th>
                        <th>Сумма</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html or '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--color-muted)">Записей за период нет</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    """