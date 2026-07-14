# app/api/v1/endpoints/auth_web.py
from urllib.parse import quote
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import User, UserRole
from app.schemas.user import try_normalize_phone
from app.core.config import settings
from app.core.security import (
    create_access_token,      # единая функция для JWT
    get_password_hash,
    verify_password,
    needs_rehash,
    validate_password_strength,
)
from app.core.limiter import limiter, is_account_locked, register_login_failure, reset_login_failures

router = APIRouter()

def _safe_redirect(target: str) -> str:
    """Защита от open redirect."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return "/"
    return target

def _set_auth_cookie(response: RedirectResponse, user_id: int) -> None:
    """Устанавливает cookie с JWT-токеном (используя create_access_token из security)."""
    token = create_access_token(user_id)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        path="/",
    )

@router.post("/login-web")
@limiter.limit("5/minute")
async def login_web(
    request: Request,
    phone: str = Form(...),
    password: str = Form(...),
    redirect: str = Form("/"),
    db: AsyncSession = Depends(get_db),
):
    """Вход через веб-форму."""
    redirect = _safe_redirect(redirect)
    norm_phone = try_normalize_phone(phone)
    lookup_phone = norm_phone or phone
    keep_phone = quote(lookup_phone)

    if norm_phone and await is_account_locked(norm_phone):
        return RedirectResponse(
            url=f"/login?error=locked&redirect={quote(redirect)}&phone={keep_phone}",
            status_code=302,
        )

    result = await db.execute(select(User).where(User.phone == lookup_phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        if norm_phone:
            await register_login_failure(norm_phone)
        return RedirectResponse(
            url=f"/login?error=1&redirect={quote(redirect)}&phone={keep_phone}",
            status_code=302,
        )

    if norm_phone:
        await reset_login_failures(norm_phone)

    # Бесшовная миграция старого хеша на Argon2id
    if needs_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(password)
        await db.commit()

    response = RedirectResponse(url=redirect, status_code=302)
    _set_auth_cookie(response, user.id)
    return response

@router.post("/register-web")
async def register_web(
    request: Request,
    phone: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Регистрация через веб-форму. Роль всегда CLIENT."""
    norm_phone = try_normalize_phone(phone)
    keep = f"phone={quote(norm_phone or phone)}&full_name={quote(full_name)}"

    if norm_phone is None:
        return RedirectResponse(url=f"/register?error=bad_phone&{keep}", status_code=302)

    try:
        validate_password_strength(password)
    except ValueError:
        return RedirectResponse(url=f"/register?error=weak_password&{keep}", status_code=302)

    existing = await db.execute(select(User).where(User.phone == norm_phone))
    if existing.scalar_one_or_none():
        return RedirectResponse(url=f"/register?error=phone_exists&{keep}", status_code=302)

    user = User(
        phone=norm_phone,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        role=UserRole.CLIENT,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    response = RedirectResponse(url="/profile", status_code=302)
    _set_auth_cookie(response, user.id)
    return response