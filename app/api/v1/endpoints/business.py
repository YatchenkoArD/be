# app/api/v1/endpoints/business.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from fastapi.responses import HTMLResponse

from app.db.session import get_db
from app.models.models import (
    User, Salon, SalonPhoto, Master, Service, Promotion,
    SalonMember, SalonRole, OWNER_DEFAULT_PERMISSIONS, AdminAudit,
)
from app.schemas.business import (
    SalonUpdateRequest,
    SalonResponse,
    MasterResponse,
    ServiceResponse,
    PromotionResponse
)
from app.api.deps import (
    get_current_user, check_salon_permission, get_user_primary_salon_id, get_salon_membership,
)

router = APIRouter()


async def get_current_salon(
    salon_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Salon:
    """
    Резолвит салон, к которому у текущего пользователя есть активное членство
    (owner или admin). Без salon_id — берётся салон, где он создатель, иначе
    первый по дате. Не проверяет конкретное право — только сам факт членства;
    эндпоинты, требующие большего, дополнительно вызывают check_salon_permission.
    """
    resolved_id = await get_user_primary_salon_id(db, current_user.id, salon_id)
    if resolved_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У вас пока нет привязанного салона. Заполните заявку на подключение."
        )
    salon = (await db.execute(select(Salon).where(Salon.id == resolved_id))).scalar_one_or_none()
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Салон не найден")
    return salon


# Оставлено для обратной совместимости импортов из других модулей.
get_owner_salon = get_current_salon


# ========== POST-эндпоинт (создание И обновление салона) ==========
@router.post("/my-salon")
async def create_or_update_salon(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    address: str = Form(...),
    phone: str = Form(...),
    method_override: str = Form(""),
    salon_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Создание ИЛИ обновление салона через веб-форму."""
    from app.web.auth import get_current_user_from_cookie

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # Если method_override=put — это обновление существующего салона
    if method_override == "put":
        resolved_id = await get_user_primary_salon_id(db, user.id, salon_id)
        if resolved_id is None:
            return RedirectResponse(url="/business/register-salon", status_code=302)
        try:
            await check_salon_permission(db, user, resolved_id, "manage_salon")
        except HTTPException:
            return HTMLResponse(content="Недостаточно прав для изменения салона", status_code=403)

        salon = (await db.execute(select(Salon).where(Salon.id == resolved_id))).scalar_one()
        salon.name = name
        salon.description = description
        salon.address = address
        salon.phone = phone
        await db.commit()
        return RedirectResponse(url="/business/dashboard?updated=1", status_code=302)

    # Иначе — создание нового салона. Лимита на число салонов на владельца
    # сейчас нет (тарифы нигде не enforced — вводить гейт только по числу
    # салонов было бы непоследовательно; появится вместе с логикой тарифов).
    salon = Salon(
        creator_id=user.id,
        name=name,
        description=description,
        address=address,
        phone=phone,
        latitude=55.7558,
        longitude=37.6173,
        rating=0.0,
        reviews_count=0,
        is_active=True
    )
    db.add(salon)
    await db.flush()  # получить salon.id до commit

    db.add(SalonMember(
        salon_id=salon.id,
        user_id=user.id,
        role=SalonRole.OWNER,
        is_creator=True,
        permissions=dict(OWNER_DEFAULT_PERMISSIONS),
        is_active=True,
    ))
    await db.commit()
    await db.refresh(salon)

    return RedirectResponse(url="/business/dashboard?success=1", status_code=302)


@router.delete("/my-salon")
async def delete_salon(
    salon_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Удаление салона — доступно только создателю карточки."""
    membership = await check_salon_permission(db, current_user, salon_id, "manage_salon")
    if membership is not None and not membership.is_creator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удалить салон может только его создатель",
        )

    salon = (await db.execute(select(Salon).where(Salon.id == salon_id))).scalar_one_or_none()
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Салон не найден")

    db.add(AdminAudit(
        actor_id=current_user.id, action="delete_salon",
        target_type="salon", target_id=salon.id, salon_id=salon.id,
        detail=f"Удалён салон «{salon.name}»",
    ))
    await db.delete(salon)
    await db.commit()
    return {"status": "deleted"}


@router.get("/my-salon", response_model=SalonResponse)
async def get_my_salon(
    salon: Salon = Depends(get_current_salon)
):
    """Возвращает карточку салона текущего пользователя."""
    return salon


