"""refactor material inbox for filtering pipeline

Revision ID: 20260327_01
Revises: 20260325_01
Create Date: 2026-03-27 14:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_01"
down_revision = "20260325_01"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _has_unique_constraint(inspector: sa.Inspector, table_name: str, name: str) -> bool:
    return any(cst["name"] == name for cst in inspector.get_unique_constraints(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "collect_tasks" in tables:
        if not _has_column(inspector, "collect_tasks", "inserted_count"):
            op.add_column("collect_tasks", sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column(inspector, "collect_tasks", "review_count"):
            op.add_column("collect_tasks", sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column(inspector, "collect_tasks", "discard_count"):
            op.add_column("collect_tasks", sa.Column("discard_count", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column(inspector, "collect_tasks", "duplicate_count"):
            op.add_column("collect_tasks", sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column(inspector, "collect_tasks", "failed_count"):
            op.add_column("collect_tasks", sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"))

    if "material_inbox" in tables:
        if not _has_column(inspector, "material_inbox", "source_id"):
            op.add_column("material_inbox", sa.Column("source_id", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "material_inbox", "keyword"):
            op.add_column("material_inbox", sa.Column("keyword", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "material_inbox", "parse_status"):
            op.add_column("material_inbox", sa.Column("parse_status", sa.String(length=32), nullable=False, server_default="success"))
        if not _has_column(inspector, "material_inbox", "risk_status"):
            op.add_column("material_inbox", sa.Column("risk_status", sa.String(length=32), nullable=False, server_default="safe"))
        if not _has_column(inspector, "material_inbox", "quality_score"):
            op.add_column("material_inbox", sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column(inspector, "material_inbox", "relevance_score"):
            op.add_column("material_inbox", sa.Column("relevance_score", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column(inspector, "material_inbox", "lead_score"):
            op.add_column("material_inbox", sa.Column("lead_score", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column(inspector, "material_inbox", "is_duplicate"):
            op.add_column("material_inbox", sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()))
        if not _has_column(inspector, "material_inbox", "filter_reason"):
            op.add_column("material_inbox", sa.Column("filter_reason", sa.Text(), nullable=True))
        if not _has_column(inspector, "material_inbox", "review_note"):
            op.add_column("material_inbox", sa.Column("review_note", sa.Text(), nullable=True))

        if not _has_index(inspector, "material_inbox", "ix_material_inbox_source_id"):
            op.create_index("ix_material_inbox_source_id", "material_inbox", ["source_id"], unique=False)
        if not _has_index(inspector, "material_inbox", "ix_material_inbox_keyword"):
            op.create_index("ix_material_inbox_keyword", "material_inbox", ["keyword"], unique=False)
        if not _has_index(inspector, "material_inbox", "ix_material_inbox_status"):
            op.create_index("ix_material_inbox_status", "material_inbox", ["status"], unique=False)
        if not _has_index(inspector, "material_inbox", "ix_material_inbox_parse_status"):
            op.create_index("ix_material_inbox_parse_status", "material_inbox", ["parse_status"], unique=False)
        if not _has_index(inspector, "material_inbox", "ix_material_inbox_risk_status"):
            op.create_index("ix_material_inbox_risk_status", "material_inbox", ["risk_status"], unique=False)
        if not _has_index(inspector, "material_inbox", "ix_material_inbox_is_duplicate"):
            op.create_index("ix_material_inbox_is_duplicate", "material_inbox", ["is_duplicate"], unique=False)

        # 历史数据状态归一化：approved/negative_case -> review, discarded -> discard, 其他 -> pending
        op.execute(
            """
            UPDATE material_inbox
            SET status = CASE
                WHEN status IN ('approved', 'negative_case') THEN 'review'
                WHEN status = 'discarded' THEN 'discard'
                WHEN status IN ('pending', 'review', 'discard') THEN status
                ELSE 'pending'
            END
            """
        )

        if not _has_unique_constraint(inspector, "material_inbox", "uq_material_inbox_owner_platform_source"):
            op.create_unique_constraint(
                "uq_material_inbox_owner_platform_source",
                "material_inbox",
                ["owner_id", "platform", "source_id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "material_inbox" in tables:
        if _has_unique_constraint(inspector, "material_inbox", "uq_material_inbox_owner_platform_source"):
            op.drop_constraint("uq_material_inbox_owner_platform_source", "material_inbox", type_="unique")

        for idx_name in [
            "ix_material_inbox_is_duplicate",
            "ix_material_inbox_risk_status",
            "ix_material_inbox_parse_status",
            "ix_material_inbox_status",
            "ix_material_inbox_keyword",
            "ix_material_inbox_source_id",
        ]:
            if _has_index(inspector, "material_inbox", idx_name):
                op.drop_index(idx_name, table_name="material_inbox")

        for col_name in [
            "review_note",
            "filter_reason",
            "is_duplicate",
            "lead_score",
            "relevance_score",
            "quality_score",
            "risk_status",
            "parse_status",
            "keyword",
            "source_id",
        ]:
            if _has_column(inspector, "material_inbox", col_name):
                op.drop_column("material_inbox", col_name)

    if "collect_tasks" in tables:
        for col_name in ["failed_count", "duplicate_count", "discard_count", "review_count", "inserted_count"]:
            if _has_column(inspector, "collect_tasks", col_name):
                op.drop_column("collect_tasks", col_name)
