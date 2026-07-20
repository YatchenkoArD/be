"""salon moderation status (заявка на регистрацию бизнеса)

Модерация регистрации бизнеса: у салона появляется статус заявки
(pending/approved/rejected) + причина отклонения + факт принятия оферты.
Новый салон = pending; СУЩЕСТВУЮЩИЕ салоны переводим в approved, чтобы не
отрезать текущих владельцев от их кабинетов.

Revision ID: b7c1d9e0f2a3
Revises: c8d9e0f1a2b3
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7c1d9e0f2a3'
down_revision: Union[str, None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Значения enum — ИМЕНА членов (конвенция проекта: SQLAlchemy хранит имя).
_moderation = sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='salonmoderationstatus')


def upgrade() -> None:
    bind = op.get_bind()
    _moderation.create(bind, checkfirst=True)
    op.add_column('salons', sa.Column(
        'moderation_status',
        sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='salonmoderationstatus',
                create_type=False),
        server_default='PENDING', nullable=False,
    ))
    op.add_column('salons', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column('salons', sa.Column('offer_accepted_at', sa.DateTime(timezone=True), nullable=True))
    # Существующие салоны считаем одобренными (grandfather): договор уже был.
    op.execute("UPDATE salons SET moderation_status = 'APPROVED', "
               "offer_accepted_at = created_at")


def downgrade() -> None:
    op.drop_column('salons', 'offer_accepted_at')
    op.drop_column('salons', 'rejection_reason')
    op.drop_column('salons', 'moderation_status')
    _moderation.drop(op.get_bind(), checkfirst=True)
