# app/web/pages/salons.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Salon
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles
from app.web.components.icons import (
    ICON_SEARCH,
    ICON_MAP_PIN,
    ICON_STAR_FILLED,
    ICON_HEART,
    ICON_HEART_FILLED,
    ICON_ARROW_RIGHT,
)


async def render_salons_page(db: AsyncSession, user=None) -> str:
    """Страница со списком салонов."""

    result = await db.execute(
        select(Salon).where(Salon.is_active == True).order_by(Salon.rating.desc())
    )
    salons = result.scalars().all()

    salon_cards = ""
    for s in salons:
        # Теги услуг (из описания)
        service_chips = ""
        if s.description:
            keywords = ["стрижка", "борода", "маникюр", "педикюр", "окрашивание", "укладка", "брови"]
            found = [kw for kw in keywords if kw in s.description.lower()]
            if found:
                service_chips = "".join(
                    f'<span class="service-chip">{kw.capitalize()}</span>' for kw in found[:3]
                )
        if not service_chips:
            service_chips = '<span class="service-chip">Услуги</span>'

        rating = s.rating or 0.0
        reviews = s.reviews_count or 0

        heart_svg = ICON_HEART.replace('"', '&quot;')
        heart_filled_svg = ICON_HEART_FILLED.replace('"', '&quot;')

        salon_cards += f"""
        <div class="salon-card" data-salon-id="{s.id}">
            <div class="salon-card-inner">
                <div class="salon-image">
                    <img src="{s.logo_url or '/static/images/default-salon.jpg'}" alt="{s.name}">
                    <button class="favorite-btn" 
                            data-type="salon" 
                            data-id="{s.id}" 
                            data-icon-heart="{heart_svg}"
                            data-icon-heart-filled="{heart_filled_svg}"
                            title="В избранное">
                        <span class="heart-icon">{ICON_HEART}</span>
                    </button>
                    <div class="salon-rating-badge">
                        {ICON_STAR_FILLED}
                        <span class="rating-value">{rating:.1f}</span>
                        <span class="rating-count">({reviews})</span>
                    </div>
                </div>

                <div class="salon-info">
                    <div>
                        <h3 class="salon-name">{s.name}</h3>
                        <p class="salon-address">
                            {ICON_MAP_PIN}
                            {s.address or 'Адрес не указан'}
                        </p>
                    </div>
                    <p class="salon-desc">{s.description or ''}</p>
                    <div class="services-chips">
                        {service_chips}
                    </div>
                    <a href="/salons/{s.id}" class="btn-primary salon-btn">
                        Смотреть мастеров
                        {ICON_ARROW_RIGHT}
                    </a>
                </div>
            </div>
        </div>
        """

    if not salons:
        salon_cards = """
        <div class="salon-card" style="padding:3rem;text-align:center;">
            <p class="text-muted">Пока нет салонов. <a href="/register" style="color:var(--color-primary);">Зарегистрируйтесь</a> как владелец, чтобы добавить первый салон!</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Салоны — руми</title>
    <meta name="description" content="Найдите лучший салон красоты рядом с вами.">
    {get_base_styles()}
</head>
<body>
    {render_header("salons")}
    {render_sidebar("salons", user)}

    <main class="main-content">
        <section class="section-py bg-surface-alt salons-hero">
            <div class="section-container">
                <div class="salons-hero-content">
                    <h1 class="text-display salons-title">Салоны красоты</h1>
                    <p class="text-body-lg salons-subtitle">Найдите лучший салон рядом с вами по названию или услуге</p>
                    <div class="search-box">
                        {ICON_SEARCH}
                        <input type="text" id="searchInput" placeholder="Поиск салона по названию..." class="search-input">
                    </div>
                </div>
            </div
        </section>

        <section class="section-py bg-surface salons-list-section">
            <div class="section-container">
                <div id="salons-list" class="salons-grid">
                    {salon_cards}
                </div>
            </div>
        </section>

        {render_footer(user)}
    </main>

    <script src="/static/js/pages/salons.js"></script>
</body>
</html>"""

    return html