# app/api/v1/endpoints/inventory.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import InventoryItem, Master, User, UserRole, Booking, WarehouseRequestType
from app.api.deps import check_salon_permission, get_current_user, require_role
from app.services.inventory_service import InventoryService, InventoryError

router = APIRouter()


async def _master_or_404(db: AsyncSession, master_id: int) -> Master:
    master = (await db.execute(select(Master).where(Master.id == master_id))).scalar_one_or_none()
    if not master:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Мастер не найден")
    return master


# ========== Админ/владелец: номенклатура и приход (веб-формы, как services.py) ==========

@router.post("/master/{master_id}/items")
async def create_inventory_item_web(
    master_id: int,
    request: Request,
    name: str = Form(...),
    unit: str = Form(...),
    cost_per_unit: int = Form(...),
    min_quantity: float = Form(0),
    db: AsyncSession = Depends(get_db),
):
    """Добавляет новую позицию номенклатуры на мини-склад мастера."""
    from app.web.auth import get_current_user_from_cookie

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    master = await _master_or_404(db, master_id)
    try:
        await check_salon_permission(db, user, master.salon_id, "manage_inventory")
    except HTTPException:
        return HTMLResponse(content="Недостаточно прав для управления складом", status_code=403)

    db.add(InventoryItem(master_id=master_id, name=name, unit=unit, cost_per_unit=cost_per_unit, min_quantity=min_quantity))
    await db.commit()

    return RedirectResponse(url="/business/dashboard?tab=warehouse&item_added=1", status_code=302)


