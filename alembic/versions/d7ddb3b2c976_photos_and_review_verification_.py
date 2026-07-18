"""photos and review verification (portfolio, review photos, reports)

Портфолио мастера (свои фото), фото в отзывах, жалобы на фото + верификация
отзыва реальной COMPLETED-записью. Review.master_id стал nullable — при
уходе мастера из салона привязка снимается (см. toggle_master_web), сам
отзыв остаётся в общем списке салона.

Автогенерация зацепила посторонний дрейф схемы (устаревшая users.salon_id,
NOT NULL-синхронизация в десятке несвязанных таблиц) — сознательно не
включено, это отдельная задача.

Revision ID: d7ddb3b2c976
Revises: e1f2a3b4c5d6
Create Date: 2026-07-18 21:20:18.963887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd7ddb3b2c976'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('master_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('master_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['master_id'], ['masters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('review_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('photo_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('master_photo_id', sa.Integer(), nullable=True),
        sa.Column('review_photo_id', sa.Integer(), nullable=True),
        sa.Column('reporter_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RESOLVED', 'DISMISSED', name='photoreportstatus'), server_default='PENDING', nullable=False),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('(master_photo_id IS NOT NULL)::int + (review_photo_id IS NOT NULL)::int = 1', name='check_photo_report_exactly_one_target'),
        sa.ForeignKeyConstraint(['master_photo_id'], ['master_photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['review_photo_id'], ['review_photos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id']),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_photo_reports_status', 'photo_reports', ['status'], unique=False)

    # op.add_column с новым Enum-типом не создаёт сам тип (это не create_table,
    # автосоздание там не срабатывает) — создаём явно перед использованием.
    op.execute("CREATE TYPE reviewtargettype AS ENUM ('MASTER', 'SALON', 'STAFF')")
    op.add_column('reviews', sa.Column(
        'target_type',
        sa.Enum('MASTER', 'SALON', 'STAFF', name='reviewtargettype', create_type=False),
        server_default='MASTER', nullable=False,
    ))
    op.add_column('reviews', sa.Column('staff_user_id', sa.Integer(), nullable=True))
    op.add_column('reviews', sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('reviews', sa.Column('booking_id', sa.Integer(), nullable=True))
    op.alter_column('reviews', 'master_id', existing_type=sa.INTEGER(), nullable=True)
    op.create_index('ix_reviews_master', 'reviews', ['master_id'], unique=False)
    op.create_index('ix_reviews_salon', 'reviews', ['salon_id'], unique=False)

    # master_id раньше был NOT NULL без явного ondelete (дефолт RESTRICT) —
    # пересоздаём с SET NULL, чтобы отвязка при увольнении мастера (и любое
    # будущее удаление строки Master) не роняла отзыв.
    op.drop_constraint('reviews_master_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_master_id_fkey', 'reviews', 'masters', ['master_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('reviews_booking_id_fkey', 'reviews', 'bookings', ['booking_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('reviews_staff_user_id_fkey', 'reviews', 'users', ['staff_user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('reviews_staff_user_id_fkey', 'reviews', type_='foreignkey')
    op.drop_constraint('reviews_booking_id_fkey', 'reviews', type_='foreignkey')
    op.drop_constraint('reviews_master_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_master_id_fkey', 'reviews', 'masters', ['master_id'], ['id'])

    op.drop_index('ix_reviews_salon', table_name='reviews')
    op.drop_index('ix_reviews_master', table_name='reviews')
    op.alter_column('reviews', 'master_id', existing_type=sa.INTEGER(), nullable=False)
    op.drop_column('reviews', 'booking_id')
    op.drop_column('reviews', 'is_verified')
    op.drop_column('reviews', 'staff_user_id')
    op.drop_column('reviews', 'target_type')

    op.drop_index('ix_photo_reports_status', table_name='photo_reports')
    op.drop_table('photo_reports')
    op.drop_table('review_photos')
    op.drop_table('master_photos')

    op.execute('DROP TYPE IF EXISTS photoreportstatus')
    op.execute('DROP TYPE IF EXISTS reviewtargettype')
