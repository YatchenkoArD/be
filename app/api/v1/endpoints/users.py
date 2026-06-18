# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import User
from app.schemas.user import UserResponse, UserUpdate
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получить профиль текущего пользователя"""
    return current_user

@router.post("/me")
async def update_me_form(
    request: Request,
    full_name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Обновление имени пользователя через веб-форму."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    user.full_name = full_name
    await db.commit()
    
    return RedirectResponse(url="/profile?success=updated", status_code=302)

@router.patch("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновить профиль текущего пользователя"""
    
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    
    if user_data.email is not None:
        # Проверяем, не занят ли email
        result = await db.execute(
            select(User).where(
                User.email == user_data.email,
                User.id != current_user.id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email уже используется"
            )
        current_user.email = user_data.email
    
    if user_data.avatar_url is not None:
        current_user.avatar_url = user_data.avatar_url
    
    if user_data.portfolio_desc is not None:
        current_user.portfolio_desc = user_data.portfolio_desc
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

@router.post("/me/update-form")
async def update_profile_form(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(None),
    avatar_url: str = Form(None),
    portfolio_desc: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Обновление профиля через форму (веб-интерфейс)."""
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Обновляем базовые поля
    user.full_name = full_name
    
    # Обновляем дополнительные поля если они предоставлены
    if email and email != user.email:
        # Проверяем, не занят ли email другим пользователем
        result = await db.execute(
            select(User).where(
                User.email == email,
                User.id != user.id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return RedirectResponse(
                url="/profile?error=email_taken", 
                status_code=302
            )
        user.email = email
    
    if avatar_url is not None:
        user.avatar_url = avatar_url
    
    if portfolio_desc is not None:
        user.portfolio_desc = portfolio_desc
    
    await db.commit()
    await db.refresh(user)
    
    return RedirectResponse(url="/profile?success=updated", status_code=302)

@router.post("/me/password-form")
async def update_password_form(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Обновление пароля через форму (веб-интерфейс)."""
    import hashlib
    from app.web.auth import get_current_user_from_cookie
    
    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Проверяем текущий пароль
    if user.hashed_password != hashlib.sha256(current_password.encode()).hexdigest():
        return RedirectResponse(
            url="/profile?error=wrong_password", 
            status_code=302
        )
    
    # Проверяем совпадение паролей
    if new_password != confirm_password:
        return RedirectResponse(
            url="/profile?error=password_mismatch", 
            status_code=302
        )
    
    # Проверяем минимальную длину
    if len(new_password) < 6:
        return RedirectResponse(
            url="/profile?error=password_too_short", 
            status_code=302
        )
    
    # Обновляем пароль
    user.hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
    await db.commit()
    
    return RedirectResponse(
        url="/profile?success=password_updated", 
        status_code=302
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить публичный профиль пользователя по ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return user