@router.post("/master/{master_id}/receive")
async def receive_stock_web(
    master_id: int,
    request: Request,
    item_id: int = Form(...),
    quantity: float = Form(...),
    comment: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Приход расходников на мини-склад мастера."""
    from app.web.auth import get_current_user_from_cookie

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    master = await _master_or_404(db, master_id)
    try:
        await check_salon_permission(db, user, master.salon_id, "manage_inventory")
    except HTTPException:
        return HTMLResponse(content="Недостаточно прав для управления складом", status_code=403)

    try:
        await InventoryService.receive_stock(db, item_id=item_id, quantity=quantity, comment=comment, actor=user)
    except InventoryError as e:
        return HTMLResponse(content=e.message, status_code=e.status)

    return RedirectResponse(url="/business/dashboard?tab=warehouse&received=1", status_code=302)


@router.get("/master/{master_id}/stock")
async def get_master_stock_api(
    master_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Остатки мини-склада мастера (для владельца/админа салона)."""
    master = await _master_or_404(db, master_id)
    await check_salon_permission(db, current_user, master.salon_id, "manage_inventory")
    items = await InventoryService.get_master_stock(db, master_id)
    return [
        {"id": i.id, "name": i.name, "unit": i.unit, "quantity": i.quantity,
         "cost_per_unit": i.cost_per_unit, "min_quantity": i.min_quantity}
        for i in items
    ]


# ========== Инвентаризация (JSON — динамический список позиций) ==========

@router.post("/master/{master_id}/audit/start")
async def start_audit_web(
    master_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Открывает акт инвентаризации мини-склада мастера."""
    from app.web.auth import get_current_user_from_cookie

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    master = await _master_or_404(db, master_id)
    try:
        await check_salon_permission(db, user, master.salon_id, "manage_inventory")
    except HTTPException:
        return HTMLResponse(content="Недостаточно прав для управления складом", status_code=403)

    try:
        audit = await InventoryService.start_audit(db, master_id=master_id, actor=user)
    except InventoryError as e:
        return HTMLResponse(content=e.message, status_code=e.status)

    return RedirectResponse(url=f"/business/dashboard?tab=warehouse&audit_id={audit.id}", status_code=302)


class AuditConfirmRequest(BaseModel):
    actual_quantities: dict[int, float]


@router.post("/audit/{audit_id}/confirm")
async def confirm_audit_api(
    audit_id: int,
    body: AuditConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Закрывает акт инвентаризации, фиксируя фактические остатки."""
    from app.models.models import InventoryAudit

    audit = (await db.execute(select(InventoryAudit).where(InventoryAudit.id == audit_id))).scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Акт не найден")
    master = await _master_or_404(db, audit.master_id)
    await check_salon_permission(db, current_user, master.salon_id, "manage_inventory")

    try:
        audit = await InventoryService.confirm_audit(
            db, audit_id=audit_id, actual_quantities=body.actual_quantities, actor=current_user
        )
    except InventoryError as e:
        raise HTTPException(status_code=e.status, detail=e.message)

    return {"id": audit.id, "status": audit.status.value, "confirmed_at": audit.confirmed_at.isoformat()}


# ========== Мастер: свой мини-склад и списание после клиента (JSON self-service) ==========

@router.get("/my/stock")
async def get_my_stock(
    current_user: User = Depends(require_role(UserRole.MASTER)),
    db: AsyncSession = Depends(get_db),
):
    """Остаток своего мини-склада (для кабинета мастера)."""
    master = (await db.execute(select(Master).where(Master.user_id == current_user.id))).scalar_one_or_none()
    if not master:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль мастера не найден")
    items = await InventoryService.get_master_stock(db, master.id)
    return [
        {"id": i.id, "name": i.name, "unit": i.unit, "quantity": i.quantity}
        for i in items
    ]


class ConsumptionLine(BaseModel):
    item_id: int
    quantity: float


class ConsumptionRequest(BaseModel):
    booking_id: int
    items: list[ConsumptionLine]


@router.post("/my/consumption")
async def log_my_consumption(
    body: ConsumptionRequest,
    current_user: User = Depends(require_role(UserRole.MASTER)),
    db: AsyncSession = Depends(get_db),
):
    """Форма мастера после клиента: сколько расходников фактически потрачено."""
    master = (await db.execute(select(Master).where(Master.user_id == current_user.id))).scalar_one_or_none()
    if not master:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль мастера не найден")

    booking_master_id = (await db.execute(
        select(Booking.master_id).where(Booking.id == body.booking_id)
    )).scalar_one_or_none()
    if booking_master_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    if booking_master_id != master.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Это не ваша запись")

    try:
        booking = await InventoryService.log_consumption(
            db, booking_id=body.booking_id,
            items=[{"item_id": line.item_id, "quantity": line.quantity} for line in body.items],
            actor=current_user,
        )
    except InventoryError as e:
        raise HTTPException(status_code=e.status, detail=e.message)

    return {"booking_id": booking.id, "consumption_reported": booking.consumption_reported}


# ========== Техника и инструменты (общий склад салона, только владелец/админ) ==========

@router.post("/salon/{salon_id}/equipment")
async def add_equipment_web(
    salon_id: int,
    request: Request,
    name: str = Form(...),
    quantity: int = Form(1),
    purchased_at: Optional[str] = Form(None),
    service_life_months: Optional[int] = Form(None),
    cost_per_unit: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Добавляет позицию техники/инструментов на общий склад салона."""
    from datetime import date as date_cls
    from app.web.auth import get_current_user_from_cookie

    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    try:
        await check_salon_permission(db, user, salon_id, "manage_inventory")
    except HTTPException:
        return HTMLResponse(content="Недостаточно прав для управления складом", status_code=403)

    parsed_date = None
    if purchased_at:
        try:
            parsed_date = date_cls.fromisoformat(purchased_at)
        except ValueError:
            pass

    try:
        await InventoryService.add_equipment(
            db, salon_id=salon_id, name=name, quantity=quantity,
            purchased_at=parsed_date, service_life_months=service_life_months, cost_per_unit=cost_per_unit,
        )
    except InventoryError as e:
        return HTMLResponse(content=e.message, status_code=e.status)

    return RedirectResponse(url="/business/dashboard?tab=warehouse&equipment_added=1", status_code=302)


@router.post("/salon/{salon_id}/equipment/{equipment_id}/toggle")
async def toggle_equipment_web(
    salon_id: int,
    equipment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Владелец/админ вручную переключает исправно/сломано."""
    await check_salon_permission(db, current_user, salon_id, "manage_inventory")
    try:
        equipment = await InventoryService.toggle_equipment_status(db, equipment_id=equipment_id, salon_id=salon_id)
    except InventoryError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"id": equipment.id, "status": equipment.status.value}


# ========== Заявки: расходник заканчивается / техника сломалась ==========

@router.post("/requests")
async def create_warehouse_request_web(
    request_type: str = Form(...),
    item_id: Optional[int] = Form(None),
    equipment_id: Optional[int] = Form(None),
    comment: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Мастер сигналит: расходник заканчивается, или техника сломалась.
    Доступ — по факту записи Master (не по role, см. has_master_profile)."""
    master = (await db.execute(select(Master).where(Master.user_id == current_user.id))).scalar_one_or_none()
    if master is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет профиля мастера")

    try:
        parsed_type = WarehouseRequestType(request_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректный тип заявки")

    try:
        req = await InventoryService.create_request(
            db, salon_id=master.salon_id, type=parsed_type, created_by=current_user,
            item_id=item_id, equipment_id=equipment_id, comment=comment,
        )
    except InventoryError as e:
        raise HTTPException(status_code=e.status, detail=e.message)

    from app.services.notifications import notify_warehouse_request_created
    await notify_warehouse_request_created(db, req)

    return {"id": req.id, "status": req.status.value}


@router.post("/requests/{request_id}/resolve")
async def resolve_warehouse_request_web(
    request_id: int,
    salon_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_salon_permission(db, current_user, salon_id, "manage_inventory")
    try:
        req = await InventoryService.resolve_request(db, request_id=request_id, salon_id=salon_id, actor=current_user)
    except InventoryError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"id": req.id, "status": req.status.value}


@router.post("/requests/{request_id}/dismiss")
async def dismiss_warehouse_request_web(
    request_id: int,
    salon_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_salon_permission(db, current_user, salon_id, "manage_inventory")
    try:
        req = await InventoryService.dismiss_request(db, request_id=request_id, salon_id=salon_id, actor=current_user)
    except InventoryError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"id": req.id, "status": req.status.value}


@router.post("/salon/{salon_id}/notify-toggle")
async def toggle_warehouse_notify_web(
    salon_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Личный тумблер: получать ли Telegram-пуш о заявках склада. Каждый
    участник переключает только свою запись — не общая настройка салона."""
    from app.models.models import SalonMember

    member = (await db.execute(
        select(SalonMember).where(
            SalonMember.salon_id == salon_id,
            SalonMember.user_id == current_user.id,
            SalonMember.is_active == True,
        )
    )).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не участник этого салона")

    member.notify_warehouse_requests = not member.notify_warehouse_requests
    await db.commit()
    return {"notify_warehouse_requests": member.notify_warehouse_requests}
