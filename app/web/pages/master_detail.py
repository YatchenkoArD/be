# app/web/pages/master_detail.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Master, Service, User
from app.web.components.header import render_header
from app.web.components.footer import render_footer
from app.web.components.sidebar import render_sidebar
from app.web.components.styles import get_base_styles


async def render_master_detail(db: AsyncSession, master_id: int, user=None) -> str:
    """Страница конкретного мастера."""
    
    result = await db.execute(select(Master).where(Master.id == master_id))
    master = result.scalar_one_or_none()
    
    if not master:
        return """<!DOCTYPE html><html><body style="text-align:center;padding:3rem"><h1>Мастер не найден</h1><a href="/">На главную</a></body></html>"""
    
    # Получаем пользователя (имя мастера)
    user_result = await db.execute(select(User).where(User.id == master.user_id))
    master_user = user_result.scalar_one_or_none()
    master_name = master_user.full_name if master_user else "Мастер"
    
    # Получаем услуги мастера
    services_result = await db.execute(
        select(Service).where(Service.master_id == master.id).order_by(Service.price)
    )
    services = services_result.scalars().all()
    
    # Карточки услуг
    services_html = ""
    for srv in services:
        services_html += f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:1rem;border-bottom:1px solid var(--color-border)">
            <div>
                <p style="font-weight:600">{srv.name}</p>
                <p style="font-size:0.8rem;color:var(--color-muted)">{srv.duration_minutes} минут</p>
            </div>
            <div style="font-size:1.25rem;font-weight:700;color:var(--color-primary)">{srv.price} ₽</div>
        </div>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{master_name} — {master.specialization} — руми</title>
    {get_base_styles()}
</head>
<body>
    {render_header("salons")}
    {render_sidebar("salons", user)}
    
    <main style="margin-right: 16rem; padding-top: 2rem;">
        <div class="section-container">
            <a href="/salons/{master.salon_id}" style="color:var(--color-primary);text-decoration:none;margin-bottom:1rem;display:inline-block">← К салону</a>
            
            <div class="card" style="margin-bottom:2rem">
                <div style="display:flex;gap:2rem;align-items:center;margin-bottom:1.5rem">
                    <div style="width:8rem;height:8rem;border-radius:50%;background:linear-gradient(135deg,var(--color-primary),var(--color-accent));display:flex;align-items:center;justify-content:center;font-size:3rem;color:white">
                        {master_name[0]}
                    </div>
                    <div>
                        <h1 class="text-display" style="font-size:2rem">{master_name}</h1>
                        <p style="font-size:1.1rem;color:var(--color-muted)">{master.specialization}</p>
                        <p style="margin-top:0.5rem">⭐ {master.rating} · Опыт {master.experience_years} лет</p>
                        <form action="/api/v1/favorites/toggle-master/{master.id}" method="post" style="display:inline;margin-top:0.5rem">
                            <button type="submit" class="btn-outline" style="font-size:0.8rem;padding:0.4rem 0.8rem" title="Добавить мастера в избранное">⭐ В избранное</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <h2 style="margin-bottom:1rem">Услуги и цены</h2>
            <div class="card">
                {services_html}
            </div>
            
            <div style="margin-top:2rem;text-align:center">
                <a href="/salons/{master.salon_id}" class="btn-primary" style="font-size:1rem;padding:1rem 2rem">Записаться</a>
            </div>
        </div>
        {render_footer(user)}
    </main>
</body>
</html>"""
    
    return html