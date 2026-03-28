"""extend generation task with structured outputs and adoption state

Revision ID: 20260328_01
Revises: 20260327_02
Create Date: 2026-03-28 16:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260328_01"
down_revision = "20260327_02"
branch_labels = None
depends_on = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "generation_tasks"):
        return

    additions: list[tuple[str, sa.Column]] = [
        ("tags_json", sa.Column("tags_json", sa.JSON(), nullable=True)),
        ("copies_json", sa.Column("copies_json", sa.JSON(), nullable=True)),
        ("compliance_json", sa.Column("compliance_json", sa.JSON(), nullable=True)),
        ("selected_variant", sa.Column("selected_variant", sa.String(length=64), nullable=True)),
        ("selected_variant_index", sa.Column("selected_variant_index", sa.Integer(), nullable=True)),
        (
            "adoption_status",
            sa.Column("adoption_status", sa.String(length=20), nullable=False, server_default="pending"),
        ),
        ("adopted_at", sa.Column("adopted_at", sa.DateTime(), nullable=True)),
        ("adopted_by_user_id", sa.Column("adopted_by_user_id", sa.Integer(), nullable=True)),
    ]

    for column_name, column in additions:
        if not _has_column(inspector, "generation_tasks", column_name):
            op.add_column("generation_tasks", column)

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "generation_tasks", "ix_generation_tasks_adoption_status"):
        op.create_index("ix_generation_tasks_adoption_status", "generation_tasks", ["adoption_status"], unique=False)
    if not _has_index(inspector, "generation_tasks", "ix_generation_tasks_adopted_by_user_id"):
        op.create_index("ix_generation_tasks_adopted_by_user_id", "generation_tasks", ["adopted_by_user_id"], unique=False)



def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "generation_tasks"):
        return

    if _has_index(inspector, "generation_tasks", "ix_generation_tasks_adopted_by_user_id"):
        op.drop_index("ix_generation_tasks_adopted_by_user_id", table_name="generation_tasks")
    if _has_index(inspector, "generation_tasks", "ix_generation_tasks_adoption_status"):
        op.drop_index("ix_generation_tasks_adoption_status", table_name="generation_tasks")

    inspector = sa.inspect(bind)
    for column_name in [
        "adopted_by_user_id",
        "adopted_at",
        "adoption_status",
        "selected_variant_index",
        "selected_variant",
        "compliance_json",
        "copies_json",
        "tags_json",
    ]:
        if _has_column(inspector, "generation_tasks", column_name):
            op.drop_column("generation_tasks", column_name)
            inspector = sa.inspect(bind)
