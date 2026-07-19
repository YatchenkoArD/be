# app/web/pages/model_checkout.py
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.web.components.icons import (
    ICON_ARROW_LEFT,
    ICON_CIRCLE_CHECK,
)
import json

TARIFFS = {
    "start": {
        "id": "start",
        "name": "Старт",
        "description": "Для тех, кто хочет попробовать",
        "price": "490 ₽",
        "period": "/мес",
        "features": [
            "До 3 записей в месяц",
            "Скидка 30% на услуги мастеров",
            "Доступ к начинающим мастерам",
            "Базовое портфолио"
        ]
    },
    "pro": {
        "id": "pro",
        "name": "Про",
        "description": "Самый популярный выбор",
        "price": "990 ₽",
        "period": "/мес",
        "features": [
            "До 8 записей в месяц",
            "Скидка 50% на все услуги",
            "Приоритетная запись",
            "Доступ к топ-мастерам",
            "Расширенное портфолио",
            "Эксклюзивные процедуры"
        ]
    },
    "premium": {
        "id": "premium",
        "name": "Премиум",
        "description": "Максимум возможностей",
        "price": "1 990 ₽",
        "period": "/мес",
        "features": [
            "Безлимитные записи",
            "Скидка до 70% на услуги",
            "VIP приоритет на запись",
            "Доступ ко всем мастерам",
            "Персональный менеджер",
            "Фотосессии для портфолио",
            "Ранний доступ к новым салонам"
        ]
    }
}

def render_model_checkout_page(plan: str = "start", user=None) -> str:
    active = TARIFFS.get(plan, TARIFFS["start"])
    tariffs_json = json.dumps(TARIFFS, ensure_ascii=False)
    
    features_html = ''.join(f'<li>{ICON_CIRCLE_CHECK}<span>{f}</span></li>' for f in active["features"])

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Оформление подписки | Руми</title>
    <meta name="description" content="Оформите подписку «Модель» и получайте услуги со скидкой">
    {get_base_styles()}
