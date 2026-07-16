# app/web/pages/profile.py
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.web.components.icons import (
    ICON_USER,
    ICON_CAMERA,
    ICON_PHONE,
    ICON_MAIL,
    ICON_CALENDAR_SMALL,
    ICON_EDIT,
    ICON_MAP_PIN_SMALL,
)

def render_profile_page(user=None, master_profile=None, salon=None, stats=None, error=None, success=None) -> str:
    # Обработка сообщений
    error_message = ""
    success_message = ""
    if error:
        error_messages = {
            "email_taken": "Этот email уже используется другим пользователем",
            "wrong_password": "Неверный текущий пароль",
            "password_mismatch": "Новые пароли не совпадают",
            "password_too_short": "Пароль должен быть не менее 8 символов",
            "phone_exists": "Пользователь с таким телефоном уже зарегистрирован",
            "update_failed": "Не удалось обновить профиль",
        }
        error_message = f'<div class="profile-alert profile-alert-error">{error_messages.get(error, "Произошла ошибка")}</div>'

    if success:
        success_messages = {
            "updated": "Профиль успешно обновлён",
            "password_updated": "Пароль успешно изменён",
            "avatar_updated": "Аватар обновлён",
        }
        success_message = f'<div class="profile-alert profile-alert-success">{success_messages.get(success, "Операция выполнена успешно")}</div>'

    if not user:
        return _render_guest_page()

    # Общие данные
    name = user.full_name or "Пользователь"
    phone = user.phone or ""
    email = user.email or ""
    city = getattr(user, "city", "") or "Не указан"
    avatar_url = user.avatar_url or ""
    role = user.role.value if user.role else "client"
    created_at = getattr(user, "created_at", None)
    member_since = created_at.strftime("%d.%m.%Y") if created_at else ""
    avatar_letter = name[0].upper() if name else "?"

    role_names = {
        "client": "Клиент",
        "model": "Модель",
        "master": "Мастер",
        "business": "Владелец салона",
        "admin": "Администратор",
    }
    role_display = role_names.get(role, role.capitalize())

    # Ролевой блок
    role_block = ""

    if role == "model":
        tier_names = {"start": "Старт", "pro": "Про", "premium": "Премиум"}
        tier = getattr(user, "subscription_tier", None)
        tier_display = tier_names.get(tier.value if tier else "", "Неактивна") if tier else "Неактивна"
        expires = getattr(user, "subscription_expires_at", None)
        expires_str = expires.strftime("%d.%m.%Y") if expires else "—"
        role_block = f"""
        <div class="profile-role-block profile-subscription-block">
            <div class="profile-role-header">
                <h3>💎 Подписка</h3>
            </div>
            <div class="profile-role-body">
                <div class="profile-subscription-row">
                    <span class="profile-label">Тариф</span>
                    <span class="profile-value">{tier_display}</span>
                </div>
                <div class="profile-subscription-row">
                    <span class="profile-label">Действует до</span>
                    <span class="profile-value">{expires_str}</span>
                </div>
                <a href="/model/dashboard" class="profile-btn-secondary">Управление подпиской →</a>
            </div>
        </div>
        """

    elif role == "master" and master_profile:
        spec = master_profile.specialization or "—"
        exp = master_profile.experience_years or 0
        rating = master_profile.rating or 0
        bio = master_profile.bio or ""
        role_block = f"""
        <div class="profile-role-block profile-master-block">
            <div class="profile-role-header">
                <h3>💼 Профессиональная информация</h3>
            </div>
            <div class="profile-role-body">
                <div class="profile-master-grid">
                    <div>
                        <span class="profile-label">Специализация</span>
                        <span class="profile-value">{spec}</span>
                    </div>
                    <div>
                        <span class="profile-label">Опыт</span>
                        <span class="profile-value">{exp} лет</span>
                    </div>
                    <div>
                        <span class="profile-label">Рейтинг</span>
                        <span class="profile-value">⭐ {rating}</span>
                    </div>
                </div>
                {f'<div class="profile-master-bio">{bio}</div>' if bio else ''}
                <a href="/master/schedule" class="profile-btn-secondary">Моё расписание →</a>
            </div>
        </div>
        """

    elif role == "business" and salon:
        salon_name = salon.name or "—"
        salon_address = salon.address or "—"
        salon_phone = salon.phone or "—"
        salon_rating = salon.rating or 0
        salon_reviews = salon.reviews_count or 0
        masters_count = getattr(salon, "masters_count", 0)
        role_block = f"""
        <div class="profile-role-block profile-business-block">
            <div class="profile-role-header">
                <h3>🏢 Мой салон</h3>
            </div>
            <div class="profile-role-body">
                <div class="profile-business-name">{salon_name}</div>
                <div class="profile-business-meta">
                    <span>📍 {salon_address}</span>
                    <span>📞 {salon_phone}</span>
                </div>
                <div class="profile-business-stats">
                    <span>⭐ {salon_rating} ({salon_reviews} отзывов)</span>
                    <span>👥 {masters_count} мастеров</span>
                </div>
                <a href="/business/dashboard" class="profile-btn-secondary">Панель управления →</a>
            </div>
        </div>
        """

    # HTML
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Мой профиль — руми</title>
    {get_base_styles()}
    <link rel="stylesheet" href="/static/css/pages/profile.css">
