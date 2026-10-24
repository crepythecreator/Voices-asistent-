"""Режим подтверждения действий ИИ: confirm (по умолчанию) или auto

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("confirm_mode", sa.String(length=16), nullable=False, server_default="confirm"),
    )


def downgrade() -> None:
    op.drop_column("users", "confirm_mode")
