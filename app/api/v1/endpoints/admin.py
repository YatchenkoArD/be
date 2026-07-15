# app/api/v1/endpoints/admin.py
"""Действия администратора. Все эндпоинты — только для роли ADMIN (cookie-auth),
каждое изменяющее действие пишется в admin_audit. Защиты: нельзя тронуть себя и
нельзя оставить платформу без активного админа.
"""
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import (
    User, UserRole, Salon, Master, Service, Booking, Review, Promotion,
    SalonPhoto, Favorite, AdminAudit, SalonMember, SalonRole, OWNER_DEFAULT_PERMISSIONS,
)
from app.core.security import get_password_hash
from app.web.auth import get_current_user_from_cookie

router = APIRouter()

# Роли, которые админ может назначать вручную. MASTER исключён —
# мастер создаётся через бизнес-флоу (профиль Master + привязка к салону).
ASSIGNABLE_ROLES = {UserRole.CLIENT, UserRole.MODEL, UserRole.BUSINESS, UserRole.ADMIN}


# ── helpers ──────────────────────────────────────────────────────────────────
async def _get_admin(request: Request, db: AsyncSession):
    user = await get_current_user_from_cookie(request, db)
    if not user or user.role != UserRole.ADMIN or not user.is_active:
        return None
    return user


def _audit(db, actor_id, action, target_type, target_id, detail):
    db.add(AdminAudit(
        actor_id=actor_id, action=action,
        target_type=target_type, target_id=target_id, detail=detail,
    ))


async def _active_admins_excluding(db, exclude_id) -> int:
    q = select(func.count(User.id)).where(
        User.role == UserRole.ADMIN, User.is_active == True, User.id != exclude_id
    )
    return (await db.execute(q)).scalar() or 0


def _back(tab: str, ok: str = "", err: str = "", extra: str = "") -> RedirectResponse:
    url = f"/admin?tab={tab}"
    if ok:
        url += f"&ok={quote(ok)}"
    if err:
        url += f"&err={quote(err)}"
    if extra:
        url += f"&{extra}"
    return RedirectResponse(url=url, status_code=302)


# ── ПОЛЬЗОВАТЕЛИ ─────────────────────────────────────────────────────────────
@router.post("/users/{uid}/role")
async def change_role(uid: int, request: Request, role: str = Form(...), db: AsyncSession = Depends(get_db)):
    admin = await _get_admin(request, db)
    if not admin:
        return RedirectResponse("/login?redirect=/admin", status_code=302)

    target = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not target:
        return _back("users", err="Пользователь не найден")
    try:
        new_role = UserRole(role)
    except ValueError:
        return _back("users", err="Недопустимая роль")
    if new_role not in ASSIGNABLE_ROLES:
        return _back("users", err="Эту роль нельзя назначить вручную")
    if target.id == admin.id:
        return _back("users", err="Нельзя менять собственную роль")
    if target.role == UserRole.ADMIN and new_role != UserRole.ADMIN and await _active_admins_excluding(db, target.id) == 0:
        return _back("users", err="Нельзя разжаловать последнего администратора")

    old = target.role.value
    target.role = new_role
    _audit(db, admin.id, "change_role", "user", target.id, f"{target.phone}: {old} → {new_role.value}")
    await db.commit()
    return _back("users", ok=f"Роль {target.phone}: {old} → {new_role.value}")


