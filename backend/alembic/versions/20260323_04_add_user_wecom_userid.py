"""add user wecom_userid

Revision ID: 20260323_04
Revises: 20260323_03
Create Date: 2026-03-23 23:59:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_04"
down_revision = "20260323_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "wecom_userid" not in user_columns:
        op.add_column("users", sa.Column("wecom_userid", sa.String(64), nullable=True))
        op.create_index("ix_users_wecom_userid", "users", ["wecom_userid"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    index_names = {idx["name"] for idx in inspector.get_indexes("users")}

    if "ix_users_wecom_userid" in index_names:
        op.drop_index("ix_users_wecom_userid", table_name="users")
    if "wecom_userid" in user_columns:
        op.drop_column("users", "wecom_userid")
