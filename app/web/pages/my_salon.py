# app/web/pages/my_salon.py
import html
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Salon, Master, Promotion, SalonLoyaltySettings, LoyaltyOffer, User as UserModel

DAY_KEYS_RU = [
    ("mon", "Понедельник"), ("tue", "Вторник"), ("wed", "Среда"), ("thu", "Четверг"),
    ("fri", "Пятница"), ("sat", "Суббота"), ("sun", "Воскресенье"),
]
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles


_ERROR_MESSAGES = {
    "bad_phone": "Не удалось распознать телефон мастера. Формат: +7 999 123-45-67 или 8 999 123-45-67.",
    "master_exists": "У этого пользователя уже есть профиль мастера.",
}


async def render_my_salon_page(db: AsyncSession, salon: Salon, user=None, query_params=None) -> str:
    """Страница редактирования своего салона."""
    from app.models.models import SalonPhoto  # локальный импорт: избегаем циклов

    query_params = query_params or {}

    # Фото галереи — явный select (ленивая подгрузка в async уронила бы рендер)
    photos = (
        await db.execute(select(SalonPhoto).where(SalonPhoto.salon_id == salon.id).order_by(SalonPhoto.id))
    ).scalars().all()
    photo_cards = "".join(
        f'''<div style="position:relative">
                <img src="{p.url}" alt="" style="width:140px;height:100px;object-fit:cover;border-radius:0.5rem;border:1px solid var(--color-border)">
                <form method="post" action="/api/v1/upload/salon/{salon.id}/photo/{p.id}/delete" style="position:absolute;top:0.25rem;right:0.25rem;margin:0">
                    <button type="submit" title="Удалить фото" onclick="return confirm('Удалить фото?')"
                        style="background:rgba(0,0,0,0.55);color:#fff;border:none;border-radius:50%;width:1.5rem;height:1.5rem;cursor:pointer;line-height:1">&times;</button>
                </form>
            </div>'''
        for p in photos
    )
    photos_section = f'''
            <!-- Фото салона -->
            <div class="card" style="margin-top: 2rem;">
                <h2 class="text-subtitle" style="font-size: 1.25rem; margin-bottom: 1rem;">Фото салона</h2>
                <div id="photoDropZone" data-upload-url="/api/v1/upload/salon/{salon.id}/photo"
                     style="border:2px dashed var(--color-border);border-radius:0.75rem;padding:1.5rem;text-align:center;cursor:pointer;transition:all 0.2s;margin-bottom:1rem">
                    <p style="margin:0;font-weight:500">Перетащите фото сюда или нажмите, чтобы выбрать</p>
                    <p style="margin:0.25rem 0 0;font-size:0.8rem;color:var(--color-muted)">Можно несколько сразу · JPG/PNG до 5 МБ · появятся на странице салона</p>
                </div>
                <input type="file" id="photoFileInput" accept="image/*" multiple style="display:none">
                <div id="photoUploadStatus"></div>
                <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-top:0.5rem">
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

    # Временный пароль нового мастера показываем один раз, сразу после
    # добавления — дальше он нигде не хранится и не восстанавливается.
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

    # Получаем мастеров салона
    masters_result = await db.execute(
        select(Master).where(Master.salon_id == salon.id)
    )
    masters = masters_result.scalars().all()

    # Получаем акции
    promos_result = await db.execute(
        select(Promotion).where(Promotion.salon_id == salon.id)
    )
    promotions = promos_result.scalars().all()

    # Настройки лояльности + именные скидки/промокоды
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
        # Явно загружаем пользователя для мастера (вместо ленивой загрузки m.user)
        user_result = await db.execute(
            select(UserModel).where(UserModel.id == m.user_id)
        )
        master_user = user_result.scalar_one_or_none()
        user_name = master_user.full_name if master_user else "—"
        
        masters_rows += f"""
        <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <strong>{user_name}</strong>
            </td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">{m.specialization}</td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <button onclick="editMaster({m.id}, '{user_name}', '{m.specialization}', {m.experience_years})" style="background: none; border: none; color: var(--color-primary); cursor: pointer; font-size:1.1rem" title="Редактировать">✏️</button>
                <button onclick="deleteMaster({m.id}, '{user_name}')" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size:1.1rem; margin-left:0.5rem" title="Удалить">🗑️</button>
            </td>
        </tr>
        """
    
    # Таблица именных скидок/промокодов лояльности
    loyalty_offers_rows = ""
    for o in loyalty_offers:
        code_str = o.promo_code or "—"
        loyalty_offers_rows += f"""
        <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);"><strong>{o.title}</strong></td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">{o.discount_percent}%</td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);"><code>{code_str}</code></td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <button onclick="deleteLoyaltyOffer({o.id}, '{o.title}')" style="background: none; border: none; color: red; cursor: pointer;">🗑️</button>
            </td>
        </tr>
        """

    # Часы работы: разбираем текущий JSON (может отсутствовать — это и есть
    # причина пустого расписания, пока владелец их не заполнит)
    parsed_hours = {}
    if salon.working_hours:
        try:
            parsed_hours = json.loads(salon.working_hours)
        except (ValueError, TypeError):
            parsed_hours = {}

    hours_rows = ""
    for key, label in DAY_KEYS_RU:
        raw = (parsed_hours.get(key) or "").strip()
        # Если для салона вообще не задан график (raw пустой), день по умолчанию
        # считаем рабочим, а не выходным — иначе все чекбоксы "Выходной" оказываются
        # включены и заблокированные поля времени незаметно для владельца
        # сохраняются как "closed", хотя он вводил часы работы.
        is_closed = raw in ("closed", "выходной", "day off")
        start_val, end_val = "10:00", "20:00"
        if raw and not is_closed and "-" in raw:
            parts = raw.split("-")
            if len(parts) == 2:
                start_val, end_val = parts[0].strip(), parts[1].strip()
        checked = "checked" if is_closed else ""
        disabled = "disabled" if is_closed else ""
        hours_rows += f"""
        <div style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;border-bottom:1px solid var(--color-border);flex-wrap:wrap">
            <span style="width:130px;font-size:0.875rem">{label}</span>
            <label style="display:flex;align-items:center;gap:0.4rem;font-size:0.8rem;color:var(--color-muted);width:110px">
                <input type="checkbox" class="wh-closed" data-day="{key}" {checked} onchange="toggleDayClosed('{key}', this.checked)"> Выходной
            </label>
            <input type="time" id="wh-start-{key}" value="{start_val}" {disabled} style="padding:0.4rem;border:1px solid var(--color-border);border-radius:0.5rem">
            <span style="color:var(--color-muted)">—</span>
            <input type="time" id="wh-end-{key}" value="{end_val}" {disabled} style="padding:0.4rem;border:1px solid var(--color-border);border-radius:0.5rem">
        </div>"""

    # Таблица акций (с рабочей кнопкой удаления)
    promos_rows = ""
    for p in promotions:
        promos_rows += f"""
        <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);"><strong>{p.title}</strong></td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">{p.tag}</td>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-border);">
                <button onclick="deletePromo({p.id}, '{p.title}')" style="background: none; border: none; color: red; cursor: pointer;">🗑️</button>
            </td>
        </tr>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Мой салон — {salon.name} — руми</title>
    {get_base_styles()}
    <style>
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal-box {{
            background: white;
            border-radius: 1rem;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            position: relative;
            max-height: 90vh;
            overflow-y: auto;
        }}
        .modal-close {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--color-muted);
        }}
        .modal-close:hover {{
            color: var(--color-heading);
        }}
    </style>
</head>
<body>
    {render_header("business")}
    {render_sidebar("business", user)}
    
    <main style="margin-right: 16rem; padding-top: 2rem;">
        <div class="section-container">
            
            <!-- Заголовок -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                <div>
                    <h1 class="text-display" style="font-size: 2rem;">{salon.name}</h1>
                    <p class="text-muted">Редактирование карточки салона</p>
                </div>
                <a href="/business/dashboard" class="btn-outline">← К панели управления</a>
            </div>

            {error_banner}
            {success_banner}

            <!-- Форма редактирования -->
            <div class="card" style="margin-bottom: 2rem;">
                <h2 class="text-subtitle" style="font-size: 1.25rem; margin-bottom: 1.5rem;">Основная информация</h2>
                <form action="/api/v1/business/my-salon" method="post">
                    <input type="hidden" name="method_override" value="put">
                    <input type="hidden" name="salon_id" value="{salon.id}">
                    <div class="grid-2" style="gap: 1.5rem; margin-bottom: 1.5rem;">
                        <div>
                            <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Название салона</label>
                            <input type="text" name="name" value="{salon.name}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                        </div>
                        <div>
                            <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Телефон</label>
                            <input type="tel" name="phone" value="{salon.phone or ''}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Адрес</label>
                        <input type="text" name="address" value="{salon.address or ''}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Описание</label>
                        <textarea name="description" rows="3" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem; resize: vertical;">{salon.description or ''}</textarea>
                    </div>
                    
                    <button type="submit" class="btn-primary">💾 Сохранить изменения</button>
                </form>
            </div>

            <!-- Часы работы -->
            <div class="card" style="margin-bottom: 2rem;">
                <h2 class="text-subtitle" style="font-size: 1.25rem; margin-bottom: 0.5rem;">Часы работы</h2>
                <p class="text-muted" style="margin-bottom: 1rem; font-size: 0.875rem;">
                    Без часов работы расписание пустое и клиенты не могут записаться — заполните хотя бы будни.
                </p>
                <div style="margin-bottom: 1rem">
                    {hours_rows}
                </div>
                <div style="display:flex;gap:0.75rem;align-items:center;flex-wrap:wrap">
                    <button type="button" class="btn-primary" onclick="saveWorkingHours({salon.id})">💾 Сохранить часы работы</button>
                    <button type="button" class="btn-outline" style="font-size:0.85rem" onclick="copyMondayToWeekdays()">Скопировать понедельник на пн–пт</button>
                </div>
            </div>

            <!-- Мастера -->
            <div class="card" style="margin-bottom: 2rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h2 class="text-subtitle" style="font-size: 1.25rem;">Мастера</h2>
                    <button class="btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addMasterModal').classList.add('active')">+ Добавить мастера</button>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Имя</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Специализация</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border); width:80px"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {masters_rows or '<tr><td colspan="3" style="padding:2rem;text-align:center;color:var(--color-muted)">Пока нет мастеров</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            {photos_section}

            <!-- Акции -->
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h2 class="text-subtitle" style="font-size: 1.25rem;">Акции</h2>
                    <button class="btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addPromoModal').classList.add('active')">+ Добавить акцию</button>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Название</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Тег</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {promos_rows or '<tr><td colspan="3" style="padding:2rem;text-align:center;color:var(--color-muted)">Пока нет акций</td></tr>'}
                    </tbody>
                </table>
            </div>

            <!-- Лояльность -->
            <div class="card" style="margin-top: 2rem;">
                <h2 class="text-subtitle" style="font-size: 1.25rem; margin-bottom: 0.5rem;">Лояльность</h2>
                <p class="text-muted" style="margin-bottom: 1.5rem; font-size: 0.875rem;">
                    Скидку клиенту даёт только ваш салон — настройте её сами. Мастер такие скидки не применяет,
                    это делает администратор при завершении записи в «Расписании».
                </p>

                <div class="grid-2" style="gap: 1.5rem; margin-bottom: 1.5rem;">
                    <div>
                        <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Скидка «постоянному клиенту», %</label>
                        <input type="number" id="loyaltyRegularPercent" min="0" max="99" value="{loyalty_settings.regular_client_discount_percent if loyalty_settings else 0}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Визитов за год для авто-статуса</label>
                        <input type="number" id="loyaltyVisitsThreshold" min="1" placeholder="Не задано — только вручную" value="{loyalty_settings.regular_client_visits_threshold if loyalty_settings and loyalty_settings.regular_client_visits_threshold else ''}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                    </div>
                </div>
                <div style="margin-bottom: 1.5rem; max-width: calc(50% - 0.75rem)">
                    <label style="display: block; font-weight: 500; margin-bottom: 0.5rem;">Автоначисление баллов после оплаты, % от чека</label>
                    <input type="number" id="loyaltyBonusAccrual" min="0" max="99" step="0.1" placeholder="0 — выключено" value="{loyalty_settings.bonus_accrual_percent if loyalty_settings else 0}" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.5rem;">
                </div>
                <button type="button" class="btn-primary" onclick="saveLoyaltySettings({salon.id})">💾 Сохранить настройки лояльности</button>

                <div style="display: flex; justify-content: space-between; align-items: center; margin: 2rem 0 1rem;">
                    <h3 style="font-size: 1.05rem;">Именные скидки и промокоды</h3>
                    <button class="btn-primary" style="font-size:0.85rem;padding:0.5rem 1rem" onclick="document.getElementById('addLoyaltyOfferModal').classList.add('active')">+ Добавить</button>
                </div>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Название</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Скидка</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);">Промокод</th>
                            <th style="text-align: left; padding: 0.75rem; border-bottom: 2px solid var(--color-border);"></th>
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
    <div class="modal-overlay" id="addMasterModal">
        <div class="modal-box">
            <button class="modal-close" onclick="document.getElementById('addMasterModal').classList.remove('active')">&times;</button>
            <h2 style="margin-bottom:1.5rem">Добавить мастера</h2>
            <form action="/api/v1/master/create-web" method="post">
                <input type="hidden" name="salon_id" value="{salon.id}">
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Имя *</label>
                    <input type="text" name="full_name" required placeholder="Имя мастера" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Телефон *</label>
                    <input type="tel" name="phone" required placeholder="+7XXXXXXXXXX" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Специализация *</label>
                    <input type="text" name="specialization" required placeholder="Например: барбер-стилист" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Опыт (лет)</label>
                    <input type="number" name="experience_years" value="0" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <button type="submit" class="btn-primary" style="width:100%">Добавить мастера</button>
            </form>
        </div>
    </div>
    
    <!-- Модальное окно: Редактировать мастера -->
    <div class="modal-overlay" id="editMasterModal">
        <div class="modal-box">
            <button class="modal-close" onclick="document.getElementById('editMasterModal').classList.remove('active')">&times;</button>
            <h2 style="margin-bottom:1.5rem">Редактировать мастера</h2>
            <form id="editMasterForm" method="post">
                <input type="hidden" name="master_id" id="editMasterId">
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Имя *</label>
                    <input type="text" name="full_name" id="editMasterName" required style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Специализация *</label>
                    <input type="text" name="specialization" id="editMasterSpec" required style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Опыт (лет)</label>
                    <input type="number" name="experience_years" id="editMasterExp" value="0" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <button type="submit" class="btn-primary" style="width:100%">Сохранить изменения</button>
            </form>
        </div>
    </div>
    
    <!-- Модальное окно: Добавить акцию -->
    <div class="modal-overlay" id="addPromoModal">
        <div class="modal-box">
            <button class="modal-close" onclick="document.getElementById('addPromoModal').classList.remove('active')">&times;</button>
            <h2 style="margin-bottom:1.5rem">Добавить акцию</h2>
            <form action="/api/v1/business/my-salon/promotions/web" method="post">
                <input type="hidden" name="salon_id" value="{salon.id}">
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Название *</label>
                    <input type="text" name="title" required placeholder="Например: Скидка 20%" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Описание</label>
                    <textarea name="description" rows="2" placeholder="Условия акции..." style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem"></textarea>
                </div>
                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:500;margin-bottom:0.5rem">Тег *</label>
                    <input type="text" name="tag" required placeholder="Новичкам, Выгода, Подарок..." style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
                </div>
                <button type="submit" class="btn-primary" style="width:100%">Добавить акцию</button>
            </form>
        </div>
    </div>
    
    <!-- Модальное окно: Добавить именную скидку/промокод -->
    <div class="modal-overlay" id="addLoyaltyOfferModal">
        <div class="modal-box">
            <button class="modal-close" onclick="document.getElementById('addLoyaltyOfferModal').classList.remove('active')">&times;</button>
            <h2 style="margin-bottom:1.5rem">Добавить скидку</h2>
            <div style="margin-bottom:1rem">
                <label style="display:block;font-weight:500;margin-bottom:0.5rem">Название *</label>
                <input type="text" id="loyaltyOfferTitle" required placeholder="Например: День рождения" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
            </div>
            <div style="margin-bottom:1rem">
                <label style="display:block;font-weight:500;margin-bottom:0.5rem">Скидка, % *</label>
                <input type="number" id="loyaltyOfferPercent" min="1" max="99" required style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
            </div>
            <div style="margin-bottom:1rem">
                <label style="display:block;font-weight:500;margin-bottom:0.5rem">Промокод</label>
                <input type="text" id="loyaltyOfferCode" placeholder="Необязательно, например BDAY15" style="width:100%;padding:0.75rem;border:1px solid var(--color-border);border-radius:0.5rem">
            </div>
            <button type="button" class="btn-primary" style="width:100%" onclick="addLoyaltyOffer({salon.id})">Добавить</button>
        </div>
    </div>

    {render_footer(user)}

    <script src="/static/src/js/salon-photos.js"></script>
    <script>
    function editMaster(id, name, spec, exp) {{
        document.getElementById('editMasterId').value = id;
        document.getElementById('editMasterName').value = name;
        document.getElementById('editMasterSpec').value = spec;
        document.getElementById('editMasterExp').value = exp;
        document.getElementById('editMasterForm').action = '/api/v1/master/' + id + '/update';
        document.getElementById('editMasterModal').classList.add('active');
    }}
    
    function deleteMaster(id, name) {{
        if (confirm('Удалить мастера "' + name + '"? Это действие нельзя отменить.')) {{
            fetch('/api/v1/master/' + id + '/delete', {{ method: 'POST' }})
                .then(r => {{ if (r.ok) location.reload(); else alert('Ошибка при удалении'); }});
        }}
    }}
    
    function deletePromo(id, title) {{
        if (confirm('Удалить акцию "' + title + '"? Это действие нельзя отменить.')) {{
            fetch('/api/v1/business/my-salon/promotions/' + id + '/delete', {{ method: 'POST' }})
                .then(r => {{ if (r.ok) location.reload(); else alert('Ошибка при удалении'); }});
        }}
    }}

    const WH_DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];

    function toggleDayClosed(day, isClosed) {{
        document.getElementById('wh-start-' + day).disabled = isClosed;
        document.getElementById('wh-end-' + day).disabled = isClosed;
    }}

    function copyMondayToWeekdays() {{
        const start = document.getElementById('wh-start-mon').value;
        const end = document.getElementById('wh-end-mon').value;
        const mondayClosed = document.querySelector('.wh-closed[data-day="mon"]').checked;
        ['tue', 'wed', 'thu', 'fri'].forEach(day => {{
            document.querySelector(`.wh-closed[data-day="${{day}}"]`).checked = mondayClosed;
            document.getElementById('wh-start-' + day).value = start;
            document.getElementById('wh-end-' + day).value = end;
            toggleDayClosed(day, mondayClosed);
        }});
    }}

    async function saveWorkingHours(salonId) {{
        const hours = {{}};
        for (const day of WH_DAY_KEYS) {{
            const closed = document.querySelector(`.wh-closed[data-day="${{day}}"]`).checked;
            if (closed) {{
                hours[day] = 'closed';
            }} else {{
                const start = document.getElementById('wh-start-' + day).value;
                const end = document.getElementById('wh-end-' + day).value;
                if (!start || !end) {{ alert('Укажите время начала и конца для рабочего дня'); throw new Error('missing time'); }}
                hours[day] = `${{start}}-${{end}}`;
            }}
        }}
        const res = await fetch(`/api/v1/business/my-salon?salon_id=${{salonId}}`, {{
            method: 'PUT',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ working_hours: JSON.stringify(hours) }})
        }});
        if (res.ok) {{ alert('Часы работы сохранены'); location.reload(); }}
        else {{ const d = await res.json().catch(() => ({{}})); alert(d.detail || 'Ошибка'); }}
    }}

    async function saveLoyaltySettings(salonId) {{
        const body = {{
            regular_client_discount_percent: parseInt(document.getElementById('loyaltyRegularPercent').value) || 0,
            regular_client_visits_threshold: document.getElementById('loyaltyVisitsThreshold').value
                ? parseInt(document.getElementById('loyaltyVisitsThreshold').value) : null,
            bonus_accrual_percent: parseFloat(document.getElementById('loyaltyBonusAccrual').value) || 0,
        }};
        const res = await fetch(`/api/v1/loyalty/salon/${{salonId}}/settings`, {{
            method: 'PUT',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(body)
        }});
        if (res.ok) {{ alert('Настройки лояльности сохранены'); }}
        else {{ const d = await res.json(); alert(d.detail || 'Ошибка'); }}
    }}

    async function addLoyaltyOffer(salonId) {{
        const title = document.getElementById('loyaltyOfferTitle').value.trim();
        const discount_percent = parseInt(document.getElementById('loyaltyOfferPercent').value);
        const promo_code = document.getElementById('loyaltyOfferCode').value.trim() || null;
        if (!title || !discount_percent) {{ alert('Заполните название и размер скидки'); return; }}
        const res = await fetch(`/api/v1/loyalty/salon/${{salonId}}/offers`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ title, discount_percent, promo_code }})
        }});
        if (res.ok) {{ location.reload(); }}
        else {{ const d = await res.json(); alert(d.detail || 'Ошибка'); }}
    }}

    function deleteLoyaltyOffer(id, title) {{
        if (!confirm(`Удалить скидку «${{title}}»?`)) return;
        fetch(`/api/v1/loyalty/salon/{salon.id}/offers/${{id}}`, {{ method: 'DELETE' }})
            .then(r => {{ if (r.ok) location.reload(); else r.json().then(d => alert(d.detail || 'Ошибка')); }});
    }}
    </script>
</body>
</html>"""
    
    return html