"""add inbox assignment fields

Revision ID: 20260323_03
Revises: 20260323_02
Create Date: 2026-03-23 23:59:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_03"
down_revision = "20260323_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    inbox_columns = {col["name"] for col in inspector.get_columns("inbox_items")}
    if "assigned_to" not in inbox_columns:
        op.add_column("inbox_items", sa.Column("assigned_to", sa.Integer(), nullable=True))
        op.create_index("ix_inbox_items_assigned_to", "inbox_items", ["assigned_to"], unique=False)
        op.create_foreign_key(
            "fk_inbox_items_assigned_to_users",
            "inbox_items",
            "users",
            ["assigned_to"],
            ["id"],
        )

    if "assigned_at" not in inbox_columns:
        op.add_column("inbox_items", sa.Column("assigned_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    inbox_columns = {col["name"] for col in inspector.get_columns("inbox_items")}

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("inbox_items") if fk.get("name")}
    if "fk_inbox_items_assigned_to_users" in fk_names:
        op.drop_constraint("fk_inbox_items_assigned_to_users", "inbox_items", type_="foreignkey")

    index_names = {idx["name"] for idx in inspector.get_indexes("inbox_items")}
    if "ix_inbox_items_assigned_to" in index_names:
        op.drop_index("ix_inbox_items_assigned_to", table_name="inbox_items")

    if "assigned_at" in inbox_columns:
        op.drop_column("inbox_items", "assigned_at")
    if "assigned_to" in inbox_columns:
        op.drop_column("inbox_items", "assigned_to")
