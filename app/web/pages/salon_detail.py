# app/web/pages/salon_detail.py
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.models.models import (
    Salon, SalonPhoto, Master, Service, Promotion, User, Booking, BookingStatus,
    Review, ReviewPhoto, ReviewTargetType, SalonMember, SalonModerationStatus,
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
    ICON_CHECK,
    ICON_BELL,
    ICON_CHEVRON_RIGHT,
    ICON_USER,
    ICON_SCISSORS,
)


async def render_salon_detail(db: AsyncSession, salon_id: int, user=None) -> str:
    # Публично видны только одобренные активные салоны (модерация регистрации).
    result = await db.execute(select(Salon).where(
        Salon.id == salon_id,
        Salon.is_active == True,
        Salon.moderation_status == SalonModerationStatus.APPROVED,
    ))
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

    # Фото
    salon_photos = (
        await db.execute(select(SalonPhoto).where(SalonPhoto.salon_id == salon.id).order_by(SalonPhoto.id))
    ).scalars().all()
    salon_photos = sorted(salon_photos, key=lambda p: p.url != salon.logo_url)
    photos_strip = ""
    if salon_photos:
        photos_strip = (
            '<div class="salon-photos" style="display:flex;gap:0.75rem;overflow-x:auto;padding:1rem 0">'
            + "".join(
                f'<img src="{p.url}" alt="" loading="lazy" style="height:180px;border-radius:0.75rem;flex-shrink:0">'
                for p in salon_photos
            )
            + "</div>"
        )

    heart_svg = ICON_HEART.replace('"', '&quot;')
    heart_filled_svg = ICON_HEART_FILLED.replace('"', '&quot;')
    star_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-star"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"></path></svg>'

    # Подготовка данных для JS (пошаговый флоу записи — booking_flow_html ниже)
    masters_data = []
    for m in masters:
        user_result = await db.execute(select(User).where(User.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        services_result = await db.execute(select(Service).where(Service.master_id == m.id))
        services = services_result.scalars().all()
        masters_data.append({
            "id": m.id,
            "name": master_user.full_name if master_user else "Мастер",
            "specialization": m.specialization,
            "experience": m.experience_years,
            "rating": m.rating,
            "avatar": master_user.avatar_url or "",
            "services": [
                {"id": s.id, "name": s.name, "price": s.price, "duration": s.duration_minutes}
                for s in services
            ]
        })

    # Шаг 1: список мастеров (если больше одного, иначе сразу переходим к услугам)
    masters_list_html = ""
    for m in masters_data:
        avatar_html = f'<img src="{m["avatar"]}" alt="{m["name"]}">' if m["avatar"] else f'<div class="master-avatar-placeholder">{m["name"][0].upper()}</div>'
        masters_list_html += f"""
        <div class="master-card" data-master-id="{m["id"]}">
            <div class="master-image-box">
                {avatar_html}
            </div>
            <div class="master-info-box">
                <div>
                    <div class="master-name">{m["name"]}</div>
                    <div class="master-spec">{m["specialization"]}</div>
                </div>
                <div class="master-stats">
                    <span>опыт: {m["experience"]} лет</span>
                    <span>⭐ {m["rating"]:.1f}</span>
                </div>
                <button class="btn-primary master-book-btn" data-master-id="{m["id"]}">Выбрать</button>
            </div>
        </div>
        """

    # ----- Верхний блок (салон) -----
    top_block = f"""
    <section class="salon-top-section">
        <div class="section-container">
            <a class="back-link" href="/salons/">
                {ICON_ARROW_LEFT} Все салоны
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

    # Контейнер для пошагового процесса записи
    booking_flow_html = f"""
    <section class="section-container booking-flow">
        <div id="booking-flow-container" data-masters='{json.dumps(masters_data, ensure_ascii=False)}' data-user='{json.dumps({"id": user.id, "full_name": user.full_name, "phone": user.phone} if user else None, ensure_ascii=False)}'>
            <!-- Шаг 1: Выбор мастера -->
            <div class="booking-step" id="step-masters" style="display: {'none' if len(masters_data) == 1 else 'block'}">
                <h2 class="step-title">Выберите мастера</h2>
                <div class="masters-grid">
                    {masters_list_html}
                </div>
            </div>

            <!-- Шаг 2: Выбор услуги -->
            <div class="booking-step" id="step-services" style="display: none;">
                <div class="breadcrumb">
                    <button class="breadcrumb-btn" data-step="masters">Выберите мастера</button>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-master"></span>
                </div>
                <button class="back-btn" data-step="masters">{ICON_ARROW_LEFT} Назад к мастерам</button>
                <div class="master-summary" id="master-summary">
                    <div class="master-avatar-sm" id="selected-master-avatar"></div>
                    <div>
                        <p class="master-name-sm" id="selected-master-name"></p>
                        <p class="master-spec-sm" id="selected-master-spec"></p>
                    </div>
                    {ICON_CHECK}
                </div>
                <h3 class="step-subtitle">Выберите услугу:</h3>
                <div class="services-grid" id="services-list"></div>
            </div>

            <!-- Шаг 3: Выбор даты -->
            <div class="booking-step" id="step-date" style="display: none;">
                <div class="breadcrumb">
                    <button class="breadcrumb-btn" data-step="masters">Выберите мастера</button>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-master-2"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-service"></span>
                </div>
                <button class="back-btn" data-step="services">{ICON_ARROW_LEFT} Назад к услугам</button>
                <div class="master-summary">
                    <div class="master-avatar-sm" id="selected-master-avatar-2"></div>
                    <div>
                        <p class="master-name-sm" id="selected-master-name-2"></p>
                        <p class="master-spec-sm" id="selected-master-spec-2"></p>
                    </div>
                    {ICON_CHECK}
                    <span class="service-summary" id="selected-service-summary"></span>
                    <span class="service-price" id="selected-service-price"></span>
                </div>
                <h3 class="step-subtitle">Выберите дату:</h3>
                <div class="dates-grid" id="dates-grid"></div>
            </div>

            <!-- Шаг 4: Выбор времени -->
            <div class="booking-step" id="step-time" style="display: none;">
                <div class="breadcrumb">
                    <button class="breadcrumb-btn" data-step="masters">Выберите мастера</button>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-master-3"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-service-2"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-date"></span>
                </div>
                <button class="back-btn" data-step="date">{ICON_ARROW_LEFT} Назад к дате</button>
                <div class="master-summary">
                    <div class="master-avatar-sm" id="selected-master-avatar-3"></div>
                    <div>
                        <p class="master-name-sm" id="selected-master-name-3"></p>
                        <p class="master-spec-sm" id="selected-master-spec-3"></p>
                    </div>
                    {ICON_CHECK}
                    <span class="service-summary" id="selected-service-summary-2"></span>
                    <span class="service-price" id="selected-service-price-2"></span>
                    <span class="date-summary" id="selected-date-summary"></span>
                </div>
                <h3 class="step-subtitle">Выберите время:</h3>
                <div class="times-grid" id="times-grid"></div>
            </div>

            <!-- Шаг 5: Напоминание -->
            <div class="booking-step" id="step-reminder" style="display: none;">
                <div class="breadcrumb">
                    <button class="breadcrumb-btn" data-step="masters">Выберите мастера</button>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-master-4"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-service-3"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-date-2"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-time"></span>
                </div>
                <button class="back-btn" data-step="time">{ICON_ARROW_LEFT} Назад к времени</button>
                <div class="master-summary">
                    <div class="master-avatar-sm" id="selected-master-avatar-4"></div>
                    <div>
                        <p class="master-name-sm" id="selected-master-name-4"></p>
                        <p class="master-spec-sm" id="selected-master-spec-4"></p>
                    </div>
                    {ICON_CHECK}
                    <span class="service-summary" id="selected-service-summary-3"></span>
                    <span class="service-price" id="selected-service-price-3"></span>
                    <span class="date-summary" id="selected-date-summary-2"></span>
                    <span class="time-summary" id="selected-time-summary"></span>
                </div>
                <h3 class="step-subtitle">Напоминание:</h3>
                <div class="reminder-box">
                    <div class="reminder-toggle">
                        <div class="reminder-info">
                            {ICON_BELL}
                            <div>
                                <p class="reminder-title">Напомнить о записи</p>
                                <p class="reminder-desc">Получите уведомление перед визитом</p>
                            </div>
                        </div>
                        <button class="toggle-switch active" id="reminder-toggle"></button>
                    </div>
                    <div class="reminder-options" id="reminder-options">
                        <button class="reminder-option" data-minutes="30">За 30 мин</button>
                        <button class="reminder-option active" data-minutes="60">За 1 час</button>
                        <button class="reminder-option" data-minutes="120">За 2 часа</button>
                        <button class="reminder-option" data-minutes="1440">За день</button>
                    </div>
                </div>
                <button class="btn-primary next-btn" id="reminder-next">Далее →</button>
            </div>

            <!-- Шаг 6: Подтверждение -->
            <div class="booking-step" id="step-confirm" style="display: none;">
                <div class="breadcrumb">
                    <button class="breadcrumb-btn" data-step="masters">Выберите мастера</button>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-master-5"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-service-4"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-date-3"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current" id="breadcrumb-time-2"></span>
                    {ICON_CHEVRON_RIGHT}
                    <span class="breadcrumb-current">Подтверждение</span>
                </div>
                <button class="back-btn" data-step="reminder">{ICON_ARROW_LEFT} Назад</button>
                <div class="confirm-box">
                    <h3 class="confirm-title">Подтверждение записи</h3>
                    <div class="confirm-items">
                        <div class="confirm-item">
                            <div class="confirm-icon">{ICON_USER}</div>
                            <div>
                                <p class="confirm-label">Мастер</p>
                                <p class="confirm-value" id="confirm-master"></p>
                                <p class="confirm-sub" id="confirm-master-spec"></p>
                            </div>
                            {ICON_CHECK}
                        </div>
                        <div class="confirm-item">
                            <div class="confirm-icon">{ICON_SCISSORS}</div>
                            <div>
                                <p class="confirm-label">Услуга</p>
                                <p class="confirm-value" id="confirm-service"></p>
                                <p class="confirm-sub" id="confirm-duration"></p>
                            </div>
                            <span class="confirm-price" id="confirm-price"></span>
                        </div>
                        <div class="confirm-item">
                            {ICON_CLOCK}
                            <div>
                                <p class="confirm-label">Дата и время</p>
                                <p class="confirm-value" id="confirm-datetime"></p>
                            </div>
                        </div>
                        <div class="confirm-item">
                            {ICON_MAP_PIN}
                            <div>
                                <p class="confirm-label">Салон</p>
                                <p class="confirm-value">{salon.name}</p>
                                <p class="confirm-sub">{salon.address or 'Адрес не указан'}</p>
                            </div>
                        </div>
                        <div class="confirm-item">
                            {ICON_BELL}
                            <div>
                                <p class="confirm-label">Напоминание</p>
                                <p class="confirm-value" id="confirm-reminder"></p>
                            </div>
                        </div>
                    </div>
                    <div class="confirm-user">
                        <p class="confirm-user-label">Ваши данные</p>
                        <div class="confirm-user-info">
                            <span id="confirm-user-name">{user.full_name if user else 'Гость'}</span>
                            <span id="confirm-user-phone">{user.phone if user else ''}</span>
                            <a href="/profile" class="confirm-edit-link">изменить</a>
                        </div>
                    </div>
                    <button class="btn-primary confirm-submit" id="confirm-submit">Записаться</button>
                    <button class="btn-outline confirm-cancel" data-step="reminder">Отменить</button>
                </div>
            </div>
        </div>
    </section>
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
    # Отзыв можно оставить только после завершённого визита через Руми (см.
    # ReviewService.create_review) — не показываем форму тем, у кого такого
    # визита нет, иначе форма молча упирается в ошибку сервера при отправке.
    has_completed_visit = False
    if user:
        visit_check = await db.execute(
            select(Booking.id)
            .join(Master, Master.id == Booking.master_id)
            .where(Booking.client_id == user.id, Booking.status == BookingStatus.COMPLETED, Master.salon_id == salon.id)
            .limit(1)
        )
        has_completed_visit = visit_check.scalar_one_or_none() is not None

    if user and has_completed_visit:
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
    elif user:
        review_form_html = '<p class="empty-state">Отзыв можно оставить после завершённого визита, оформленного записью через Руми.</p>'
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
    <link rel="stylesheet" href="/static/src/css/salon-detail.css">
</head>
<body class="page-body">
    {render_header("salons")}
    {render_sidebar("salons", user)}

    <div class="main-wrapper">
        <main>
            {top_block}
            {f'<section class="section-container">{photos_strip}</section>' if photos_strip else ''}
            {promos_html}
            {booking_flow_html}

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

    <script>
        window.salonId = {salon.id};
        window.maxBookingDays = {MAX_BOOKING_DAYS_AHEAD};
    </script>
    <script src="/static/src/js/salon-detail.js"></script>
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
