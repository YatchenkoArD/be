# app/web/pages/register_salon.py
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles


def render_register_salon_page(user=None) -> str:
    """Страница регистрации нового салона."""
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Добавить салон — руми</title>
    {get_base_styles()}
</head>
<body>
    {render_header("business")}
    {render_sidebar("business", user)}
    
    <main style="margin-right: 16rem; padding-top: 2rem;">
        <div class="section-container">
            <div class="card" style="max-width: 600px; margin: 0 auto;">
                <h1 class="text-display" style="font-size: 1.75rem; margin-bottom: 0.5rem;">Добавить салон</h1>
                <p class="text-muted" style="margin-bottom: 2rem;">Заполните информацию о вашем салоне. После проверки он появится в каталоге.</p>
                
                <form action="/api/v1/business/my-salon" method="post">
                    <label style="display: block; font-weight: 500; margin-bottom: 0.5rem; color: var(--color-heading);">Название салона *</label>
                    <input type="text" name="name" required placeholder="Например: Студия красоты «Лотос»" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.75rem; font-size: 0.95rem; margin-bottom: 1.5rem;">
                    
                    <label style="display: block; font-weight: 500; margin-bottom: 0.5rem; color: var(--color-heading);">Описание</label>
                    <textarea name="description" rows="3" placeholder="Опишите ваш салон, услуги, особенности..." style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.75rem; font-size: 0.95rem; margin-bottom: 1.5rem; resize: vertical;"></textarea>
                    
                    <label style="display: block; font-weight: 500; margin-bottom: 0.5rem; color: var(--color-heading);">Адрес *</label>
                    <input type="text" name="address" required placeholder="Город, улица, дом" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.75rem; font-size: 0.95rem; margin-bottom: 1.5rem;">
                    
                    <label style="display: block; font-weight: 500; margin-bottom: 0.5rem; color: var(--color-heading);">Телефон *</label>
                    <input type="tel" name="phone" required placeholder="+7XXXXXXXXXX" style="width: 100%; padding: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.75rem; font-size: 0.95rem; margin-bottom: 1.5rem;">
                    
                    <button type="submit" class="btn-primary" style="width: 100%; padding: 1rem; font-size: 1rem;">Зарегистрировать салон</button>
                </form>
                
                <p class="text-muted" style="text-align: center; margin-top: 1rem; font-size: 0.8rem;">После отправки салон появится в каталоге после проверки модератором.</p>
            </div>
        </div>
    </main>
    
    {render_footer()}
</body>
</html>"""
    
    return html