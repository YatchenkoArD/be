"""users.tg_notify_prefs — личные подписки на уведомления

Revision ID: b2c3d4e5f6a7
Revises: f7a8b9c0d1e2
Create Date: 2026-07-20

Запрос руководителя: получать ли пуши — личный выбор каждого владельца/
админа, не общесалонная настройка. Права решают «кто МОЖЕТ получать»
(матрица салона), prefs — «кто ХОЧЕТ». JSON {тема: bool}; NULL или
отсутствие ключа = включено (дефолт — получать всё).
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tg_notify_prefs", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "tg_notify_prefs")
