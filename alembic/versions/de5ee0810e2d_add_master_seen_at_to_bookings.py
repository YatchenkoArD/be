"""add master_seen_at to bookings

Revision ID: de5ee0810e2d
Revises: b7c1d9e0f2a3
Create Date: 2026-07-20 23:06:43.951487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de5ee0810e2d'
down_revision: Union[str, None] = 'b7c1d9e0f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("master_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "master_seen_at")
