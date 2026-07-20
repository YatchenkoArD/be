# app/scripts/create_admin.py
"""Bootstrap первого администратора (или повышение существующего юзера до ADMIN).

Использование:
    python -m app.scripts.create_admin --phone +7XXXXXXXXXX [--name "Имя"]

Пароль вводится интерактивно (getpass) — НЕ передаётся в аргументах и не пишется
в историю/логи. Хешируется Argon2id. Самостоятельно зарегистрироваться админом
через сайт нельзя (роль назначает только сервер) — это и есть точка входа.
"""
import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine
from app.models.models import User, UserRole
from app.core.security import get_password_hash, validate_password_strength
from app.schemas.user import try_normalize_phone


async def _run(phone: str, name: str | None, password: str) -> None:
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        existing = await db.execute(select(User).where(User.phone == phone))
        user = existing.scalar_one_or_none()

        if user:
            if user.role == UserRole.ADMIN:
                print(f"Пользователь {phone} уже ADMIN — ничего не делаю.")
                return
            user.role = UserRole.ADMIN
            user.is_active = True
            # Через этот скрипт всегда создаётся Старший модератор — иначе
            # некому было бы назначать остальных через веб-панель.
            user.is_senior_admin = True
            if password:
                user.hashed_password = get_password_hash(password)
            await db.commit()
            print(f"Пользователь {phone} повышен до ADMIN (старший модератор).")
        else:
            user = User(
                phone=phone,
                full_name=name,
                hashed_password=get_password_hash(password),
                role=UserRole.ADMIN,
                is_active=True,
                is_senior_admin=True,
            )
            db.add(user)
            await db.commit()
            print(f"Создан администратор {phone} (старший модератор).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Создать/повысить администратора")
    parser.add_argument("--phone", required=True, help="Телефон в формате +7XXXXXXXXXX")
    parser.add_argument("--name", default=None, help="Имя (необязательно)")
    args = parser.parse_args()

    phone = try_normalize_phone(args.phone)
    if not phone:
        print("Ошибка: телефон должен быть в формате +7XXXXXXXXXX", file=sys.stderr)
        sys.exit(1)

    password = getpass.getpass("Пароль администратора: ")
    confirm = getpass.getpass("Повторите пароль: ")
    if password != confirm:
        print("Ошибка: пароли не совпадают", file=sys.stderr)
        sys.exit(1)
    try:
        validate_password_strength(password)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(_run(phone, args.name, password))


if __name__ == "__main__":
    main()
