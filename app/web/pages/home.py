# app/web/pages/home.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Salon
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles


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
        <div class="card" style="text-align: center;">
            <div style="width: 4rem; height: 4rem; border-radius: 50%; background: linear-gradient(135deg, var(--color-primary), var(--color-accent)); margin: 0 auto 1rem; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: white; font-weight: bold;">
                {s.name[0]}
            </div>
            <h3 class="text-subtitle" style="font-size: 1.1rem;">{s.name}</h3>
            <p class="text-muted" style="font-size: 0.85rem; margin: 0.5rem 0;">
                📍 {s.address or 'Адрес не указан'}
            </p>
            <p style="font-weight: 600; color: var(--color-primary);">
                ⭐ {s.rating or '0.0'} 
                <span class="text-muted" style="font-weight: 400;">({s.reviews_count or 0} отзывов)</span>
            </p>
            <a href="/salons/{s.id}" class="btn-primary" style="margin-top: 1rem; font-size: 0.85rem; padding: 0.5rem 1rem;">Подробнее</a>
        </div>
        """
    
    if not salons:
        salon_cards = '<p style="text-align: center; grid-column: 1 / -1;">Пока нет салонов. <a href="/register">Зарегистрируйтесь</a> как владелец, чтобы добавить первый салон!</p>'
    
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

    <main style="margin-right: 16rem;">
        <!-- Hero -->
        <section style="position: relative; background: linear-gradient(135deg, #FFF8F6, #F8C8DC33, #F28C6F22); overflow: hidden; padding: 8rem 0 6rem 0;">
            <div class="section-container" style="position: relative; z-index: 10;">
                <div class="badge" style="margin-bottom: 1rem;">Запись в пару кликов</div>
                <h1 class="text-display" style="font-size: 6rem; line-height: 1.1;">Красота — рядом<br>с вами</h1>
                <p style="font-size: 1.1rem; max-width: 32rem; margin-bottom: 2rem; color: var(--color-body);">Выберите услугу, салон и время — готово. Никаких звонков, всё онлайн.</p>
                
                <a href="/salons" style="display: flex; align-items: center; gap: 0.75rem; background: white; border: 2px solid transparent; border-radius: 1rem; padding: 1rem 1.5rem; width: 100%; max-width: 40rem; cursor: pointer; box-shadow: 0 10px 25px rgba(0,0,0,0.08); text-decoration: none; transition: all 0.2s;">
                    <div style="display: flex; align-items: center; justify-content: center; width: 3rem; height: 3rem; background: linear-gradient(135deg, var(--color-primary), var(--color-accent)); border-radius: 50%; color: white; flex-shrink: 0;">
                        🔍
                    </div>
                    <div style="flex: 1; text-align: left;">
                        <span style="display: block; font-weight: 600; color: var(--color-heading); font-size: 1.1rem;">Найти салон или услугу</span>
                        <span style="display: block; color: var(--color-muted); font-size: 0.875rem;">Маникюр, стрижка, окрашивание, брови...</span>
                    </div>
                    <div style="background: linear-gradient(135deg, var(--color-primary), var(--color-accent)); color: white; padding: 0.75rem 1.5rem; border-radius: 2rem; font-weight: 600; font-size: 0.875rem;">Найти</div>
                </a>
                
                <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1.5rem;">
                    <a href="/salons" class="btn-outline" style="font-size: 0.85rem;">✂️ Стрижка</a>
                    <a href="/salons" class="btn-outline" style="font-size: 0.85rem;">💅 Маникюр</a>
                    <a href="/salons" class="btn-outline" style="font-size: 0.85rem;">🎨 Окрашивание</a>
                    <a href="/salons" class="btn-outline" style="font-size: 0.85rem;">✨ Брови</a>
                </div>
                
                <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 2rem;">
                    <span class="text-muted" style="font-size: 0.875rem;">📍 Салоны рядом с вами</span>
                    <span class="text-muted" style="font-size: 0.875rem;">⚡ Запись за 30 секунд</span>
                    <span class="text-muted" style="font-size: 0.875rem;">✅ Проверенные мастера</span>
                </div>
            </div>
        </section>

        <!-- Как записаться -->
        <section class="section-py bg-surface">
            <div class="section-container">
                <div style="text-align: center; margin-bottom: 3rem;">
                    <div class="badge">Просто как 1-2-3</div>
                    <h2 class="text-display" style="font-size: 2.5rem; margin-top: 1rem;">Как записаться?</h2>
                    <p class="text-body" style="max-width: 32rem; margin: 0.5rem auto 0;">Три простых шага — и вы записаны к лучшему мастеру</p>
                </div>
                <div class="grid-3" style="max-width: 48rem; margin: 0 auto;">
                    <div class="card" style="text-align: center;">
                        <div style="width: 3rem; height: 3rem; border-radius: 50%; background: linear-gradient(135deg, var(--color-primary), var(--color-accent)); margin: 0 auto 1rem; display: flex; align-items: center; justify-content: center; color: white;">1</div>
                        <span class="badge" style="margin-bottom: 0.5rem;">Шаг 01</span>
                        <h3 class="text-subtitle" style="font-size: 1.1rem; margin: 0.5rem 0;">Найдите салон</h3>
                        <p class="text-muted" style="font-size: 0.875rem;">Выберите салон или услугу рядом с вами. Фильтры, рейтинги и отзывы помогут.</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <div style="width: 3rem; height: 3rem; border-radius: 50%; background: linear-gradient(135deg, var(--color-primary), var(--color-accent)); margin: 0 auto 1rem; display: flex; align-items: center; justify-content: center; color: white;">2</div>
                        <span class="badge" style="margin-bottom: 0.5rem;">Шаг 02</span>
                        <h3 class="text-subtitle" style="font-size: 1.1rem; margin: 0.5rem 0;">Выберите время</h3>
                        <p class="text-muted" style="font-size: 0.875rem;">Посмотрите свободные окна у мастера и выберите удобное время.</p>
                    </div>
                    <div class="card" style="text-align: center;">
                        <div style="width: 3rem; height: 3rem; border-radius: 50%; background: linear-gradient(135deg, var(--color-primary), var(--color-accent)); margin: 0 auto 1rem; display: flex; align-items: center; justify-content: center; color: white;">3</div>
                        <span class="badge" style="margin-bottom: 0.5rem;">Шаг 03</span>
                        <h3 class="text-subtitle" style="font-size: 1.1rem; margin: 0.5rem 0;">Готово!</h3>
                        <p class="text-muted" style="font-size: 0.875rem;">Приходите в назначенное время. Напоминание придёт заранее.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Популярные салоны -->
        <section class="section-py bg-surface-alt">
            <div class="section-container">
                <div style="text-align: center; margin-bottom: 3rem;">
                    <h2 class="text-display" style="font-size: 2.5rem;">Популярные салоны</h2>
                    <p class="text-muted" style="max-width: 32rem; margin: 0.5rem auto 0;">Лучшие салоны красоты по отзывам пользователей руми</p>
                </div>
                <div class="grid-3" style="max-width: 48rem; margin: 0 auto;">
                    {salon_cards}
                </div>
                <div style="text-align: center; margin-top: 2.5rem;">
                    <a href="/salons" class="btn-outline">Смотреть все салоны →</a>
                </div>
            </div>
        </section>

        {render_footer()}
    </main>
</body>
</html>"""
    
    return html