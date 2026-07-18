"""equipment and warehouse requests

Общий склад техники/инструментов салона (Equipment) и единая «заявка»
(WarehouseRequest) — расходник заканчивается ИЛИ техника сломалась, оба
случая решает один и тот же админ-воркфлоу на вкладке «Склад».

Тот же посторонний дрейф схемы, что и в прошлых двух миграциях
(users.salon_id, NOT NULL в несвязанных таблицах) — снова не включён.

Revision ID: 78a6031c004b
Revises: 4debae4e546b
Create Date: 2026-07-18 21:53:56.130331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '78a6031c004b'
down_revision: Union[str, None] = '4debae4e546b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
        sa.Column('status', sa.Enum('WORKING', 'BROKEN', name='equipmentstatus'), server_default='WORKING', nullable=False),
        sa.Column('purchased_at', sa.Date(), nullable=True),
        sa.Column('service_life_months', sa.Integer(), nullable=True),
        sa.Column('cost_per_unit', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('warehouse_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salon_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('CONSUMABLE_LOW', 'EQUIPMENT_BROKEN', name='warehouserequesttype'), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=True),
        sa.Column('equipment_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RESOLVED', 'DISMISSED', name='warehouserequeststatus'), server_default='PENDING', nullable=False),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('(item_id IS NOT NULL)::int + (equipment_id IS NOT NULL)::int <= 1', name='check_warehouse_request_at_most_one_target'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['salon_id'], ['salons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_warehouse_requests_salon_status', 'warehouse_requests', ['salon_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_warehouse_requests_salon_status', table_name='warehouse_requests')
    op.drop_table('warehouse_requests')
    op.drop_table('equipment')

    op.execute('DROP TYPE IF EXISTS warehouserequeststatus')
    op.execute('DROP TYPE IF EXISTS warehouserequesttype')
    op.execute('DROP TYPE IF EXISTS equipmentstatus')