@router.post("/users/{uid}/toggle-active")
async def toggle_active(uid: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin(request, db)
    if not admin:
        return RedirectResponse("/login?redirect=/admin", status_code=302)

    target = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not target:
        return _back("users", err="Пользователь не найден")
    if target.id == admin.id:
        return _back("users", err="Нельзя заблокировать самого себя")
    if target.role == UserRole.ADMIN and target.is_active and await _active_admins_excluding(db, target.id) == 0:
        return _back("users", err="Нельзя заблокировать последнего администратора")

    target.is_active = not target.is_active
    state = "разблокирован" if target.is_active else "заблокирован"
    _audit(db, admin.id, "toggle_active", "user", target.id, f"{target.phone}: {state}")
    await db.commit()
    return _back("users", ok=f"{target.phone} {state}")


@router.post("/users/{uid}/reset-password")
async def reset_password(uid: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin(request, db)
    if not admin:
        return RedirectResponse("/login?redirect=/admin", status_code=302)

    target = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not target:
        return _back("users", err="Пользователь не найден")

    temp = secrets.token_urlsafe(9)
    target.hashed_password = get_password_hash(temp)
    _audit(db, admin.id, "reset_password", "user", target.id, f"{target.phone}: сброс пароля")
    await db.commit()
    # временный пароль показываем один раз
    return _back("users", ok=f"Пароль {target.phone} сброшен", extra=f"temp_pw={quote(temp)}&temp_for={quote(target.phone)}")


@router.post("/users/{uid}/delete")
async def delete_user(uid: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin(request, db)
    if not admin:
        return RedirectResponse("/login?redirect=/admin", status_code=302)

    target = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not target:
        return _back("users", err="Пользователь не найден")
    if target.id == admin.id:
        return _back("users", err="Нельзя удалить самого себя")
    if target.role == UserRole.ADMIN and await _active_admins_excluding(db, target.id) == 0:
        return _back("users", err="Нельзя удалить последнего администратора")

    # Сложные связи блокируем — их надо разрулить явно (заблокируйте пользователя)
    owns_salon = (await db.execute(select(func.count(Salon.id)).where(Salon.creator_id == target.id))).scalar() or 0
    is_master = (await db.execute(select(func.count(Master.id)).where(Master.user_id == target.id))).scalar() or 0
    if owns_salon:
        return _back("users", err="Пользователь владеет салоном — сначала переназначьте владельца")
    if is_master:
        return _back("users", err="У пользователя есть профиль мастера — удалите его через салон")

    phone = target.phone
    # Чистим клиентские зависимости и удаляем
    await db.execute(delete(Favorite).where(Favorite.user_id == target.id))
    await db.execute(delete(Review).where(Review.client_id == target.id))
    await db.execute(delete(Booking).where(Booking.client_id == target.id))
    await db.delete(target)
    _audit(db, admin.id, "delete_user", "user", uid, f"удалён {phone}")
    await db.commit()
    return _back("users", ok=f"Пользователь {phone} удалён")


# ── САЛОНЫ ───────────────────────────────────────────────────────────────────
@router.post("/salons/{sid}/toggle-active")
async def salon_toggle(sid: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin(request, db)
    if not admin:
        return RedirectResponse("/login?redirect=/admin", status_code=302)

    salon = (await db.execute(select(Salon).where(Salon.id == sid))).scalar_one_or_none()
    if not salon:
        return _back("salons", err="Салон не найден")
    salon.is_active = not salon.is_active
    state = "активирован" if salon.is_active else "деактивирован"
    _audit(db, admin.id, "salon_toggle", "salon", sid, f"{salon.name}: {state}")
    await db.commit()
    return _back("salons", ok=f"«{salon.name}» {state}")


@router.post("/salons/{sid}/owner")
async def salon_owner(sid: int, request: Request, owner_phone: str = Form(""), db: AsyncSession = Depends(get_db)):
    admin = await _get_admin(request, db)
    if not admin:
        return RedirectResponse("/login?redirect=/admin", status_code=302)

    salon = (await db.execute(select(Salon).where(Salon.id == sid))).scalar_one_or_none()
    if not salon:
        return _back("salons", err="Салон не найден")

    owner_phone = owner_phone.strip()

    # Снимаем is_creator с текущего создателя (если есть) в любом случае —
    # либо совсем снимаем владельца, либо передаём создателя другому.
    current_creator_membership = (await db.execute(
        select(SalonMember).where(SalonMember.salon_id == sid, SalonMember.is_creator == True)
    )).scalar_one_or_none()
    if current_creator_membership is not None:
        current_creator_membership.is_creator = False

    if not owner_phone:  # снять владельца
        salon.creator_id = None
        _audit(db, admin.id, "salon_owner", "salon", sid, f"{salon.name}: владелец снят")
        await db.commit()
        return _back("salons", ok=f"«{salon.name}»: владелец снят")

    owner = (await db.execute(select(User).where(User.phone == owner_phone))).scalar_one_or_none()
    if not owner:
        return _back("salons", err="Пользователь с таким телефоном не найден")

    # Множественные салоны на владельца разрешены — блокировки больше нет.
    membership = (await db.execute(
        select(SalonMember).where(SalonMember.salon_id == sid, SalonMember.user_id == owner.id)
    )).scalar_one_or_none()
    if membership is None:
        membership = SalonMember(
            salon_id=sid, user_id=owner.id, role=SalonRole.OWNER,
            is_creator=True, permissions=dict(OWNER_DEFAULT_PERMISSIONS), is_active=True,
        )
        db.add(membership)
    else:
        membership.role = SalonRole.OWNER
        membership.is_creator = True
        membership.is_active = True

    salon.creator_id = owner.id
    if owner.role != UserRole.ADMIN:
        owner.role = UserRole.BUSINESS  # владелец салона → бизнес-роль (для навигации/UX)
    _audit(db, admin.id, "salon_owner", "salon", sid, f"{salon.name}: владелец → {owner.phone}")
    await db.commit()
    return _back("salons", ok=f"«{salon.name}»: владелец → {owner.phone}")


@router.post("/salons/{sid}/delete")
async def salon_delete(sid: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin(request, db)
    if not admin:
        return RedirectResponse("/login?redirect=/admin", status_code=302)

    salon = (await db.execute(select(Salon).where(Salon.id == sid))).scalar_one_or_none()
    if not salon:
        return _back("salons", err="Салон не найден")

    masters = (await db.execute(select(func.count(Master.id)).where(Master.salon_id == sid))).scalar() or 0
    if masters:
        return _back("salons", err="В салоне есть мастера — сначала удалите их")

    name = salon.name
    await db.execute(delete(Promotion).where(Promotion.salon_id == sid))
    await db.execute(delete(Review).where(Review.salon_id == sid))
    await db.execute(delete(SalonPhoto).where(SalonPhoto.salon_id == sid))
    await db.delete(salon)
    _audit(db, admin.id, "salon_delete", "salon", sid, f"удалён «{name}»")
    await db.commit()
    return _back("salons", ok=f"Салон «{name}» удалён")


# ── ОТЗЫВЫ ───────────────────────────────────────────────────────────────────
@router.post("/reviews/{rid}/delete")
async def review_delete(rid: int, request: Request, db: AsyncSession = Depends(get_db)):
    admin = await _get_admin(request, db)
    if not admin:
        return RedirectResponse("/login?redirect=/admin", status_code=302)

    review = (await db.execute(select(Review).where(Review.id == rid))).scalar_one_or_none()
    if not review:
        return _back("reviews", err="Отзыв не найден")

    master_id, salon_id = review.master_id, review.salon_id
    await db.delete(review)
    await db.flush()

    # пересчёт рейтинга мастера
    master = (await db.execute(select(Master).where(Master.id == master_id))).scalar_one_or_none()
    if master:
        avg = (await db.execute(select(func.avg(Review.rating)).where(Review.master_id == master_id))).scalar()
        master.rating = round(float(avg or 0.0), 1)
    # пересчёт рейтинга и счётчика салона
    salon = (await db.execute(select(Salon).where(Salon.id == salon_id))).scalar_one_or_none()
    if salon:
        cnt = (await db.execute(select(func.count(Review.id)).where(Review.salon_id == salon_id))).scalar() or 0
        avg = (await db.execute(select(func.avg(Review.rating)).where(Review.salon_id == salon_id))).scalar()
        salon.reviews_count = cnt
        salon.rating = round(float(avg or 0.0), 1)

    _audit(db, admin.id, "review_delete", "review", rid, f"удалён отзыв #{rid}")
    await db.commit()
    return _back("reviews", ok="Отзыв удалён, рейтинг пересчитан")
