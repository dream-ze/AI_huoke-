"""add workflow, skill execution, reminder tables and customer follow fields

Revision ID: 20260331_04
Revises: 20260331_03
Create Date: 2026-03-31

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "20260331_04"
down_revision = "20260331_03"
branch_labels = None
depends_on = None


def upgrade():
    # 1. 工作流任务表
    op.create_table(
        "workflow_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_type", sa.String(64), nullable=False),
        sa.Column("current_skill", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("retry_count", sa.Integer(), default=0),
        sa.Column("max_retries", sa.Integer(), default=3),
        sa.Column("trace_id", sa.String(64), nullable=False, index=True),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
    )

    # 2. Skill 执行记录表
    op.create_table(
        "skill_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_task_id", sa.Integer(), sa.ForeignKey("workflow_tasks.id"), nullable=False),
        sa.Column("skill_name", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_snapshot", JSONB, nullable=True),
        sa.Column("output_snapshot", JSONB, nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 3. 提醒配置表
    op.create_table(
        "reminder_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("webhook_url", sa.String(512), nullable=True),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("daily_summary_time", sa.String(8), default="09:00"),
        sa.Column("urgent_interval_hours", sa.Integer(), default=1),
        sa.Column("new_customer_hours", sa.Integer(), default=24),
        sa.Column("high_intent_days", sa.Integer(), default=2),
        sa.Column("normal_days", sa.Integer(), default=7),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 4. 提醒日志表
    op.create_table(
        "reminder_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("reminder_type", sa.String(32), nullable=False),
        sa.Column("channel", sa.String(32), default="wecom"),
        sa.Column("status", sa.String(16), default="sent"),
        sa.Column("message_preview", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 5. Customer 表新增跟进时间字段
    op.add_column("customers", sa.Column("next_follow_at", sa.DateTime(), nullable=True))
    op.add_column("customers", sa.Column("last_follow_at", sa.DateTime(), nullable=True))
    op.add_column("customers", sa.Column("last_reminder_sent_at", sa.DateTime(), nullable=True))

    # 创建索引
    op.create_index("ix_workflow_tasks_status", "workflow_tasks", ["status"])
    op.create_index("ix_workflow_tasks_owner", "workflow_tasks", ["owner_id"])
    op.create_index("ix_skill_executions_workflow", "skill_executions", ["workflow_task_id"])


def downgrade():
    op.drop_table("reminder_logs")
    op.drop_table("reminder_configs")
    op.drop_table("skill_executions")
    op.drop_table("workflow_tasks")
    op.drop_column("customers", "last_reminder_sent_at")
    op.drop_column("customers", "last_follow_at")
    op.drop_column("customers", "next_follow_at")
