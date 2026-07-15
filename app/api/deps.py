# app/api/deps.py
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import User, UserRole, SalonMember
from app.core.config import settings
from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Декодирует JWT-токен, находит пользователя и возвращает его."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


def require_role(*roles: UserRole):
    """
    Фабрика зависимостей для проверки ролей.
    Использование: Depends(require_role(UserRole.BUSINESS, UserRole.MASTER))
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется одна из ролей: {[r.value for r in roles]}"
            )
        return current_user
    return role_checker


async def get_salon_membership(
    db: AsyncSession, user_id: int, salon_id: int
) -> Optional[SalonMember]:
    """Активное членство пользователя в салоне (owner/admin), либо None."""
    result = await db.execute(
        select(SalonMember).where(
            SalonMember.user_id == user_id,
            SalonMember.salon_id == salon_id,
            SalonMember.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_user_primary_salon_id(
    db: AsyncSession, user_id: int, salon_id: Optional[int] = None
) -> Optional[int]:
    """
    Резолвит «текущий» салон пользователя для эндпоинтов без явного salon_id
    в пути (историческое `/my-salon`). Если salon_id передан — проверяет, что
    пользователь в нём активный участник. Иначе берёт салон, где пользователь
    создатель, а при нескольких/отсутствии — самое старое активное членство.
    """
    query = select(SalonMember).where(
        SalonMember.user_id == user_id, SalonMember.is_active == True
    )
    if salon_id is not None:
        query = query.where(SalonMember.salon_id == salon_id)
    query = query.order_by(SalonMember.is_creator.desc(), SalonMember.created_at.asc())
    membership = (await db.execute(query)).scalars().first()
    return membership.salon_id if membership else None


async def check_salon_permission(
    db: AsyncSession, user: User, salon_id: int, permission: str
) -> SalonMember:
    """
    Проверяет, что у пользователя есть указанное право в салоне; кидает 403,
    если нет. Возвращает членство — вызывающий код может переиспользовать его
    (например, чтобы достать permissions ещё раз не запрашивая БД).
    Платформенный UserRole.ADMIN (суперадмин) проходит без проверки членства.
    """
    if user.role == UserRole.ADMIN:
        return None  # суперадмин платформы — членство в конкретном салоне не требуется

    membership = await get_salon_membership(db, user.id, salon_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь участником этого салона",
        )
    if not (membership.is_creator or membership.permissions.get(permission, False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Недостаточно прав: требуется «{permission}»",
        )
    return membership


def require_salon_permission(permission: str):
    """
    FastAPI-зависимость для эндпоинтов, где salon_id есть в пути запроса
    (path param `salon_id`). Для случаев, где salon_id приходит из body или
    вычисляется из другой сущности (например по member_id), вызывайте
    check_salon_permission(...) прямо в теле эндпоинта после загрузки записи.
    """
    async def checker(
        salon_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        await check_salon_permission(db, current_user, salon_id, permission)
        return current_user
    return checker