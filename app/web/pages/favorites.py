# app/web/pages/favorites.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Favorite, Salon, Master, User as UserModel
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles


async def render_favorites_page(db: AsyncSession, user) -> str:
    """Страница избранного — салоны и мастера с проверкой актуальности."""
    
    # Получаем все избранные записи пользователя
    favorites_result = await db.execute(
        select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc())
    )
    favorites = favorites_result.scalars().all()
    
    # Разделяем на салоны и мастеров, проверяем актуальность
    salon_cards = ""
    master_cards = ""
    
    for fav in favorites:
        if fav.salon_id:
            salon = (await db.execute(select(Salon).where(Salon.id == fav.salon_id, Salon.is_active == True))).scalar_one_or_none()
            if salon:
                salon_cards += f"""
                <div class="fav-card">
                    <div class="fav-card-header">
                        <h3>🏢 {salon.name}</h3>
                        <span class="fav-rating">⭐ {salon.rating} ({salon.reviews_count})</span>
                    </div>
                    <p style="color:var(--color-muted);font-size:0.9rem;margin-bottom:0.5rem">{salon.address or 'Адрес не указан'}</p>
                    <div style="display:flex;gap:0.5rem">
                        <a href="/salons/{salon.id}" class="btn-outline" style="font-size:0.8rem;padding:0.4rem 0.8rem">Перейти</a>
                        <form action="/api/v1/favorites/toggle-salon/{salon.id}" method="post" style="display:inline">
                            <button type="submit" class="btn-outline" style="color:#ef4444;border-color:#ef4444;font-size:0.8rem;padding:0.4rem 0.8rem">Убрать</button>
                        </form>
                    </div>
                </div>"""
            # else: салон удалён или неактивен — не показываем
        
        elif fav.master_id:
            master = (await db.execute(select(Master).where(Master.id == fav.master_id, Master.is_active == True))).scalar_one_or_none()
            if master:
                # Проверяем, что мастер всё ещё работает в том же салоне
                master_user = (await db.execute(select(UserModel).where(UserModel.id == master.user_id))).scalar_one_or_none()
                master_name = master_user.full_name if master_user else "Мастер"
                salon = (await db.execute(select(Salon).where(Salon.id == master.salon_id, Salon.is_active == True))).scalar_one_or_none()
                salon_name = salon.name if salon else "Салон не указан"
                
                master_cards += f"""
                <div class="fav-card">
                    <div class="fav-card-header">
                        <h3>💇 {master_name}</h3>
                        <span class="fav-rating">⭐ {master.rating}</span>
                    </div>
                    <p style="color:var(--color-muted);font-size:0.9rem;margin-bottom:0.25rem">{master.specialization}</p>
                    <p style="color:var(--color-muted);font-size:0.85rem;margin-bottom:0.5rem">🏢 {salon_name}</p>
                    <div style="display:flex;gap:0.5rem">
                        <a href="/masters/{master.id}" class="btn-outline" style="font-size:0.8rem;padding:0.4rem 0.8rem">Перейти</a>
                        <form action="/api/v1/favorites/toggle-master/{master.id}" method="post" style="display:inline">
                            <button type="submit" class="btn-outline" style="color:#ef4444;border-color:#ef4444;font-size:0.8rem;padding:0.4rem 0.8rem">Убрать</button>
                        </form>
                    </div>
                </div>"""
            # else: мастер уволен или удалён — не показываем
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Избранное — руми</title>
    {get_base_styles()}
    <style>
        .fav-card {{
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 1rem;
            padding: 1.25rem;
            margin-bottom: 0.75rem;
            transition: box-shadow 0.2s;
        }}
        .fav-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}
        .fav-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.25rem;
        }}
        .fav-card-header h3 {{
            font-size: 1.1rem;
            color: var(--color-heading);
        }}
        .fav-rating {{
            font-size: 0.9rem;
            color: var(--color-primary);
            font-weight: 600;
        }}
        .empty-state {{
            text-align: center;
            padding: 3rem;
            color: var(--color-muted);
        }}
    </style>
</head>
<body>
    {render_header("favorites", user)}
    {render_sidebar("favorites")}
    
    <main style="margin-right: 16rem; padding-top: 2rem;">
        <div class="section-container">
            <h1 class="text-display" style="font-size:2rem;margin-bottom:2rem">⭐ Избранное</h1>
            
            <!-- Салоны -->
            <h2 class="text-subtitle" style="font-size:1.25rem;margin-bottom:1rem">🏢 Салоны</h2>
            {salon_cards or '<div class="empty-state"><p>Нет избранных салонов</p><a href="/salons" style="color:var(--color-primary)">Найти салоны</a></div>'}
            
            <!-- Мастера -->
            <h2 class="text-subtitle" style="font-size:1.25rem;margin:2rem 0 1rem">💇 Мастера</h2>
            {master_cards or '<div class="empty-state"><p>Нет избранных мастеров</p><a href="/salons" style="color:var(--color-primary)">Найти мастеров</a></div>'}
        </div>
    </main>
    
    {render_footer()}
</body>
</html>"""
    
    return html