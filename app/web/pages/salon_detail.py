# app/web/pages/salon_detail.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.models import (
    Salon, SalonPhoto, Master, Service, Promotion, User, Booking, BookingStatus,
    Review, ReviewPhoto, ReviewTargetType, SalonMember,
)
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.services.loyalty_service import LoyaltyService
from app.services.schedule_utils import MAX_BOOKING_DAYS_AHEAD
from app.web.components.icons import (
    ICON_ARROW_LEFT,
    ICON_HEART,
    ICON_HEART_FILLED,
    ICON_MAP_PIN,
    ICON_PHONE,
    ICON_CLOCK,
)

async def render_salon_detail(db: AsyncSession, salon_id: int, user=None) -> str:
    result = await db.execute(select(Salon).where(Salon.id == salon_id))
    salon = result.scalar_one_or_none()

    if not salon:
        return """<!DOCTYPE html><html><body class="error-page"><div class="section-container-sm"><h1>Салон не найден</h1><a class="btn-primary" href="/salons">← Вернуться на главную</a></div></body></html>"""

    masters_result = await db.execute(
        select(Master).where(Master.salon_id == salon.id, Master.is_active == True)
    )
    masters = masters_result.scalars().all()

    promos_result = await db.execute(
        select(Promotion).where(Promotion.salon_id == salon.id, Promotion.is_active == True)
    )
    promotions = promos_result.scalars().all()

    reviews_result = await db.execute(
        select(Review).where(Review.salon_id == salon.id).order_by(Review.created_at.desc()).limit(10)
    )
    reviews = reviews_result.scalars().all()

    verified_count = (await db.execute(
        select(func.count(Review.id)).where(Review.salon_id == salon.id, Review.is_verified == True)
    )).scalar() or 0

    # Сотрудники (владелец/админ) салона — цель отзыва «Сотрудник»
    staff_result = await db.execute(
        select(SalonMember, User)
        .join(User, User.id == SalonMember.user_id)
        .where(SalonMember.salon_id == salon.id, SalonMember.is_active == True)
    )
    staff_members = staff_result.all()

    # Лояльность видна клиенту заранее, до записи — скидку/бонусы даёт салон,
    # не РУМИ (портировано из main при слиянии с редизайном).
    loyalty_html = ""
    if user:
        loyalty = await LoyaltyService.get_client_status(db, salon.id, user.id)
        chips = []
        if loyalty["is_regular_client"] and loyalty["regular_client_discount_percent"] > 0:
            chips.append(f'🏅 Постоянный клиент −{loyalty["regular_client_discount_percent"]}%')
        if loyalty["personal_discount_percent"]:
            chips.append(f'🎁 Ваша скидка −{loyalty["personal_discount_percent"]}%')
        if loyalty["bonus_points"] > 0:
            chips.append(f'⭐ {loyalty["bonus_points"]} баллов')
        if chips:
            loyalty_html = (
                '<div class="salon-loyalty" style="margin-top:0.75rem;display:flex;gap:0.75rem;flex-wrap:wrap">'
                + "".join(
                    f'<span class="badge" style="background:var(--color-accent-light);color:var(--color-primary);'
                    f'padding:0.25rem 0.75rem;border-radius:1rem;font-size:0.85rem">{c}</span>'
                    for c in chips
                )
                + "</div>"
            )

    salon_photos = (
        await db.execute(select(SalonPhoto).where(SalonPhoto.salon_id == salon.id).order_by(SalonPhoto.id))
    ).scalars().all()
    # Обложка (salon.logo_url) — первой в ленте
    salon_photos = sorted(salon_photos, key=lambda p: p.url != salon.logo_url)
    photos_strip = ""
    if salon_photos:
        photos_strip = (
            '<div class="salon-photos" style="display:flex;gap:0.75rem;overflow-x:auto;padding:1rem 0">'
            + "".join(
                f'<img src="{p.url}" alt="" loading="lazy" '
                f'style="height:180px;border-radius:0.75rem;flex-shrink:0">'
                for p in salon_photos
            )
            + "</div>"
        )

    heart_svg = ICON_HEART.replace('"', '&quot;')
    heart_filled_svg = ICON_HEART_FILLED.replace('"', '&quot;')
    star_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-star"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"></path></svg>'

    # ----- Верхний блок (салон) -----
    top_block = f"""
    <section class="salon-top-section">
        <div class="section-container">
            <a class="back-link" href="/salons/">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-arrow"><path d="m12 19-7-7 7-7"></path><path d="M19 12H5"></path></svg>
                Все салоны
            </a>
            <div class="salon-header-grid">
                <div class="salon-image-wrapper">
                    {f'<img alt="{salon.name}" src="{salon.logo_url}">' if salon.logo_url else f'<div style="width:100%;height:100%;min-height:200px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--color-primary),var(--color-accent));color:#fff;font-size:4rem;font-weight:700;border-radius:1rem">{salon.name[0].upper()}</div>'}
                    <button class="favorite-btn top-fav-btn salon-top-fav" 
                            data-type="salon" 
                            data-id="{salon.id}" 
                            data-icon-heart="{heart_svg}"
                            data-icon-heart-filled="{heart_filled_svg}"
                            title="В избранное">
                        <span class="heart-icon">{ICON_HEART}</span>
                    </button>
                </div>
                <div class="salon-info-wrapper">
                    <h1 class="salon-title">{salon.name}</h1>
                    <div class="salon-meta">
                        <div class="salon-rating" title="{verified_count} из {salon.reviews_count or 0} отзывов подтверждены реальной записью">
                            {star_svg}
                            <span class="rating-val">{salon.rating or 0.0:.1f}</span>
                            <span class="rating-count">({salon.reviews_count or 0} отзывов, {verified_count} подтверждено)</span>
                        </div>
                        <div class="salon-tags">
                            {_get_service_tags(salon)}
                        </div>
                    </div>
                    <p class="salon-desc">{salon.description or ''}</p>
                    {loyalty_html}
                    <div class="salon-contacts">
                        <span class="contact-item">{ICON_MAP_PIN} {salon.address or 'Адрес не указан'}</span>
                        <span class="contact-item">{ICON_PHONE} {salon.phone or '—'}</span>
                        <span class="contact-item">{ICON_CLOCK} {salon.working_hours or 'Пн-Вс: 10:00 — 21:00'}</span>
                    </div>
                </div>
            </div>
        </div>
    </section>
    """

    # ----- Акции -----
    promos_html = ""
    if promotions:
        promos_html = '<section class="section-container promos-section"><h2 class="section-title">Акции</h2><div class="promos-grid">'
        for p in promotions:
            promos_html += f"""
            <div class="promo-card">
                <span class="promo-badge">{p.tag}</span>
                <h3 class="promo-title">{p.title}</h3>
                <p class="promo-desc">{p.description or ''}</p>
            </div>
            """
        promos_html += '</div></section>'

    # ----- Мастера и запись -----
    masters_list_html = ""
    detail_html = ""

    for m in masters:
        user_result = await db.execute(select(User).where(User.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        user_name = master_user.full_name if master_user else "Мастер"
        avatar = master_user.avatar_url or ""

        # Карточка в списке
        masters_list_html += f"""
        <div class="master-card" data-master-id="{m.id}">
            <div class="master-image-box">
                {f'<img src="{avatar}" alt="{user_name}">' if avatar else f'<div class="master-avatar-placeholder">{user_name[0].upper()}</div>'}
            </div>
            <div class="master-info-box">
                <div>
                    <div class="master-name">{user_name}</div>
                    <div class="master-spec">{m.specialization or "Барбер"}</div>
                </div>
                <div class="master-stats">
                    <span>опыт: {m.experience_years} лет</span>
                    <span>⭐ {m.rating or 0.0:.1f}</span>
                </div>
                <button class="btn-primary master-book-btn" data-master-id="{m.id}">Записаться</button>
            </div>
        </div>
        """

        # Детальный вид
        services_result = await db.execute(select(Service).where(Service.master_id == m.id))
        services = services_result.scalars().all()

        services_html = ""
        for s in services:
            services_html += f"""
            <button class="service-btn" 
                    data-master-id="{m.id}"
                    data-service-id="{s.id}"
                    data-service-name="{s.name}"
                    data-price="{s.price}"
                    data-duration="{s.duration_minutes}">
                <div>
                    <div class="service-name">{s.name}</div>
                    <div class="service-duration">{s.duration_minutes} мин</div>
                </div>
                <div class="service-price">{s.price} ₽</div>
            </button>
            """

        detail_html += f"""
        <div class="master-detail hidden" data-master-id="{m.id}">
            <button class="back-to-masters">← Назад к мастерам</button>
            
            <div class="master-detail-profile">
                <div class="master-detail-avatar">
                    {f'<img src="{avatar}" alt="{user_name}">' if avatar else f'<div class="master-avatar-placeholder">{user_name[0].upper()}</div>'}
                </div>
                <div>
                    <div class="master-detail-name">{user_name}</div>
                    <div class="master-spec">{m.specialization or "Барбер"}</div>
                    <div class="master-stats">
                        <span>опыт: {m.experience_years} лет</span>
                        <span>⭐ {m.rating or 0.0:.1f}</span>
                    </div>
                </div>
            </div>

            <h3 style="margin: 1.5rem 0 1rem; font-weight:600;">Выберите услугу:</h3>
            <div class="services-grid">
                {services_html}
            </div>

            <div class="slots-container hidden" id="detail-slots-{m.id}">
                <div class="slots-title" id="detail-slots-title-{m.id}"></div>
                <div class="slots-grid" id="detail-slot-grid-{m.id}"></div>
            </div>
        </div>
        """

    masters_block = f"""
    <section class="section-container masters-section">
        <div class="section-header">
            <h2 class="section-title">Выберите мастера</h2>
        </div>
        <div id="masters-list-container">
            <div class="masters-list">
                {masters_list_html or '<p>В салоне пока нет мастеров.</p>'}
            </div>
        </div>
        {detail_html}
    </section>
    """

    # Плавающая панель записи
    booking_panel = """
    <div class="booking-panel hidden" id="bookPanel">
        <div class="booking-panel-inner">
            <div class="booking-info">
                <span class="booking-master" id="panelMaster"></span>
                <span class="booking-dot"> · </span>
                <span class="booking-time" id="panelTime"></span>
            </div>
            <button class="btn-primary" onclick="confirmBooking()">Записаться</button>
        </div>
    </div>
    """

    # ----- Отзывы -----
    TARGET_LABELS = {
        ReviewTargetType.MASTER: "👤 Мастер",
        ReviewTargetType.SALON: "🏠 Салон",
        ReviewTargetType.STAFF: "🧑‍💼 Сотрудник",
    }
    reviews_html = ""
    if reviews:
        for r in reviews:
            client_result = await db.execute(select(User).where(User.id == r.client_id))
            client_user = client_result.scalar_one_or_none()
            client_name = client_user.full_name if client_user else "Клиент"
            stars = "★" * r.rating + "☆" * (5 - r.rating)
            date_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else ""

            target_label = TARGET_LABELS[r.target_type]
            if r.target_type == ReviewTargetType.MASTER and r.master_id:
                mu = await db.execute(
                    select(User).join(Master, Master.user_id == User.id).where(Master.id == r.master_id)
                )
                mu_row = mu.scalar_one_or_none()
                if mu_row:
                    target_label += f": {mu_row.full_name}"
            elif r.target_type == ReviewTargetType.STAFF and r.staff_user_id:
                su = await db.execute(select(User).where(User.id == r.staff_user_id))
                su_row = su.scalar_one_or_none()
                if su_row:
                    target_label += f": {su_row.full_name}"

            verified_badge = (
                '<span class="badge-tag" style="background:#dcfce7;color:#166534" '
                'title="Клиент реально был на завершённой записи">✅ Подтверждено записью</span>'
                if r.is_verified else
                '<span class="badge-tag" style="background:#f3f4f6;color:var(--color-muted)">Без подтверждения</span>'
            )

            photos_result = await db.execute(select(ReviewPhoto).where(ReviewPhoto.review_id == r.id))
            review_photos = photos_result.scalars().all()
            photos_html = ""
            if review_photos:
                items = ""
                for p in review_photos:
                    delete_btn = (
                        f'<button class="review-photo-delete" data-review-id="{r.id}" data-photo-id="{p.id}" '
                        f'title="Удалить фото">✕</button>'
                        if user and user.id == r.client_id else ""
                    )
                    report_btn = (
                        f'<button class="review-photo-report" data-photo-id="{p.id}" title="Пожаловаться">⚑</button>'
                        if user else ""
                    )
                    items += (
                        f'<div class="review-photo-item" style="position:relative;display:inline-block">'
                        f'<img src="{p.url}" alt="" loading="lazy" style="width:100px;height:100px;'
                        f'object-fit:cover;border-radius:0.5rem;margin:0.25rem">{delete_btn}{report_btn}</div>'
                    )
                photos_html = f'<div class="review-photos" style="display:flex;flex-wrap:wrap">{items}</div>'

            reviews_html += f"""
            <div class="review-item" data-target-type="{r.target_type.value}" data-verified="{'1' if r.is_verified else '0'}">
                <div class="review-header">
                    <strong class="review-author">{client_name}</strong>
                    <span class="review-date">{date_str}</span>
                </div>
                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin:0.35rem 0">
                    <span class="badge-tag">{target_label}</span>
                    {verified_badge}
                </div>
                <div class="review-stars">{stars}</div>
                <p class="review-text">{r.comment or 'Без комментария'}</p>
                {photos_html}
            </div>
            """
    else:
        reviews_html = '<p class="empty-state">Пока нет отзывов. Будьте первым!</p>'

    # ----- Форма отзыва -----
    if user:
        master_options = ""
        for m in masters:
            mu = (await db.execute(select(User).where(User.id == m.user_id))).scalar_one_or_none()
            master_options += f'<option value="{m.id}">{mu.full_name if mu else "Мастер"}</option>'
        staff_options = "".join(
            f'<option value="{su.id}">{su.full_name or su.phone}</option>' for _sm, su in staff_members
        )
        review_form_html = f"""
        <div class="card" style="padding:1.5rem;margin-bottom:1.5rem">
            <h3 style="margin-bottom:1rem">Оставить отзыв</h3>
            <form id="reviewForm" action="/api/v1/reviews/create" method="post" enctype="multipart/form-data">
                <input type="hidden" name="salon_id" value="{salon.id}">
                <div style="margin-bottom:0.75rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.4rem">О чём отзыв</label>
                    <select name="target_type" id="reviewTargetType" onchange="reviewToggleTarget()" style="width:100%;padding:0.6rem;border:1px solid var(--color-border);border-radius:0.5rem">
                        <option value="salon">Салон в целом (помещение, сервис)</option>
                        <option value="master">Конкретный мастер</option>
                        <option value="staff">Администратор/сотрудник</option>
                    </select>
                </div>
                <div style="margin-bottom:0.75rem" id="reviewMasterField">
                    <label style="display:block;font-weight:500;margin-bottom:0.4rem">Мастер</label>
                    <select name="master_id" style="width:100%;padding:0.6rem;border:1px solid var(--color-border);border-radius:0.5rem">
                        {master_options}
                    </select>
                </div>
                <div style="margin-bottom:0.75rem;display:none" id="reviewStaffField">
                    <label style="display:block;font-weight:500;margin-bottom:0.4rem">Сотрудник</label>
                    <select name="staff_user_id" style="width:100%;padding:0.6rem;border:1px solid var(--color-border);border-radius:0.5rem">
                        {staff_options}
                    </select>
                </div>
                <div style="margin-bottom:0.75rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.4rem">Оценка</label>
                    <select name="rating" style="width:100%;padding:0.6rem;border:1px solid var(--color-border);border-radius:0.5rem">
                        <option value="5">★★★★★</option>
                        <option value="4">★★★★☆</option>
                        <option value="3">★★★☆☆</option>
                        <option value="2">★★☆☆☆</option>
                        <option value="1">★☆☆☆☆</option>
                    </select>
                </div>
                <div style="margin-bottom:0.75rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.4rem">Комментарий</label>
                    <textarea name="comment" rows="3" style="width:100%;padding:0.6rem;border:1px solid var(--color-border);border-radius:0.5rem"></textarea>
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.4rem">Фото работ (до 5)</label>
                    <input type="file" name="files" accept="image/*" multiple>
                </div>
                <button type="submit" class="btn-primary">Отправить отзыв</button>
            </form>
        </div>
        <script>
            function reviewToggleTarget() {{
                const v = document.getElementById('reviewTargetType').value;
                document.getElementById('reviewMasterField').style.display = v === 'master' ? 'block' : 'none';
                document.getElementById('reviewStaffField').style.display = v === 'staff' ? 'block' : 'none';
            }}
        </script>
        """
    else:
        review_form_html = '<p class="empty-state">Чтобы оставить отзыв, <a href="/login">войдите</a>.</p>'

    reviews_filter_html = """
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem">
        <button class="btn-outline review-filter-btn active" data-filter="all" onclick="reviewFilter('all', this)">Все</button>
        <button class="btn-outline review-filter-btn" data-filter="master" onclick="reviewFilter('master', this)">О мастерах</button>
        <button class="btn-outline review-filter-btn" data-filter="salon" onclick="reviewFilter('salon', this)">О салоне</button>
        <button class="btn-outline review-filter-btn" data-filter="staff" onclick="reviewFilter('staff', this)">О сотрудниках</button>
        <button class="btn-outline review-filter-btn" data-filter="verified" onclick="reviewFilter('verified', this)">Только подтверждённые</button>
    </div>
    <script>
        function reviewFilter(kind, btn) {
            document.querySelectorAll('.review-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.review-item').forEach(el => {
                let show = true;
                if (kind === 'verified') show = el.dataset.verified === '1';
                else if (kind !== 'all') show = el.dataset.targetType === kind;
                el.style.display = show ? '' : 'none';
            });
        }
        document.addEventListener('click', async (e) => {
            if (e.target.classList.contains('review-photo-delete')) {
                if (!confirm('Удалить это фото?')) return;
                const { reviewId, photoId } = e.target.dataset;
                const res = await fetch(`/api/v1/upload/review/${reviewId}/photo/${photoId}/delete`, { method: 'POST' });
                if (res.ok) location.reload(); else alert('Не удалось удалить фото');
            }
            if (e.target.classList.contains('review-photo-report')) {
                const reason = prompt('Опишите проблему с этим фото (необязательно):', '');
                if (reason === null) return;
                const body = new URLSearchParams({ review_photo_id: e.target.dataset.photoId, reason: reason || '' });
                const res = await fetch('/api/v1/reports/photo', { method: 'POST', body });
                if (res.ok) alert('Жалоба отправлена, спасибо'); else alert('Не удалось отправить жалобу');
            }
        });
    </script>
    """

    html = f"""<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{salon.name} | руми</title>
    {get_base_styles()}
    <link rel="stylesheet" href="/static/css/pages/salon_detail.css">
</head>
<body class="page-body">
    {render_header("salons")}
    {render_sidebar("salons", user)}

    <div class="main-wrapper">
        <main>
            {top_block}
            {f'<section class="section-container">{photos_strip}</section>' if photos_strip else ''}
            {promos_html}
            {masters_block}

            <section class="section-container reviews-section">
                <h2 class="section-title">Отзывы</h2>
                {review_form_html}
                {reviews_filter_html}
                <div class="reviews-list">
                    {reviews_html}
                </div>
            </section>

            {render_footer(user)}
        </main>
    </div>

    {booking_panel}

    <script>window.MAX_BOOKING_DAYS = {MAX_BOOKING_DAYS_AHEAD};</script>
</body>
</html>"""
    return html

def _get_service_tags(salon: Salon) -> str:
    if not salon.description:
        return ''
    keywords = ["стрижка", "борода", "маникюр", "педикюр", "окрашивание", "укладка", "брови"]
    found = [kw.capitalize() for kw in keywords if kw in salon.description.lower()]
    if not found:
        return ''
    return ''.join(f'<span class="badge-tag">{kw}</span>' for kw in found[:3])