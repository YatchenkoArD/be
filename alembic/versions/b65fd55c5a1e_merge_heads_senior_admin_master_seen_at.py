"""merge heads: senior admin + master seen_at

Revision ID: b65fd55c5a1e
Revises: 40c19ba85b9f, de5ee0810e2d
Create Date: 2026-07-21 02:03:20.266336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b65fd55c5a1e'
down_revision: Union[str, None] = ('40c19ba85b9f', 'de5ee0810e2d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
