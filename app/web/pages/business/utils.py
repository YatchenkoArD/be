# app/web/pages/business/utils.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Master, Service, User as UserModel


async def get_masters_data(db: AsyncSession, salon_id: int):
    """Загружает мастеров салона с явной загрузкой пользователей."""
    masters_result = await db.execute(select(Master).where(Master.salon_id == salon_id))
    masters = masters_result.scalars().all()
    
    masters_rows = ""
    for m in masters:
        user_result = await db.execute(select(UserModel).where(UserModel.id == m.user_id))
        master_user = user_result.scalar_one_or_none()
        user_name = master_user.full_name if master_user else "—"
        
        svc_result = await db.execute(select(func.count(Service.id)).where(Service.master_id == m.id))
        svc_count = svc_result.scalar() or 0
        
        masters_rows += f"""
        <tr>
            <td>{user_name}</td>
            <td>{m.specialization}</td>
            <td>{m.experience_years} лет</td>
            <td>{svc_count}</td>
            <td>⭐ {m.rating}</td>
        </tr>
        """
    
    return masters, masters_rows


def get_master_ids(masters):
    """Возвращает список id мастеров."""
    return [m.id for m in masters]