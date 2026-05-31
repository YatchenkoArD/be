# app/web/pages/business/tabs/reviews.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Master, User as UserModel


async def render_reviews_tab(db: AsyncSession, reviews, salon) -> str:
    """Вкладка Отзывы."""
    reviews_rows = ""
    for r in reviews:
        client_result = await db.execute(select(UserModel).where(UserModel.id == r.client_id))
        client_user = client_result.scalar_one_or_none()
        client_name = client_user.full_name if client_user else "Клиент"
        
        master_result = await db.execute(select(Master).where(Master.id == r.master_id))
        master = master_result.scalar_one_or_none()
        master_name = "—"
        if master:
            master_user = await db.execute(select(UserModel).where(UserModel.id == master.user_id))
            mu = master_user.scalar_one_or_none()
            master_name = mu.full_name if mu else "Мастер"
        
        stars = "⭐" * r.rating + "☆" * (5 - r.rating)
        date_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else ""
        
        reviews_rows += f"""
        <tr>
            <td><strong>{client_name}</strong></td>
            <td>{master_name}</td>
            <td>{stars}</td>
            <td style="max-width:300px">{r.comment or 'Без комментария'}</td>
            <td style="font-size:0.85rem;color:var(--color-muted)">{date_str}</td>
        </tr>"""
    
    return f"""
    <div id="tab-reviews" class="tab-content">
        <div class="card" style="margin-bottom:1.5rem">
            <div class="rating-summary">
                <div>
                    <div class="rating-big">{salon.rating}</div>
                    <div class="rating-stars">{"⭐" * int(salon.rating)}{"☆" * (5 - int(salon.rating))}</div>
                    <div style="font-size:0.85rem;color:var(--color-muted)">{salon.reviews_count} отзывов</div>
                </div>
            </div>
        </div>
        <div class="card" style="overflow-x:auto">
            <table>
                <thead>
                    <tr><th>Клиент</th><th>Мастер</th><th>Оценка</th><th>Комментарий</th><th>Дата</th></tr>
                </thead>
                <tbody>
                    {reviews_rows or '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--color-muted)">Пока нет отзывов</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>"""