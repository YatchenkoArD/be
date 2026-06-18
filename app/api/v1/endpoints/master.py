# app/api/v1/endpoints/master.py
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib

from app.db.session import get_db
from app.models.models import User, Master, Booking, Salon, UserRole, BookingStatus
from app.api.deps import get_current_user, require_role

router = APIRouter()

@router.get("/schedule")
async def get_my_schedule(
    current_user: User = Depends(require_role([UserRole.MASTER])),
    db: AsyncSession = Depends(get_db)
):
    """Получить своё расписание (только для MASTER)"""
    
    result = await db.execute(
        select(Master).where(Master.user_id == current_user.id)
    )
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Профиль мастера не найден")
    
    bookings_result = await db.execute(
        select(Booking)
        .where(
            Booking.master_id == master.id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
        .order_by(Booking.start_time)
    )
    bookings = bookings_result.scalars().all()
    
    return {
        "master_id": master.id,
        "specialization": master.specialization,
        "bookings": [
            {
                "id": b.id,
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
                "status": b.status.value,
                "client_name": f"Клиент #{b.client_id}"
            }
            for b in bookings
        ]
    }


@router.post("/create-web")
async def create_master_web(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    specialization: str = Form(...),
    experience_years: int = Form(0),
    db: AsyncSession = Depends(get_db)
):
    """Добавление мастера владельцем салона через веб-форму."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login", status_code=302)
    
    salon = (await db.execute(select(Salon).where(Salon.owner_id == user.id))).scalar_one_or_none()
    if not salon:
        return RedirectResponse(url="/business/register-salon", status_code=302)
    
    # Проверяем, нет ли уже мастера с таким телефоном
    existing_user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if existing_user:
        # Если пользователь уже есть, просто создаём профиль мастера
        existing_master = (await db.execute(select(Master).where(Master.user_id == existing_user.id))).scalar_one_or_none()
        if existing_master:
            return RedirectResponse(url="/business/my-salon?error=master_exists", status_code=302)
        master_user = existing_user
    else:
        # Создаём нового пользователя-мастера
        master_user = User(
            phone=phone,
            full_name=full_name,
            hashed_password=hashlib.sha256("master123".encode()).hexdigest(),
            role=UserRole.MASTER,
            is_active=True
        )
        db.add(master_user)
        await db.flush()
    
    # Создаём профиль мастера
    master = Master(
        user_id=master_user.id,
        salon_id=salon.id,
        specialization=specialization,
        experience_years=experience_years,
        rating=0.0
    )
    db.add(master)
    await db.commit()
    
    return RedirectResponse(url="/business/my-salon?added=1", status_code=302)


@router.post("/{master_id}/update")
async def update_master_web(
    master_id: int,
    request: Request,
    full_name: str = Form(...),
    specialization: str = Form(...),
    experience_years: int = Form(0),
    db: AsyncSession = Depends(get_db)
):
    """Обновление данных мастера владельцем салона."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login", status_code=302)
    
    salon = (await db.execute(select(Salon).where(Salon.owner_id == user.id))).scalar_one_or_none()
    if not salon:
        return RedirectResponse(url="/business/register-salon", status_code=302)
    
    master = (await db.execute(select(Master).where(Master.id == master_id, Master.salon_id == salon.id))).scalar_one_or_none()
    if not master:
        return HTMLResponse(content="Мастер не найден", status_code=404)
    
    # Обновляем имя пользователя
    master_user = (await db.execute(select(User).where(User.id == master.user_id))).scalar_one_or_none()
    if master_user:
        master_user.full_name = full_name
    
    # Обновляем данные мастера
    master.specialization = specialization
    master.experience_years = experience_years
    await db.commit()
    
    return RedirectResponse(url="/business/my-salon?updated=1", status_code=302)


@router.post("/{master_id}/delete")
async def delete_master_web(
    master_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Удаление мастера владельцем салона."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login", status_code=302)
    
    master = (await db.execute(select(Master).where(Master.id == master_id))).scalar_one_or_none()
    if not master:
        return HTMLResponse(content="Мастер не найден", status_code=404)
    
    # Проверяем, что мастер принадлежит салону владельца
    salon = (await db.execute(select(Salon).where(Salon.owner_id == user.id))).scalar_one_or_none()
    if not salon or master.salon_id != salon.id:
        return HTMLResponse(content="Нет доступа", status_code=403)
    
    await db.delete(master)
    await db.commit()
    
    return RedirectResponse(url="/business/my-salon?deleted=1", status_code=302)


@router.post("/{master_id}/toggle")
async def toggle_master_web(
    master_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Включение/отключение мастера."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login", status_code=302)
    
    master = (await db.execute(select(Master).where(Master.id == master_id))).scalar_one_or_none()
    if not master:
        return HTMLResponse(content="Мастер не найден", status_code=404)
    
    salon = (await db.execute(select(Salon).where(Salon.owner_id == user.id))).scalar_one_or_none()
    if not salon or master.salon_id != salon.id:
        return HTMLResponse(content="Нет доступа", status_code=403)
    
    master.is_active = not master.is_active
    await db.commit()
    
    return RedirectResponse(url="/business/dashboard?tab=employees", status_code=302)