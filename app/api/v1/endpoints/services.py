# app/api/v1/endpoints/services.py
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import Service, Master, Salon

router = APIRouter()


@router.post("/services/create")
async def create_service_web(
    request: Request,
    master_id: int = Form(...),
    name: str = Form(...),
    price: int = Form(...),
    duration_minutes: int = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """Добавление услуги мастеру."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login", status_code=302)
    
    salon = (await db.execute(select(Salon).where(Salon.owner_id == user.id))).scalar_one_or_none()
    if not salon:
        return RedirectResponse(url="/business/register-salon", status_code=302)
    
    # Проверяем, что мастер принадлежит салону владельца
    master = (await db.execute(select(Master).where(Master.id == master_id, Master.salon_id == salon.id))).scalar_one_or_none()
    if not master:
        return HTMLResponse(content="Мастер не найден или не принадлежит вашему салону", status_code=403)
    
    service = Service(
        master_id=master_id,
        name=name,
        price=price,
        duration_minutes=duration_minutes,
        description=description
    )
    db.add(service)
    await db.commit()
    
    return RedirectResponse(url="/business/dashboard?tab=services&added=1", status_code=302)


@router.post("/services/{service_id}/update")
async def update_service_web(
    service_id: int,
    request: Request,
    master_id: int = Form(...),
    name: str = Form(...),
    price: int = Form(...),
    duration_minutes: int = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """Обновление услуги."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login", status_code=302)
    
    salon = (await db.execute(select(Salon).where(Salon.owner_id == user.id))).scalar_one_or_none()
    if not salon:
        return RedirectResponse(url="/business/register-salon", status_code=302)
    
    service = (await db.execute(select(Service).where(Service.id == service_id))).scalar_one_or_none()
    if not service:
        return HTMLResponse(content="Услуга не найдена", status_code=404)
    
    # Проверяем, что услуга принадлежит мастеру из салона владельца
    master = (await db.execute(select(Master).where(Master.id == service.master_id, Master.salon_id == salon.id))).scalar_one_or_none()
    if not master:
        return HTMLResponse(content="Нет доступа", status_code=403)
    
    service.master_id = master_id
    service.name = name
    service.price = price
    service.duration_minutes = duration_minutes
    service.description = description
    await db.commit()
    
    return RedirectResponse(url="/business/dashboard?tab=services&updated=1", status_code=302)


@router.post("/services/{service_id}/delete")
async def delete_service_web(
    service_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Удаление услуги."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role.value != "business":
        return RedirectResponse(url="/login", status_code=302)
    
    salon = (await db.execute(select(Salon).where(Salon.owner_id == user.id))).scalar_one_or_none()
    if not salon:
        return RedirectResponse(url="/business/register-salon", status_code=302)
    
    service = (await db.execute(select(Service).where(Service.id == service_id))).scalar_one_or_none()
    if not service:
        return HTMLResponse(content="Услуга не найдена", status_code=404)
    
    master = (await db.execute(select(Master).where(Master.id == service.master_id, Master.salon_id == salon.id))).scalar_one_or_none()
    if not master:
        return HTMLResponse(content="Нет доступа", status_code=403)
    
    await db.delete(service)
    await db.commit()
    
    return RedirectResponse(url="/business/dashboard?tab=services&deleted=1", status_code=302)