</head>
<body>
    {render_header("model")}
    {render_sidebar("model", user)}

    <main class="home-main">
        <section class="section-py section-gradient checkout-section">
            <div class="section-container">
                <div class="checkout-wrapper">
                    <a href="/model#plans" class="checkout-back-link">
                        {ICON_ARROW_LEFT}
                        Назад к тарифам
                    </a>
                    <div class="checkout-header">
                        <h1 class="text-display checkout-title">Оформление подписки</h1>
                        <p class="text-body checkout-subtitle">Заполните данные для подключения тарифа</p>
                    </div>

                    <!-- Селектор тарифов -->
                    <div class="tariff-selector">
                        <button class="tariff-btn" data-plan="start">Старт</button>
                        <button class="tariff-btn active" data-plan="pro">Про</button>
                        <button class="tariff-btn" data-plan="premium">Премиум</button>
                    </div>

                    <div class="checkout-grid">
                        <div class="checkout-form">
                            <div class="form-fields">
                                <div>
                                    <label class="form-label">Имя</label>
                                    <input type="text" placeholder="Анна Иванова" class="form-input">
                                </div>
                                <div>
                                    <label class="form-label">Телефон</label>
                                    <input type="tel" placeholder="+7 (999) 123-45-67" class="form-input phone-input">
                                </div>
                                <div>
                                    <label class="form-label">Email</label>
                                    <input type="email" placeholder="anna@example.com" class="form-input">
                                </div>
                                <label class="checkbox-label">
                                    <input type="checkbox" class="checkbox-input" id="terms-checkbox">
                                    <span class="checkbox-text">Я соглашаюсь с <a href="/terms" class="text-link">условиями использования</a> и <a href="/privacy" class="text-link">политикой конфиденциальности</a></span>
                                </label>
                            </div>
                            <button class="checkout-submit" id="submit-btn">
                                Оплатить {active["price"]}
                            </button>
                            <p class="checkout-note" id="submit-note">Оплата будет доступна после интеграции с банком. Сейчас — заявка.</p>
                        </div>
                        <div class="checkout-summary" id="tariff-card">
                            <h3 class="tariff-card-name" id="tariff-name">{active["name"]}</h3>
                            <p class="tariff-card-desc" id="tariff-desc">{active["description"]}</p>
                            <div class="tariff-card-price" id="tariff-price">
                                <span class="price-amount">{active["price"]}</span>
                                <span class="price-period">{active["period"]}</span>
                            </div>
                            <ul class="tariff-card-features" id="tariff-features">
                                {features_html}
                            </ul>
                        </div>
                    </div>

                    <!-- Партнёр Альфа-Банк (внутри чекаута) — временно скрыт -->
                    <!--
                    <div class="partner-mini" style="margin-top: 2rem; padding: 1rem; border: 1px solid #ffcaca; border-radius: 1rem; background: #fef2f2; display: flex; align-items: center; flex-wrap: wrap; gap: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <div style="display: flex; height: 2.5rem; width: 2.5rem; align-items: center; justify-content: center; border-radius: 0.75rem; background: #EE3424;">
                                <span style="font-size: 1.25rem; font-weight: 900; color: white;">A</span>
                            </div>
                            <div>
                                <p style="font-size: 0.875rem; font-weight: 600; color: #1a1a1f;">Альфа-Банк</p>
                                <span style="font-size: 0.7rem; color: #6b6470;">Партнёр руми</span>
                            </div>
                        </div>
                        <p style="flex:1; font-size: 0.875rem; color: #1a1a1f;">Оплачивай подписку Альфа‑Картой — <span style="color: #EE3424; font-weight: 600;">кешбэк 5%</span></p>
                        <a href="https://alfabank.ru" target="_blank" rel="noopener noreferrer" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; border-radius: 9999px; background: #EE3424; color: #fff; font-size: 0.75rem; font-weight: 500; text-decoration: none;">Оформить карту</a>
                    </div>
                    -->
                </div>
            </div>
        </section>
        {render_footer(user)}
    </main>

    <script>
        // Данные тарифов из Python
        const tariffs = {tariffs_json};

        function switchTariff(planId) {{
            document.querySelectorAll('.tariff-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.dataset.plan === planId);
            }});

            const tariff = tariffs[planId];
            if (!tariff) return;

            document.getElementById('tariff-name').textContent = tariff.name;
            document.getElementById('tariff-desc').textContent = tariff.description;
            const priceEl = document.getElementById('tariff-price');
            priceEl.querySelector('.price-amount').textContent = tariff.price;
            priceEl.querySelector('.price-period').textContent = tariff.period;

            const featuresList = document.getElementById('tariff-features');
            featuresList.innerHTML = tariff.features.map(f => 
                `<li>${{ICON_CIRCLE_CHECK}}<span>${{f}}</span></li>`
            ).join('');

            // Обновляем текст кнопки
            document.getElementById('submit-btn').innerHTML = 'Оплатить ' + tariff.price;

            const url = new URL(window.location);
            url.searchParams.set('plan', planId);
            window.history.pushState({{ plan: planId }}, '', url);
        }}

        document.querySelectorAll('.tariff-btn').forEach(btn => {{
            btn.addEventListener('click', function(e) {{
                const plan = this.dataset.plan;
                switchTariff(plan);
            }});
        }});

        document.addEventListener('DOMContentLoaded', function() {{
            const params = new URLSearchParams(window.location.search);
            const plan = params.get('plan');
            if (plan && tariffs[plan]) {{
                switchTariff(plan);
            }}
        }});

        // Обработка отправки формы
        document.getElementById('submit-btn').addEventListener('click', function(e) {{
            e.preventDefault();
            const checkbox = document.getElementById('terms-checkbox');
            if (!checkbox.checked) {{
                alert('Пожалуйста, согласитесь с условиями использования и политикой конфиденциальности.');
                return;
            }}
            this.textContent = 'Заявка отправлена';
            this.disabled = true;
            this.style.opacity = '0.7';
            this.style.cursor = 'default';
            document.getElementById('submit-note').textContent = 'Мы свяжемся с вами в ближайшее время.';
        }});
    </script>
</body>
</html>"""
    return html