# app/web/pages/home.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Salon
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.web.components.icons import (
    ICON_SEARCH,
    ICON_SCISSORS,
    ICON_SPARKLES,
)


async def render_home_page(db: AsyncSession, user=None) -> str:
    """Главная страница руми."""

    # Получаем популярные салоны
    try:
        result = await db.execute(
            select(Salon).where(Salon.is_active == True).order_by(Salon.rating.desc()).limit(3)
        )
        salons = result.scalars().all()
    except Exception as e:
        print(f"Ошибка загрузки салонов: {e}")
        salons = []

    # Карточки салонов
    salon_cards = ""
    for s in salons:
        salon_cards += f"""
        <div class="card salon-card">
            <div class="salon-avatar">{s.name[0]}</div>
            <h3 class="text-subtitle salon-name">{s.name}</h3>
            <p class="salon-address">📍 {s.address or 'Адрес не указан'}</p>
            <p class="salon-rating">
                ⭐ {s.rating or '0.0'} 
                <span class="salon-rating-count">({s.reviews_count or 0} отзывов)</span>
            </p>
            <a href="/salons/{s.id}" class="btn-primary salon-btn">Подробнее</a>
        </div>
        """

    if not salons:
        salon_cards = '<p class="salon-empty">Пока нет салонов. <a href="/register">Зарегистрируйтесь</a> как владелец, чтобы добавить первый салон!</p>'

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Руми — мастера и салоны красоты рядом</title>
    <meta name="description" content="Платформа для клиентов и бизнеса: находите лучших мастеров, становитесь моделью или управляйте своим салоном.">
    {get_base_styles()}
</head>
<body>
    {render_header("home", user)}
    {render_sidebar("home")}

    <main class="home-main">
        <!-- Hero секция -->
        <section class="home-hero">
            <div class="section-container relative z-10">
                <div class="home-hero-content">
                    <h1 class="home-hero-title text-display">
                        Красота — это просто<span class="dot-primary">.</span>
                    </h1>
                    <p class="home-hero-subtitle text-body-lg">
                        Услуга, салон, время — готово. Без звонков и ожиданий.
                    </p>

                    <!-- Поиск -->
                    <div class="home-search-card">
                        <a href="/salons" class="home-search-link group">
                            <div class="home-search-icon-wrapper">
                                {ICON_SEARCH}
                            </div>
                            <div class="home-search-info">
                                <span class="home-search-title">Найти салон или услугу</span>
                                <span class="home-search-desc">Маникюр, стрижка, окрашивание, брови...</span>
                            </div>
                            <div class="home-search-btn hidden sm:flex">
                                Найти
                            </div>
                        </a>
                    </div>

                    <!-- Теги -->
                    <div class="home-hero-tags">
                        <a href="/salons?service=стрижка" class="home-tag">
                            {ICON_SCISSORS} Стрижка
                        </a>
                        <a href="/salons?service=маникюр" class="home-tag">
                            {ICON_SPARKLES} Маникюр
                        </a>
                        <a href="/salons?service=окрашивание" class="home-tag">
                            {ICON_SPARKLES} Окрашивание
                        </a>
                        <a href="/salons?service=брови" class="home-tag">
                            {ICON_SPARKLES} Брови
                        </a>
                    </div>
                </div>
            </div>
        </section>

        <!-- Как записаться -->
        <section class="section-py" style="background:var(--color-surface);">
            <div class="section-container">
                <div class="how-title-wrapper">
                    <h2 class="how-title">
                        Как записаться<span class="how-title-dot">?</span>
                    </h2>
                    <p class="how-subtitle">
                        Никаких звонков. Никаких форм с десятью полями. Ничего лишнего.
                    </p>
                </div>

                <!-- Сам блок с 4 шагами -->
                <div class="steps-block">
                    <div class="steps-grid">
                        <!-- 01 -->
                        <div class="step-item">
                            <div class="step-number">
                                <span class="step-num">01</span>
                                <span class="step-dot" style="color:var(--color-primary);">.</span>
                            </div>
                            <h3 class="step-headline">Услуга</h3>
                            <p class="step-desc">Выберите, что нужно сделать.</p>
                        </div>
                        <!-- 02 -->
                        <div class="step-item">
                            <div class="step-number">
                                <span class="step-num">02</span>
                                <span class="step-dot" style="color:var(--color-primary);">.</span>
                            </div>
                            <h3 class="step-headline">Салон</h3>
                            <p class="step-desc">Найдите ближайший с нужным мастером.</p>
                        </div>
                        <!-- 03 -->
                        <div class="step-item">
                            <div class="step-number">
                                <span class="step-num">03</span>
                                <span class="step-dot" style="color:var(--color-primary);">.</span>
                            </div>
                            <h3 class="step-headline">Время</h3>
                            <p class="step-desc">Возьмите свободное окно в один тап.</p>
                        </div>
                        <!-- 04 -->
                        <div class="step-item">
                            <div class="step-number">
                                <span class="step-num">04</span>
                                <span class="step-dot" style="color:var(--color-primary);">.</span>
                            </div>
                            <h3 class="step-headline">Готово</h3>
                            <p class="step-desc">Приходите. Напоминание придёт само.</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>
        
        <!-- Популярные салоны -->
        <section class="section-py bg-surface-alt">
            <div class="section-container">
                <div class="section-header">
                    <h2 class="text-display section-title">Популярные салоны</h2>
                    <p class="text-muted section-subtitle">Лучшие салоны красоты по отзывам пользователей руми</p>
                </div>
                <div class="salon-cards-grid">
                    {salon_cards}
                </div>
                <div class="text-center mt-10">
                    <a href="/salons" class="btn-outline">Смотреть все салоны →</a>
                </div>
            </div>
        </section>

        {render_footer()}
    </main>
</body>
</html>"""

    return html