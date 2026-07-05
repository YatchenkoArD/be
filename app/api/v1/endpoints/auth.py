# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import User, UserRole
from app.schemas.user import RegisterRequest, LoginRequest, SendCodeRequest
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    needs_rehash,
    validate_password_strength,
)
from app.core.limiter import (
    limiter,
    is_account_locked,
    register_login_failure,
    reset_login_failures,
)
from app.services import otp_client

router = APIRouter()


@router.post("/register/send-code")
@limiter.limit("3/minute")
async def send_register_code(
    request: Request,
    data: SendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Отправляет код подтверждения на телефон перед регистрацией."""
    existing = await db.execute(select(User).where(User.phone == data.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким номером уже зарегистрирован",
        )

    try:
        result = await otp_client.send_code(data.phone)
    except otp_client.OTPServiceError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return result


@router.post("/register")
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Регистрация нового пользователя.

    Роль ВСЕГДА client — её нельзя задать из запроса (защита от privilege
    escalation). BUSINESS/MASTER назначаются отдельным модерируемым процессом.

    Требует предварительного вызова /register/send-code — телефон должен
    быть подтверждён кодом (request_id/code проверяются в otp-service).
    """
    try:
        validate_password_strength(data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    existing = await db.execute(select(User).where(User.phone == data.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким номером уже зарегистрирован",
        )

    try:
        code_valid = await otp_client.verify_code(data.request_id, data.code, data.phone)
    except otp_client.OTPServiceError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    if not code_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или истёкший код подтверждения",
        )

    user = User(
        phone=data.phone,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        role=UserRole.CLIENT,  # назначается сервером, не из тела запроса
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return {
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role,
        },
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/login")
@limiter.limit("5/minute")  # лимит по IP (общий счётчик в Redis между воркерами)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Вход. Возвращает JWT (Authorization: Bearer <токен>)."""
    # Уровень блокировки по аккаунту (против распределённого брутфорса)
    if await is_account_locked(data.phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Попробуйте через 15 минут.",
        )

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        await register_login_failure(data.phone)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный номер телефона или пароль",
        )

    await reset_login_failures(data.phone)

    # Бесшовная миграция: старый bcrypt/pbkdf2-хеш → переподписываем на Argon2id
    if needs_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(data.password)
        await db.commit()

    token = create_access_token(user.id)
    return {
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role,
        },
        "access_token": token,
        "token_type": "bearer",
    }
