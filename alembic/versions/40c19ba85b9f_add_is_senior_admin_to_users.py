"""add is_senior_admin to users

Revision ID: 40c19ba85b9f
Revises: b7c1d9e0f2a3
Create Date: 2026-07-20 18:35:45.002950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40c19ba85b9f'
down_revision: Union[str, None] = 'b7c1d9e0f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_senior_admin", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Существующие ADMIN-аккаунты уже имели полный доступ до введения
    # уровней — переводим их в senior, чтобы деплой никого не запер
    # (иначе назначать новых модераторов стало бы некому).
    op.execute("UPDATE users SET is_senior_admin = true WHERE role = 'ADMIN'")


def downgrade() -> None:
    op.drop_column("users", "is_senior_admin")