</head>
<body>
    {render_header("profile")}
    {render_sidebar("profile", user)}

    <main class="profile-main">
        <div class="profile-container">

            <!-- Верхний блок (баннер) -->
            <div class="profile-banner">
                <div class="profile-avatar-wrapper">
                    <div class="profile-avatar" id="profile-avatar-container">
                        {f'<img src="{avatar_url}" alt="{name}">' if avatar_url else f'<span class="profile-avatar-letter">{avatar_letter}</span>'}
                        <button class="profile-avatar-edit" id="profile-avatar-edit" title="Изменить аватар">
                            {ICON_CAMERA}
                        </button>
                        <input type="file" id="profile-avatar-input" accept="image/*" style="display:none">
                    </div>
                </div>
                <button class="profile-edit-toggle" id="profile-edit-toggle">
                    {ICON_EDIT} Редактировать
                </button>
            </div>

            <!-- Информация (белый блок) -->
            <div class="profile-view" id="profile-view">
                <div class="profile-name-wrapper">
                    <h1 class="profile-name">{name}</h1>
                    <span class="profile-role-badge">{role_display}</span>
                </div>
                <div class="profile-meta">
                    <span class="profile-meta-item">
                        {ICON_PHONE} {phone}
                    </span>
                    {f'<span class="profile-meta-item">{ICON_MAIL} {email}</span>' if email else ''}
                    <span class="profile-meta-item">
                        {ICON_MAP_PIN_SMALL} {city}
                    </span>
                    {f'<span class="profile-meta-item">{ICON_CALENDAR_SMALL} С {member_since}</span>' if member_since else ''}
                </div>
                {error_message}
                {success_message}
            </div>

            <!-- Режим редактирования -->
            <div class="profile-edit" id="profile-edit" style="display:none;">
                <div class="profile-edit-header">
                    <h2>Редактирование профиля</h2>
                    <div class="profile-edit-actions">
                        <button class="profile-btn-cancel" id="profile-edit-cancel">Отмена</button>
                        <button class="profile-btn-primary" id="profile-edit-save">Сохранить</button>
                    </div>
                </div>
                <form id="profile-edit-form" action="/api/v1/users/me/update-form" method="post">
                    <div class="profile-form-group">
                        <label for="profile-edit-name">Имя *</label>
                        <input type="text" id="profile-edit-name" name="full_name" value="{name}" required>
                    </div>
                    {f'''
                    <div class="profile-form-group">
                        <label for="profile-edit-bio">О себе</label>
                        <textarea id="profile-edit-bio" name="portfolio_desc" rows="4" placeholder="Расскажите о себе...">{getattr(user, 'portfolio_desc', '')}</textarea>
                    </div>
                    ''' if role in ['model', 'master'] else ''}
                    <button type="submit" style="display:none;">Сохранить</button>
                </form>
                <div class="profile-edit-note">
                    <p class="text-muted">Телефон, email и город можно изменить в <a href="/settings#data" class="text-link">настройках</a>.</p>
                </div>
            </div>

            <!-- Ролевой блок -->
            {role_block}

        </div>
    </main>

    {render_footer()}

    <script src="/static/js/pages/profile.js"></script>
</body>
</html>"""
    return html


def _render_guest_page() -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Мой профиль — руми</title>
    {get_base_styles()}
    <link rel="stylesheet" href="/static/css/pages/profile.css">
</head>
<body>
    {render_header("profile")}
    {render_sidebar("profile", None)}
    <main class="profile-main">
        <div class="profile-container">
            <div class="profile-guest-card">
                <h2>{ICON_USER} Войдите в аккаунт</h2>
                <p>Чтобы просматривать и редактировать профиль, войдите или зарегистрируйтесь</p>
                <div class="profile-guest-actions">
                    <a href="/login" class="profile-btn-primary">Войти</a>
                    <a href="/register" class="profile-btn-outline">Зарегистрироваться</a>
                </div>
            </div>
        </div>
    </main>
    {render_footer()}
</body>
</html>"""