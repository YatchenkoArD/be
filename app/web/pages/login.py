# app/web/pages/login.py
import html
from fastapi import Request
from app.web.components.styles import get_base_styles


def _alert(msg: str) -> str:
    """Баннер-уведомление об ошибке."""
    if not msg:
        return ""
    return (
        '<div style="background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5;'
        'border-radius:0.5rem;padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.875rem">'
        f'{msg}</div>'
    )


def render_login_page(request: Request) -> str:
    """Страница входа."""
    q = request.query_params
    redirect = html.escape(q.get("redirect", "/"), quote=True)
    phone = html.escape(q.get("phone", ""), quote=True)
    errors = {
        "1": "Неверный телефон или пароль",
        "locked": "Слишком много попыток входа. Попробуйте через 15 минут.",
    }
    banner = _alert(errors.get(q.get("error", ""), ""))

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Вход — руми</title>
    {get_base_styles()}
</head>
<body class="auth-page">
    <div class="auth-card">
        <div class="auth-logo">руми.</div>
        <h1 class="auth-title">Вход</h1>
        {banner}
        <form action="/api/v1/auth/login-web" method="post">
            <input type="hidden" name="redirect" value="{redirect}">
            <div class="form-group">
                <label for="phone">Телефон</label>
                <input type="tel" id="phone" name="phone" value="{phone}" placeholder="+7 (___) ___-__-__" class="phone-input" required>
            </div>
            <div class="form-group">
                <label for="password">Пароль</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" class="btn-primary auth-btn">Войти</button>
        </form>
        <div class="auth-links">
            <a href="/register">Регистрация</a> · <a href="/">На главную</a>
        </div>
    </div>
    {scripts}
</body>
</html>"""