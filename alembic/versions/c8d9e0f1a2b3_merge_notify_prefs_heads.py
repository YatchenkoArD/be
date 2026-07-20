"""merge heads: личные подписки (b2c3d4e5f6a7) + тумблер склада (3d2bc981a05d)

Revision ID: c8d9e0f1a2b3
Revises: b2c3d4e5f6a7, 3d2bc981a05d
Create Date: 2026-07-20

Параллельная работа над одной задачей: Артём — общие личные подписки на
темы (users.tg_notify_prefs + меню в боте), руководитель — per-салонный
тумблер склада (salon_members.notify_warehouse_requests + UI во вкладке).
Обе ветки нужны: рассылка склада учитывает ОБА фильтра.
"""
revision = "c8d9e0f1a2b3"
down_revision = ("b2c3d4e5f6a7", "3d2bc981a05d")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
