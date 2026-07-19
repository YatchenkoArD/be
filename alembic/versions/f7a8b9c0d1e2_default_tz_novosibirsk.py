"""Часовой пояс продукта — Asia/Novosibirsk (запуск в Сибири)

Revision ID: f7a8b9c0d1e2
Revises: 78a6031c004b
Create Date: 2026-07-19

Решение Артёма 19.07: проект запускается в Новосибирске. Дефолт зоны новых
салонов и существующие демо-салоны (стояла московская) переводятся на
Asia/Novosibirsk. Время броней хранится «настенными часами салона», поэтому
сами брони не пересчитываются — меняется только интерпретация «который час
сейчас» (контейнеры приложения переведены той же выкаткой, TZ в compose).
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "78a6031c004b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "salons", "timezone",
        server_default="Asia/Novosibirsk", existing_type=sa.String(50),
        existing_nullable=False,
    )
    op.execute("UPDATE salons SET timezone = 'Asia/Novosibirsk' WHERE timezone = 'Europe/Moscow'")


def downgrade() -> None:
    op.alter_column(
        "salons", "timezone",
        server_default="Europe/Moscow", existing_type=sa.String(50),
        existing_nullable=False,
    )
