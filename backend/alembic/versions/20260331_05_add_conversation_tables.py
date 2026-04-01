"""add conversation, message, and lead_profile tables

Revision ID: 20260331_05
Revises: 20260331_04
Create Date: 2026-03-31

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "20260331_05"
down_revision = "20260331_04"
branch_labels = None
depends_on = None


def upgrade():
    # 会话记录表
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("conversation_type", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), default="active"),
        sa.Column("ai_handled", sa.Boolean(), default=True),
        sa.Column("takeover_at", sa.DateTime(), nullable=True),
        sa.Column("takeover_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 消息记录表
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reply_suggestion", JSONB, nullable=True),
        sa.Column("is_sent", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 线索画像表
    op.create_table(
        "lead_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=False, unique=True),
        sa.Column("loan_amount_need", sa.String(32), nullable=True),
        sa.Column("has_house", sa.Boolean(), nullable=True),
        sa.Column("has_car", sa.Boolean(), nullable=True),
        sa.Column("has_provident_fund", sa.Boolean(), nullable=True),
        sa.Column("credit_status", sa.String(32), nullable=True),
        sa.Column("urgency_level", sa.String(16), nullable=True),
        sa.Column("extracted_phone", sa.String(20), nullable=True),
        sa.Column("extracted_wechat", sa.String(64), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), server_default=sa.func.now()),
    )

    # 索引
    op.create_index("ix_conversations_lead", "conversations", ["lead_id"])
    op.create_index("ix_conversations_customer", "conversations", ["customer_id"])
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_messages_conversation", "messages", ["conversation_id"])


def downgrade():
    op.drop_table("lead_profiles")
    op.drop_table("messages")
    op.drop_table("conversations")
