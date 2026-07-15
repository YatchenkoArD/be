"""add salon_members table with flexible per-member permissions;
rename salons.owner_id -> creator_id (nullable, no longer unique);
add admin_audit.salon_id

Revision ID: f3a9c7d1e5b2
Revises: c1a2b3d4e5f6
Create Date: 2026-07-10
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f3a9c7d1e5b2"
down_revision: Union[str, None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Держим копию дефолтных прав владельца прямо в миграции (а не импортируем
# из app.models) — так старая миграция не сломается, если модель изменится.
SALON_PERMISSION_KEYS = (
    "manage_salon", "manage_owners", "manage_admins", "manage_masters",
    "manage_schedule", "manage_promotions", "manage_reviews",
    "view_finances", "manage_tariff", "view_audit_log",
)
OWNER_DEFAULT_PERMISSIONS = {k: True for k in SALON_PERMISSION_KEYS}


def upgrade() -> None:
    # --- salon_members ---
    op.create_table(
        "salon_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("salon_id", sa.Integer(), sa.ForeignKey("salons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        # Значения — по ИМЕНИ члена Python-enum (OWNER/ADMIN), не по .value —
        # так SQLAlchemy Enum(SalonRole) хранит все остальные enum'ы в проекте
        # (UserRole, BookingStatus и т.д.), это должно быть с ними согласовано.
        sa.Column("role", sa.Enum("OWNER", "ADMIN", name="salonrole"), nullable=False),
        sa.Column("is_creator", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("invited_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("salon_id", "user_id", name="uq_salon_member"),
    )
    op.create_index("ix_salon_members_user", "salon_members", ["user_id"])
    op.create_index(
        "uq_salon_creator", "salon_members", ["salon_id"], unique=True,
        postgresql_where=sa.text("is_creator = true"),
    )

    # --- salons.owner_id -> creator_id (nullable, больше не unique — один
    # пользователь теперь может быть создателем нескольких салонов) ---
    op.execute("ALTER TABLE salons DROP CONSTRAINT IF EXISTS salons_owner_id_key")
    op.alter_column("salons", "owner_id", new_column_name="creator_id", nullable=True)

    # --- admin_audit.salon_id (NULL = платформенное действие) ---
    op.add_column(
        "admin_audit",
        sa.Column("salon_id", sa.Integer(), sa.ForeignKey("salons.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_admin_audit_salon", "admin_audit", ["salon_id"])

    # --- data-migration: у каждого существующего салона с валидным
    # creator_id создаём SalonMember(is_creator=True, role=owner) ---
    conn = op.get_bind()
    salons = conn.execute(sa.text("SELECT id, creator_id FROM salons WHERE creator_id IS NOT NULL")).fetchall()
    permissions_json = json.dumps(OWNER_DEFAULT_PERMISSIONS)
    for salon_id, creator_id in salons:
        user_exists = conn.execute(
            sa.text("SELECT 1 FROM users WHERE id = :uid"), {"uid": creator_id}
        ).fetchone()
        if not user_exists:
            continue  # битые/тестовые данные — пропускаем, не роняем миграцию
        conn.execute(
            sa.text(
                """
                INSERT INTO salon_members
                    (salon_id, user_id, role, is_creator, permissions, is_active, created_at)
                VALUES
                    (:salon_id, :user_id, 'OWNER', true, CAST(:permissions AS JSON), true, now())
                """
            ),
            {"salon_id": salon_id, "user_id": creator_id, "permissions": permissions_json},
        )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_salon", table_name="admin_audit")
    op.drop_column("admin_audit", "salon_id")

    op.alter_column("salons", "creator_id", new_column_name="owner_id", nullable=True)
    op.create_unique_constraint("salons_owner_id_key", "salons", ["owner_id"])

    op.drop_index("uq_salon_creator", table_name="salon_members")
    op.drop_index("ix_salon_members_user", table_name="salon_members")
    op.drop_table("salon_members")
    op.execute("DROP TYPE IF EXISTS salonrole")