@router.put("/my-salon", response_model=SalonResponse)
async def update_my_salon(
    update_data: SalonUpdateRequest,
    salon: Salon = Depends(get_current_salon),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновляет информацию о своём салоне (API)."""
    await check_salon_permission(db, current_user, salon.id, "manage_salon")

    if update_data.name is not None:
        salon.name = update_data.name
    if update_data.description is not None:
        salon.description = update_data.description
    if update_data.phone is not None:
        salon.phone = update_data.phone
    if update_data.address is not None:
        salon.address = update_data.address
    if update_data.working_hours is not None:
        salon.working_hours = update_data.working_hours

    if update_data.photos is not None:
        old_photos = await db.execute(
            select(SalonPhoto).where(SalonPhoto.salon_id == salon.id)
        )
        for photo in old_photos.scalars().all():
            await db.delete(photo)

        for url in update_data.photos:
            new_photo = SalonPhoto(salon_id=salon.id, url=url)
            db.add(new_photo)

    await db.commit()
    await db.refresh(salon)
    return salon


@router.get("/my-salon/masters", response_model=List[MasterResponse])
async def get_my_masters(
    salon: Salon = Depends(get_current_salon),
    db: AsyncSession = Depends(get_db)
):
    """Список всех мастеров моего салона."""
    result = await db.execute(
        select(Master).where(Master.salon_id == salon.id)
    )
    return result.scalars().all()


@router.get("/my-salon/promotions", response_model=List[PromotionResponse])
async def get_my_promotions(
    salon: Salon = Depends(get_current_salon),
    db: AsyncSession = Depends(get_db)
):
    """Список акций моего салона."""
    result = await db.execute(
        select(Promotion).where(Promotion.salon_id == salon.id)
    )
    return result.scalars().all()


@router.post("/my-salon/promotions", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
async def create_promotion(
    promotion_data: PromotionResponse,
    salon: Salon = Depends(get_current_salon),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создаёт новую акцию для салона."""
    await check_salon_permission(db, current_user, salon.id, "manage_promotions")

    new_promotion = Promotion(
        salon_id=salon.id,
        title=promotion_data.title,
        description=promotion_data.description,
        tag=promotion_data.tag
    )
    db.add(new_promotion)
    await db.commit()
    await db.refresh(new_promotion)
    return new_promotion


@router.get("/my-salon/dashboard")
async def get_business_dashboard(
    salon: Salon = Depends(get_current_salon),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Возвращает сводку для панели бизнеса."""
    from app.models.models import Booking, BookingStatus
    from sqlalchemy import func as sql_func
    from datetime import datetime, timedelta

    masters_count = len(salon.masters)

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    bookings_today = await db.execute(
        select(sql_func.count(Booking.id)).where(
            Booking.master_id.in_([m.id for m in salon.masters]),
            Booking.start_time >= today_start,
            Booking.start_time < today_end
        )
    )
    today_count = bookings_today.scalar() or 0

    # Выручка — только тем, у кого есть view_finances (создатель — всегда).
    revenue = None
    membership = await get_salon_membership(db, current_user.id, salon.id)
    can_view_finances = membership is not None and (
        membership.is_creator or membership.permissions.get("view_finances", False)
    )
    if can_view_finances:
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        revenue_month = await db.execute(
            select(sql_func.sum(Booking.final_price)).where(
                Booking.master_id.in_([m.id for m in salon.masters]),
                Booking.start_time >= month_start,
                Booking.status == BookingStatus.COMPLETED
            )
        )
        revenue = revenue_month.scalar() or 0

    return {
        "salon_name": salon.name,
        "masters_count": masters_count,
        "today_bookings": today_count,
        "monthly_revenue": revenue,
        "rating": salon.rating,
        "reviews_count": salon.reviews_count
    }


@router.post("/my-salon/promotions/web")
async def create_promotion_web(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    tag: str = Form(...),
    salon_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Создание акции через веб-форму."""
    from app.web.auth import get_current_user_from_cookie

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    resolved_id = await get_user_primary_salon_id(db, user.id, salon_id)
    if resolved_id is None:
        return RedirectResponse(url="/business/register-salon", status_code=302)
    try:
        await check_salon_permission(db, user, resolved_id, "manage_promotions")
    except HTTPException:
        return HTMLResponse(content="Недостаточно прав для управления акциями", status_code=403)

    promo = Promotion(
        salon_id=resolved_id,
        title=title,
        description=description,
        tag=tag
    )
    db.add(promo)
    await db.commit()

    return RedirectResponse(url="/business/my-salon?promo_added=1", status_code=302)


@router.post("/my-salon/promotions/{promo_id}/delete")
async def delete_promotion_web(
    promo_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Удаление акции."""
    from app.web.auth import get_current_user_from_cookie

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    promo = (await db.execute(select(Promotion).where(Promotion.id == promo_id))).scalar_one_or_none()
    if not promo:
        return HTMLResponse(content="Акция не найдена", status_code=404)

    try:
        await check_salon_permission(db, user, promo.salon_id, "manage_promotions")
    except HTTPException:
        return HTMLResponse(content="Недостаточно прав для управления акциями", status_code=403)

    await db.delete(promo)
    await db.commit()

    return RedirectResponse(url="/business/my-salon?promo_deleted=1", status_code=302)
