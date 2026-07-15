# app/api/v1/endpoints/staff.py
"""Управление совладельцами/админами салона (вкладка «Сотрудники»)."""
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.models import (
    User, SalonMember, SalonRole, AdminAudit,
    SALON_PERMISSION_KEYS, OWNER_DEFAULT_PERMISSIONS, ADMIN_DEFAULT_PERMISSIONS,
)
from app.schemas.salon_member import (
    SalonMemberResponse, InviteMemberRequest, UpdatePermissionsRequest,
)
from app.api.deps import get_current_user, check_salon_permission
from app.core.security import get_password_hash

router = APIRouter()


def _filter_permissions(overrides: dict) -> dict:
    return {k: bool(v) for k, v in overrides.items() if k in SALON_PERMISSION_KEYS}


@router.post("/invite", response_model=SalonMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: InviteMemberRequest,
    salon_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Приглашает пользователя как совладельца (owner) или админа (admin) салона."""
    required_permission = "manage_owners" if payload.role == SalonRole.OWNER else "manage_admins"
    await check_salon_permission(db, current_user, salon_id, required_permission)

    invited_user = (await db.execute(select(User).where(User.phone == payload.phone))).scalar_one_or_none()
    if invited_user is None:
        # Аналог создания мастера с временным паролем (master.py create_master_web):
        # уникальный случайный пароль, показывается пригласившему один раз.
        temp_password = secrets.token_urlsafe(9)
        invited_user = User(
            phone=payload.phone,
            full_name=payload.full_name,
            hashed_password=get_password_hash(temp_password),
            is_active=True,
        )
        db.add(invited_user)
        await db.flush()

    existing = (await db.execute(
        select(SalonMember).where(
            SalonMember.salon_id == salon_id, SalonMember.user_id == invited_user.id
        )
    )).scalar_one_or_none()
    if existing is not None:
        if existing.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь уже участник этого салона")
        existing.is_active = True
        existing.role = payload.role
        existing.invited_by_id = current_user.id
        member = existing
    else:
        default_perms = dict(OWNER_DEFAULT_PERMISSIONS if payload.role == SalonRole.OWNER else ADMIN_DEFAULT_PERMISSIONS)
        if payload.permissions:
            default_perms.update(_filter_permissions(payload.permissions))
        member = SalonMember(
            salon_id=salon_id,
            user_id=invited_user.id,
            role=payload.role,
            is_creator=False,
            permissions=default_perms,
            is_active=True,
            invited_by_id=current_user.id,
        )
        db.add(member)

    db.add(AdminAudit(
        actor_id=current_user.id, action="invite_salon_member",
        target_type="salon_member", target_id=invited_user.id, salon_id=salon_id,
        detail=f"Приглашён {payload.phone} как {payload.role.value}",
    ))
    await db.commit()

    member = (await db.execute(
        select(SalonMember).options(selectinload(SalonMember.user)).where(SalonMember.id == member.id)
    )).scalar_one()
    return member


@router.post("/{member_id}/permissions", response_model=SalonMemberResponse)
async def update_member_permissions(
    member_id: int,
    payload: UpdatePermissionsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Изменяет набор прав участника. Права создателя менять нельзя — они всегда полные."""
    member = (await db.execute(
        select(SalonMember).options(selectinload(SalonMember.user)).where(SalonMember.id == member_id)
    )).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Участник не найден")

    await check_salon_permission(db, current_user, member.salon_id, "manage_owners")

    if member.is_creator:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя изменить права создателя салона")

    member.permissions = {**member.permissions, **_filter_permissions(payload.permissions)}

    db.add(AdminAudit(
        actor_id=current_user.id, action="update_salon_member_permissions",
        target_type="salon_member", target_id=member.id, salon_id=member.salon_id,
        detail=f"Изменены права участника #{member.user_id}",
    ))
    await db.commit()
    await db.refresh(member)
    return member


@router.delete("/{member_id}")
async def remove_member(
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Снимает участника с бизнес-панели салона (мягкое удаление, is_active=False)."""
    member = (await db.execute(select(SalonMember).where(SalonMember.id == member_id))).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Участник не найден")

    if member.is_creator:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Создателя салона нельзя снять")

    required_permission = "manage_owners" if member.role == SalonRole.OWNER else "manage_admins"
    await check_salon_permission(db, current_user, member.salon_id, required_permission)

    member.is_active = False

    db.add(AdminAudit(
        actor_id=current_user.id, action="remove_salon_member",
        target_type="salon_member", target_id=member.id, salon_id=member.salon_id,
        detail=f"Снят участник #{member.user_id}",
    ))
    await db.commit()
    return {"status": "removed"}
