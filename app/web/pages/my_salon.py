# app/web/pages/my_salon.py
import html
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Salon, Master, Promotion, SalonLoyaltySettings, LoyaltyOffer, User as UserModel, SalonPhoto

DAY_KEYS_RU = [
    ("mon", "Понедельник"), ("tue", "Вторник"), ("wed", "Среда"), ("thu", "Четверг"),
    ("fri", "Пятница"), ("sat", "Суббота"), ("sun", "Воскресенье"),
]
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.web.components.icons import (
    ICON_EDIT,
    ICON_TRASH,
    ICON_SAVE,
    ICON_PLUS,
    ICON_COPY,
    ICON_CLOCK_SMALL,
    ICON_PERCENT_SMALL,
    ICON_GIFT_SMALL,
)


_ERROR_MESSAGES = {
    "bad_phone": "Не удалось распознать телефон мастера. Формат: +7 999 123-45-67 или 8 999 123-45-67.",
    "master_exists": "У этого пользователя уже есть профиль мастера.",
}


async def render_my_salon_page(db: AsyncSession, salon: Salon, user=None, query_params=None) -> str:
    """Страница редактирования своего салона."""

    query_params = query_params or {}

    # Фото галереи
    photos = (
        await db.execute(select(SalonPhoto).where(SalonPhoto.salon_id == salon.id).order_by(SalonPhoto.id))
    ).scalars().all()

    def _photo_card(p) -> str:
        is_cover = salon.logo_url == p.url
        border_class = "cover-border" if is_cover else "default-border"
        cover_badge = (
            f'<span class="cover-badge">★ Обложка</span>'
            if is_cover else
            f'''<form method="post" action="/api/v1/upload/salon/{salon.id}/photo/{p.id}/cover" style="margin:0;position:absolute;bottom:0.25rem;left:0.25rem">
                    <button type="submit" title="Показывать это фото на карточке салона в общем списке" class="cover-btn">Сделать обложкой</button>
                </form>'''
        )
        return f'''
        <div class="my-salon-photo-item">
            <img src="{p.url}" alt="" class="{border_class}">
            <form method="post" action="/api/v1/upload/salon/{salon.id}/photo/{p.id}/delete" style="margin:0;position:absolute;top:0.25rem;right:0.25rem">
                <button type="submit" title="Удалить фото" onclick="return confirm('Удалить фото?')" class="delete-btn">&times;</button>
            </form>
            {cover_badge}
        </div>'''

    photo_cards = "".join(_photo_card(p) for p in photos)
    photos_section = f'''
            <div class="my-salon-card">
                <h2 class="my-salon-card-title">Фото салона</h2>
                <div id="photoDropZone" data-upload-url="/api/v1/upload/salon/{salon.id}/photo" class="my-salon-dropzone">
                    <p>Перетащите фото сюда или нажмите, чтобы выбрать</p>
                    <p class="hint">Можно несколько сразу · JPG/PNG до 5 МБ · появятся на странице салона</p>
                </div>
                <input type="file" id="photoFileInput" accept="image/*" multiple style="display:none">
                <div id="photoUploadStatus"></div>
                <div class="my-salon-photos">
                    {photo_cards or '<p style="color:var(--color-muted);margin:0">Пока нет фотографий</p>'}
                </div>
            </div>'''

    error_banner = ""
    error_code = query_params.get("error")
    if error_code:
        message = _ERROR_MESSAGES.get(error_code, "Что-то пошло не так, попробуйте ещё раз.")
        error_banner = (
            '<div style="background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5;'
            'border-radius:0.5rem;padding:0.75rem 1rem;margin-bottom:1.5rem;font-size:0.875rem">'
            f'{message}</div>'
        )

    success_banner = ""
    temp_pw = query_params.get("temp_pw")
    if temp_pw:
        safe_temp_pw = html.escape(temp_pw, quote=True)
        success_banner = (
            '<div style="background:#DCFCE7;color:#166534;border:1px solid #86EFAC;'
            'border-radius:0.5rem;padding:0.75rem 1rem;margin-bottom:1.5rem;font-size:0.875rem">'
            f'Мастер добавлен. Временный пароль (передайте его мастеру, он больше нигде не отобразится): '
            f'<code style="background:white;padding:0.15rem 0.5rem;border-radius:0.25rem;font-weight:700">{safe_temp_pw}</code>'
            '</div>'
        )
    elif query_params.get("added"):
        success_banner = (
            '<div style="background:#DCFCE7;color:#166534;border:1px solid #86EFAC;'
            'border-radius:0.5rem;padding:0.75rem 1rem;margin-bottom:1.5rem;font-size:0.875rem">'
            'Мастер добавлен.</div>'
        )

    # Мастера
    masters_result = await db.execute(select(Master).where(Master.salon_id == salon.id))
    masters = masters_result.scalars().all()

    # Акции
    promos_result = await db.execute(select(Promotion).where(Promotion.salon_id == salon.id))
    promotions = promos_result.scalars().all()

    # Лояльность
    loyalty_settings = (await db.execute(
        select(SalonLoyaltySettings).where(SalonLoyaltySettings.salon_id == salon.id)
    )).scalar_one_or_none()
    loyalty_offers_result = await db.execute(
        select(LoyaltyOffer).where(LoyaltyOffer.salon_id == salon.id).order_by(LoyaltyOffer.created_at.desc())
    )
    loyalty_offers = loyalty_offers_result.scalars().all()

    # Таблица мастеров
    masters_rows = ""
    for m in masters:
        user_result = await db.execute(select(UserModel).where(UserModel.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        user_name = master_user.full_name if master_user else "—"

        masters_rows += f"""
        <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <strong>{user_name}</strong>
            </td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">{m.specialization}</td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <button onclick="editMaster({m.id}, '{user_name}', '{m.specialization}', {m.experience_years})" style="background: none; border: none; color: var(--color-primary); cursor: pointer; font-size:1.1rem" title="Редактировать">
                    {ICON_EDIT}
                </button>
                <button onclick="deleteMaster({m.id}, '{user_name}')" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size:1.1rem; margin-left:0.5rem" title="Удалить">
                    {ICON_TRASH}
                </button>
            </td>
        </tr>
        """

    # Таблица лояльности
    loyalty_offers_rows = ""
    for o in loyalty_offers:
        code_str = o.promo_code or "—"
        loyalty_offers_rows += f"""
        <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);"><strong>{o.title}</strong></td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">{o.discount_percent}%</td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);"><code>{code_str}</code></td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <button onclick="deleteLoyaltyOffer({o.id}, '{o.title}')" style="background: none; border: none; color: red; cursor: pointer;">{ICON_TRASH}</button>
            </td>
        </tr>
        """

    # Часы работы
    parsed_hours = {}
    if salon.working_hours:
        try:
            parsed_hours = json.loads(salon.working_hours)
        except (ValueError, TypeError):
            parsed_hours = {}

    hours_rows = ""
    for key, label in DAY_KEYS_RU:
        raw = (parsed_hours.get(key) or "").strip()
        is_closed = raw in ("closed", "выходной", "day off")
        start_val, end_val = "10:00", "20:00"
        if raw and not is_closed and "-" in raw:
            parts = raw.split("-")
            if len(parts) == 2:
                start_val, end_val = parts[0].strip(), parts[1].strip()
        checked = "checked" if is_closed else ""
        disabled = "disabled" if is_closed else ""
        hours_rows += f"""
        <div class="my-salon-hours-row">
            <span class="day-label">{label}</span>
            <label class="closed-label">
                <input type="checkbox" class="wh-closed" data-day="{key}" {checked} onchange="toggleDayClosed('{key}', this.checked)"> Выходной
            </label>
            <input type="time" id="wh-start-{key}" value="{start_val}" {disabled}>
            <span class="time-sep">—</span>
            <input type="time" id="wh-end-{key}" value="{end_val}" {disabled}>
        </div>"""

    # Акции
    promos_rows = ""
    for p in promotions:
        promos_rows += f"""
        <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);"><strong>{p.title}</strong></td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">{p.tag}</td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <button onclick="deletePromo({p.id}, '{p.title}')" style="background: none; border: none; color: red; cursor: pointer;">{ICON_TRASH}</button>
            </td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Мой салон — {salon.name} — руми</title>
    {get_base_styles()}
    <link rel="stylesheet" href="/static/src/css/pages/my-salon.css">
</head>
<body>
    {render_header("business")}
    {render_sidebar("business", user)}

    <main class="my-salon-main">
        <div class="section-container">

            <!-- Заголовок -->
            <div class="my-salon-header">
                <div>
                    <h1>{salon.name}</h1>
                    <p>Редактирование карточки салона</p>
                </div>
                <a href="/business/dashboard" class="btn-outline">← К панели управления</a>
            </div>

            {error_banner}
            {success_banner}

            <!-- Основная информация -->
            <div class="my-salon-card">
                <h2 class="my-salon-card-title">Основная информация</h2>
                <form action="/api/v1/business/my-salon" method="post">
                    <input type="hidden" name="method_override" value="put">
                    <input type="hidden" name="salon_id" value="{salon.id}">
                    <div class="my-salon-grid-2">
                        <div>
                            <label for="salonName">Название салона</label>
                            <input type="text" id="salonName" name="name" value="{salon.name}">
                        </div>
                        <div>
                            <label for="salonPhone">Телефон</label>
                            <input type="tel" id="salonPhone" name="phone" value="{salon.phone or ''}">
                        </div>
                    </div>
                    <div style="margin-bottom: 1.5rem;">
                        <label for="salonAddress" style="display:block;font-weight:500;margin-bottom:0.5rem;">Адрес</label>
                        <input type="text" id="salonAddress" name="address" value="{salon.address or ''}" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem;">
                    </div>
                    <div style="margin-bottom: 1.5rem;">
                        <label for="salonDescription" style="display:block;font-weight:500;margin-bottom:0.5rem;">Описание</label>
                        <textarea id="salonDescription" name="description" rows="3" class="my-salon-textarea">{salon.description or ''}</textarea>
                    </div>
                    <button type="submit" class="my-salon-btn-primary">{ICON_SAVE} Сохранить изменения</button>
                </form>
            </div>

            <!-- Часы работы -->
            <div class="my-salon-card">
                <h2 class="my-salon-card-title">Часы работы</h2>
                <p class="my-salon-card-hint">
                    Без часов работы расписание пустое и клиенты не могут записаться — заполните хотя бы будни.
                </p>
                <div style="margin-bottom: 1rem">
                    {hours_rows}
                </div>
                <div style="display:flex;gap:0.75rem;align-items:center;flex-wrap:wrap">
                    <button type="button" class="my-salon-btn-primary" onclick="saveWorkingHours({salon.id})">{ICON_SAVE} Сохранить часы работы</button>
                    <button type="button" class="my-salon-btn-outline" onclick="copyMondayToWeekdays()">{ICON_COPY} Скопировать понедельник на пн–пт</button>
                </div>
            </div>

            <!-- Мастера -->
            <div class="my-salon-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h2 class="my-salon-card-title" style="margin:0;">Мастера</h2>
                    <button class="my-salon-btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addMasterModal').classList.add('active')">
                        {ICON_PLUS} Добавить мастера
                    </button>
                </div>
                <table class="my-salon-table">
                    <thead>
                        <tr>
                            <th>Имя</th>
                            <th>Специализация</th>
                            <th style="width:80px">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {masters_rows or '<tr><td colspan="3" style="padding:2rem;text-align:center;color:var(--color-muted)">Пока нет мастеров</td></tr>'}
                    </tbody>
                </table>
            </div>

            {photos_section}

            <!-- Акции -->
            <div class="my-salon-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h2 class="my-salon-card-title" style="margin:0;">Акции</h2>
                    <button class="my-salon-btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addPromoModal').classList.add('active')">
                        {ICON_PLUS} Добавить акцию
                    </button>
                </div>
                <table class="my-salon-table">
                    <thead>
                        <tr>
                            <th>Название</th>
                            <th>Тег</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {promos_rows or '<tr><td colspan="3" style="padding:2rem;text-align:center;color:var(--color-muted)">Пока нет акций</td></tr>'}
                    </tbody>
                </table>
            </div>

            <!-- Лояльность -->
            <div class="my-salon-card">
                <h2 class="my-salon-card-title">Лояльность</h2>
                <p class="my-salon-card-hint">
                    Скидку клиенту даёт только ваш салон — настройте её сами. Мастер такие скидки не применяет,
                    это делает администратор при завершении записи в «Расписании».
                </p>

                <div class="my-salon-grid-2">
                    <div>
                        <label for="loyaltyRegularPercent">Скидка «постоянному клиенту», %</label>
                        <input type="number" id="loyaltyRegularPercent" min="0" max="99" value="{loyalty_settings.regular_client_discount_percent if loyalty_settings else 0}">
                    </div>
                    <div>
                        <label for="loyaltyVisitsThreshold">Визитов за год для авто-статуса</label>
                        <input type="number" id="loyaltyVisitsThreshold" min="1" placeholder="Не задано — только вручную" value="{loyalty_settings.regular_client_visits_threshold if loyalty_settings and loyalty_settings.regular_client_visits_threshold else ''}">
                    </div>
                </div>
                <div style="margin-bottom: 1.5rem; max-width: calc(50% - 0.75rem);">
                    <label for="loyaltyBonusAccrual">Автоначисление баллов после оплаты, % от чека</label>
                    <input type="number" id="loyaltyBonusAccrual" min="0" max="99" step="0.1" placeholder="0 — выключено" value="{loyalty_settings.bonus_accrual_percent if loyalty_settings else 0}">
                </div>
                <button type="button" class="my-salon-btn-primary" onclick="saveLoyaltySettings({salon.id})">{ICON_SAVE} Сохранить настройки лояльности</button>

                <div style="display: flex; justify-content: space-between; align-items: center; margin: 2rem 0 1rem;">
                    <h3 style="font-size: 1.05rem; font-weight:600; color:var(--color-heading);">Именные скидки и промокоды</h3>
                    <button class="my-salon-btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addLoyaltyOfferModal').classList.add('active')">
                        {ICON_PLUS} Добавить
                    </button>
                </div>
                <table class="my-salon-table">
                    <thead>
                        <tr>
                            <th>Название</th>
                            <th>Скидка</th>
                            <th>Промокод</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {loyalty_offers_rows or '<tr><td colspan="4" style="padding:2rem;text-align:center;color:var(--color-muted)">Пока нет именных скидок</td></tr>'}
                    </tbody>
                </table>
            </div>

        </div>
    </main>

    <!-- Модальное окно: Добавить мастера -->
    <div class="my-salon-modal-overlay" id="addMasterModal">
        <div class="my-salon-modal-box">
            <button class="my-salon-modal-close" onclick="document.getElementById('addMasterModal').classList.remove('active')">&times;</button>
            <h2>Добавить мастера</h2>
            <form action="/api/v1/master/create-web" method="post">
                <input type="hidden" name="salon_id" value="{salon.id}">
                <div class="my-salon-form-group">
                    <label for="masterName">Имя *</label>
                    <input type="text" id="masterName" name="full_name" required placeholder="Имя мастера">
                </div>
                <div class="my-salon-form-group">
                    <label for="masterPhone">Телефон *</label>
                    <input type="tel" id="masterPhone" name="phone" required placeholder="+7XXXXXXXXXX">
                </div>
                <div class="my-salon-form-group">
                    <label for="masterSpec">Специализация *</label>
                    <input type="text" id="masterSpec" name="specialization" required placeholder="Например: барбер-стилист">
                </div>
                <div class="my-salon-form-group">
                    <label for="masterExp">Опыт (лет)</label>
                    <input type="number" id="masterExp" name="experience_years" value="0">
                </div>
                <button type="submit" class="my-salon-btn-primary" style="width:100%">Добавить мастера</button>
            </form>
        </div>
    </div>

    <!-- Модальное окно: Редактировать мастера -->
    <div class="my-salon-modal-overlay" id="editMasterModal">
        <div class="my-salon-modal-box">
            <button class="my-salon-modal-close" onclick="document.getElementById('editMasterModal').classList.remove('active')">&times;</button>
            <h2>Редактировать мастера</h2>
            <form id="editMasterForm" method="post">
                <input type="hidden" name="master_id" id="editMasterId">
                <div class="my-salon-form-group">
                    <label for="editMasterName">Имя *</label>
                    <input type="text" id="editMasterName" name="full_name" required>
                </div>
                <div class="my-salon-form-group">
                    <label for="editMasterSpec">Специализация *</label>
                    <input type="text" id="editMasterSpec" name="specialization" required>
                </div>
                <div class="my-salon-form-group">
                    <label for="editMasterExp">Опыт (лет)</label>
                    <input type="number" id="editMasterExp" name="experience_years" value="0">
                </div>
                <button type="submit" class="my-salon-btn-primary" style="width:100%">Сохранить изменения</button>
            </form>
        </div>
    </div>

    <!-- Модальное окно: Добавить акцию -->
    <div class="my-salon-modal-overlay" id="addPromoModal">
        <div class="my-salon-modal-box">
            <button class="my-salon-modal-close" onclick="document.getElementById('addPromoModal').classList.remove('active')">&times;</button>
            <h2>Добавить акцию</h2>
            <form action="/api/v1/business/my-salon/promotions/web" method="post">
                <input type="hidden" name="salon_id" value="{salon.id}">
                <div class="my-salon-form-group">
                    <label for="promoTitle">Название *</label>
                    <input type="text" id="promoTitle" name="title" required placeholder="Например: Скидка 20%">
                </div>
                <div class="my-salon-form-group">
                    <label for="promoDesc">Описание</label>
                    <textarea id="promoDesc" name="description" rows="2" placeholder="Условия акции..."></textarea>
                </div>
                <div class="my-salon-form-group">
                    <label for="promoTag">Тег *</label>
                    <input type="text" id="promoTag" name="tag" required placeholder="Новичкам, Выгода, Подарок...">
                </div>
                <button type="submit" class="my-salon-btn-primary" style="width:100%">Добавить акцию</button>
            </form>
        </div>
    </div>

    <!-- Модальное окно: Добавить именную скидку/промокод -->
    <div class="my-salon-modal-overlay" id="addLoyaltyOfferModal">
        <div class="my-salon-modal-box">
            <button class="my-salon-modal-close" onclick="document.getElementById('addLoyaltyOfferModal').classList.remove('active')">&times;</button>
            <h2>Добавить скидку</h2>
            <div class="my-salon-form-group">
                <label for="loyaltyOfferTitle">Название *</label>
                <input type="text" id="loyaltyOfferTitle" required placeholder="Например: День рождения">
            </div>
            <div class="my-salon-form-group">
                <label for="loyaltyOfferPercent">Скидка, % *</label>
                <input type="number" id="loyaltyOfferPercent" min="1" max="99" required>
            </div>
            <div class="my-salon-form-group">
                <label for="loyaltyOfferCode">Промокод</label>
                <input type="text" id="loyaltyOfferCode" placeholder="Необязательно, например BDAY15">
            </div>
            <button type="button" class="my-salon-btn-primary" style="width:100%" onclick="addLoyaltyOffer({salon.id})">Добавить</button>
        </div>
    </div>

    {render_footer(user)}

    <script>
        window.salonId = {salon.id};
    </script>
    <script src="/static/src/js/pages/my-salon.js"></script>
</body>
</html>"""
    return html