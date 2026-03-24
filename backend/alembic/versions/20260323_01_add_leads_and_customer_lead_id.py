"""add leads table and customer lead link

Revision ID: 20260323_01
Revises: 
Create Date: 2026-03-23 16:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_01"
down_revision = "20260323_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("leads"):
        op.create_table(
            "leads",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("publish_task_id", sa.Integer(), nullable=True),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("post_url", sa.String(length=500), nullable=True),
            sa.Column("wechat_adds", sa.Integer(), nullable=True),
            sa.Column("leads", sa.Integer(), nullable=True),
            sa.Column("valid_leads", sa.Integer(), nullable=True),
            sa.Column("conversions", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("intention_level", sa.String(length=16), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["publish_task_id"], ["publish_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        lead_columns = {col["name"] for col in inspector.get_columns("leads")}
        lead_missing_columns = [
            ("owner_id", sa.Integer()),
            ("publish_task_id", sa.Integer()),
            ("platform", sa.String(length=32)),
            ("source", sa.String(length=32)),
            ("title", sa.String(length=255)),
            ("post_url", sa.String(length=500)),
            ("wechat_adds", sa.Integer()),
            ("leads", sa.Integer()),
            ("valid_leads", sa.Integer()),
            ("conversions", sa.Integer()),
            ("status", sa.String(length=32)),
            ("intention_level", sa.String(length=16)),
            ("note", sa.Text()),
            ("created_at", sa.DateTime()),
            ("updated_at", sa.DateTime()),
        ]
        for column_name, column_type in lead_missing_columns:
            if column_name not in lead_columns:
                op.add_column("leads", sa.Column(column_name, column_type, nullable=True))

    inspector = sa.inspect(bind)
    lead_columns = {col["name"] for col in inspector.get_columns("leads")}

    lead_indexes = {idx["name"] for idx in inspector.get_indexes("leads")}
    if op.f("ix_leads_id") not in lead_indexes and "id" in lead_columns:
        op.create_index(op.f("ix_leads_id"), "leads", ["id"], unique=False)
    if op.f("ix_leads_owner_id") not in lead_indexes and "owner_id" in lead_columns:
        op.create_index(op.f("ix_leads_owner_id"), "leads", ["owner_id"], unique=False)
    if op.f("ix_leads_publish_task_id") not in lead_indexes and "publish_task_id" in lead_columns:
        op.create_index(op.f("ix_leads_publish_task_id"), "leads", ["publish_task_id"], unique=False)

    customer_columns = {col["name"] for col in inspector.get_columns("customers")}
    if "lead_id" not in customer_columns:
        op.add_column("customers", sa.Column("lead_id", sa.Integer(), nullable=True))

    customer_fks = {fk["name"] for fk in inspector.get_foreign_keys("customers") if fk.get("name")}
    if "fk_customers_lead_id" not in customer_fks:
        op.create_foreign_key("fk_customers_lead_id", "customers", "leads", ["lead_id"], ["id"])

    customer_uniques = {uq["name"] for uq in inspector.get_unique_constraints("customers") if uq.get("name")}
    if "uq_customers_lead_id" not in customer_uniques:
        op.create_unique_constraint("uq_customers_lead_id", "customers", ["lead_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    customer_uniques = {uq["name"] for uq in inspector.get_unique_constraints("customers") if uq.get("name")}
    if "uq_customers_lead_id" in customer_uniques:
        op.drop_constraint("uq_customers_lead_id", "customers", type_="unique")

    customer_fks = {fk["name"] for fk in inspector.get_foreign_keys("customers") if fk.get("name")}
    if "fk_customers_lead_id" in customer_fks:
        op.drop_constraint("fk_customers_lead_id", "customers", type_="foreignkey")

    customer_columns = {col["name"] for col in inspector.get_columns("customers")}
    if "lead_id" in customer_columns:
        op.drop_column("customers", "lead_id")

    if inspector.has_table("leads"):
        lead_indexes = {idx["name"] for idx in inspector.get_indexes("leads")}
        if op.f("ix_leads_publish_task_id") in lead_indexes:
            op.drop_index(op.f("ix_leads_publish_task_id"), table_name="leads")
        if op.f("ix_leads_owner_id") in lead_indexes:
            op.drop_index(op.f("ix_leads_owner_id"), table_name="leads")
        if op.f("ix_leads_id") in lead_indexes:
            op.drop_index(op.f("ix_leads_id"), table_name="leads")
        op.drop_table("leads")
