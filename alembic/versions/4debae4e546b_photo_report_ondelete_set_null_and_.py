"""photo report ondelete set null and relaxed check

При resolve жалобы (см. app/api/v1/endpoints/reports.py) удаляемое фото было
связано с PhotoReport через ondelete=CASCADE — тот же db.delete(photo)
стирал саму запись жалобы вместе с фото, уничтожая историю модерации в
момент её создания. Меняем на SET NULL и ослабляем CHECK-constraint (ровно
одна цель — только на создании; после resolve обе могут быть NULL).

Тот же посторонний дрейф схемы, что и в прошлой миграции (users.salon_id,
NOT NULL в десятке несвязанных таблиц) — снова сознательно не включён.

Revision ID: 4debae4e546b
Revises: d7ddb3b2c976
Create Date: 2026-07-18 21:41:28.878781

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4debae4e546b'
down_revision: Union[str, None] = 'd7ddb3b2c976'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('photo_reports_master_photo_id_fkey', 'photo_reports', type_='foreignkey')
    op.drop_constraint('photo_reports_review_photo_id_fkey', 'photo_reports', type_='foreignkey')
    op.create_foreign_key(
        'photo_reports_master_photo_id_fkey', 'photo_reports', 'master_photos',
        ['master_photo_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'photo_reports_review_photo_id_fkey', 'photo_reports', 'review_photos',
        ['review_photo_id'], ['id'], ondelete='SET NULL',
    )

    op.drop_constraint('check_photo_report_exactly_one_target', 'photo_reports', type_='check')
    op.create_check_constraint(
        'check_photo_report_at_most_one_target',
        'photo_reports',
        '(master_photo_id IS NOT NULL)::int + (review_photo_id IS NOT NULL)::int <= 1',
    )


def downgrade() -> None:
    op.drop_constraint('check_photo_report_at_most_one_target', 'photo_reports', type_='check')
    op.create_check_constraint(
        'check_photo_report_exactly_one_target',
        'photo_reports',
        '(master_photo_id IS NOT NULL)::int + (review_photo_id IS NOT NULL)::int = 1',
    )

    op.drop_constraint('photo_reports_master_photo_id_fkey', 'photo_reports', type_='foreignkey')
    op.drop_constraint('photo_reports_review_photo_id_fkey', 'photo_reports', type_='foreignkey')
    op.create_foreign_key(
        'photo_reports_master_photo_id_fkey', 'photo_reports', 'master_photos',
        ['master_photo_id'], ['id'], ondelete='CASCADE',
    )
    op.create_foreign_key(
        'photo_reports_review_photo_id_fkey', 'photo_reports', 'review_photos',
        ['review_photo_id'], ['id'], ondelete='CASCADE',
    )
