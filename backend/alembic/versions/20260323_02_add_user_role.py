"""add user role column

Revision ID: 20260323_02
Revises: 20260323_01
Create Date: 2026-03-23 23:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_02"
down_revision = "20260323_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "role" not in user_columns:
        op.add_column("users", sa.Column("role", sa.String(length=32), nullable=True, server_default="operator"))
        op.execute("UPDATE users SET role='operator' WHERE role IS NULL")
        op.alter_column("users", "role", nullable=False, server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "role" in user_columns:
        op.drop_column("users", "role")
