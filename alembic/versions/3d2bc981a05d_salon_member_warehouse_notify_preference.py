"""salon member warehouse notify preference

Личный тумблер владельца/админа: получать ли Telegram-пуш о заявках склада
(расходник заканчивается / техника сломалась). По умолчанию включено.

Тот же посторонний дрейф схемы, что и в прошлых миграциях (users.salon_id,
NOT NULL в несвязанных таблицах) — снова не включён.

Revision ID: 3d2bc981a05d
Revises: f7a8b9c0d1e2
Create Date: 2026-07-19 15:57:33.493067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3d2bc981a05d'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('salon_members', sa.Column('notify_warehouse_requests', sa.Boolean(), server_default='true', nullable=False))


def downgrade() -> None:
    op.drop_column('salon_members', 'notify_warehouse_requests')
