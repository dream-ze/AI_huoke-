"""P0全量Schema升级 - 新增归因体系、合规平台规则

Revision ID: 20260402_02
Revises: 20260402_01
Create Date: 2026-04-02

新增内容：
1. 归因体系表：campaigns, publish_accounts, published_contents, lead_source_attributions, follow_up_records
2. 合规规则表：platform_compliance_rules, auto_rewrite_templates
3. leads表归因字段：campaign_id, publish_account_id, published_content_id, generation_task_id, first_touch_time, attribution_chain
4. customers表评分字段：lead_source_attribution_id, acquisition_channel, qualification_score, auto_score_reason
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers
revision = "20260402_02"
down_revision = "20260402_01"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    """检查表是否存在"""
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    if not _table_exists(inspector, table_name):
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    """执行迁移"""
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # ========== 1. 创建 campaigns 表 ==========
    if not _table_exists(inspector, "campaigns"):
        op.create_table(
            "campaigns",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("start_date", sa.DateTime(), nullable=True),
            sa.Column("end_date", sa.DateTime(), nullable=True),
            sa.Column("target_audience", sa.String(200), nullable=True),
            sa.Column("target_platform", sa.String(50), nullable=True),
            sa.Column("objective", sa.String(100), nullable=True),
            sa.Column("status", sa.String(20), server_default="draft", nullable=True),
            sa.Column("budget", sa.Numeric(15, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index(op.f("ix_campaigns_id"), "campaigns", ["id"], unique=False)

    # ========== 2. 创建 publish_accounts 表 ==========
    if not _table_exists(inspector, "publish_accounts"):
        op.create_table(
            "publish_accounts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("platform", sa.String(50), nullable=False),
            sa.Column("account_name", sa.String(200), nullable=False),
            sa.Column("account_id", sa.String(200), nullable=True),
            sa.Column("avatar_url", sa.String(500), nullable=True),
            sa.Column("follower_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("risk_level", sa.String(20), server_default="low", nullable=True),
            sa.Column("status", sa.String(20), server_default="active", nullable=True),
            sa.Column("daily_post_limit", sa.Integer(), server_default="10", nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index(op.f("ix_publish_accounts_id"), "publish_accounts", ["id"], unique=False)

    # ========== 3. 创建 published_contents 表 ==========
    if not _table_exists(inspector, "published_contents"):
        op.create_table(
            "published_contents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=True),
            sa.Column("generation_result_id", sa.Integer(), sa.ForeignKey("mvp_generation_results.id"), nullable=True),
            sa.Column("publish_account_id", sa.Integer(), sa.ForeignKey("publish_accounts.id"), nullable=True),
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("content_text", sa.Text(), nullable=False),
            sa.Column("platform", sa.String(50), nullable=False),
            sa.Column("publish_time", sa.DateTime(), nullable=True),
            sa.Column("post_url", sa.String(1000), nullable=True),
            sa.Column("views", sa.Integer(), server_default="0", nullable=True),
            sa.Column("likes", sa.Integer(), server_default="0", nullable=True),
            sa.Column("comments", sa.Integer(), server_default="0", nullable=True),
            sa.Column("shares", sa.Integer(), server_default="0", nullable=True),
            sa.Column("wechat_adds", sa.Integer(), server_default="0", nullable=True),
            sa.Column("leads_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index(op.f("ix_published_contents_id"), "published_contents", ["id"], unique=False)

    # ========== 4. 创建 lead_source_attributions 表 ==========
    if not _table_exists(inspector, "lead_source_attributions"):
        op.create_table(
            "lead_source_attributions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=True),
            sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=True),
            sa.Column("publish_account_id", sa.Integer(), sa.ForeignKey("publish_accounts.id"), nullable=True),
            sa.Column("published_content_id", sa.Integer(), sa.ForeignKey("published_contents.id"), nullable=True),
            sa.Column("generation_task_id", sa.Integer(), nullable=True),
            sa.Column("touchpoint_platform", sa.String(50), nullable=True),
            sa.Column("touchpoint_url", sa.String(1000), nullable=True),
            sa.Column("first_touch_time", sa.DateTime(), nullable=True),
            sa.Column("last_touch_time", sa.DateTime(), nullable=True),
            sa.Column("conversion_path", sa.JSON(), nullable=True),
            sa.Column("attribution_type", sa.String(20), server_default="last_touch", nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_lead_source_attributions_id"), "lead_source_attributions", ["id"], unique=False)

    # ========== 5. 创建 follow_up_records 表 ==========
    if not _table_exists(inspector, "follow_up_records"):
        op.create_table(
            "follow_up_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=True),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
            sa.Column("follow_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("follow_date", sa.DateTime(), nullable=False),
            sa.Column("follow_type", sa.String(20), server_default="phone", nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("outcome", sa.String(100), nullable=True),
            sa.Column("next_follow_at", sa.DateTime(), nullable=True),
            sa.Column("next_action", sa.String(200), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_follow_up_records_id"), "follow_up_records", ["id"], unique=False)

    # ========== 6. 创建 platform_compliance_rules 表 ==========
    if not _table_exists(inspector, "platform_compliance_rules"):
        op.create_table(
            "platform_compliance_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("platform", sa.String(50), nullable=False),
            sa.Column("rule_category", sa.String(100), nullable=True),
            sa.Column("keyword_or_pattern", sa.String(500), nullable=False),
            sa.Column("risk_level", sa.String(20), server_default="medium", nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("suggestion", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("idx_platform_compliance_platform", "platform_compliance_rules", ["platform"], unique=False)
        op.create_index("idx_platform_compliance_active", "platform_compliance_rules", ["is_active"], unique=False)
        op.create_index(op.f("ix_platform_compliance_rules_id"), "platform_compliance_rules", ["id"], unique=False)

    # ========== 7. 创建 auto_rewrite_templates 表 ==========
    if not _table_exists(inspector, "auto_rewrite_templates"):
        op.create_table(
            "auto_rewrite_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trigger_pattern", sa.String(500), nullable=False),
            sa.Column("risk_level", sa.String(20), server_default="medium", nullable=False),
            sa.Column("safe_alternative", sa.Text(), nullable=False),
            sa.Column("platform_scope", sa.String(200), nullable=True),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("idx_auto_rewrite_active", "auto_rewrite_templates", ["is_active"], unique=False)
        op.create_index("idx_auto_rewrite_category", "auto_rewrite_templates", ["category"], unique=False)
        op.create_index(op.f("ix_auto_rewrite_templates_id"), "auto_rewrite_templates", ["id"], unique=False)

    # ========== 8. 为 leads 表添加归因字段 ==========
    if _table_exists(inspector, "leads"):
        leads_columns = [
            ("campaign_id", sa.Column("campaign_id", sa.Integer(), nullable=True)),
            ("publish_account_id", sa.Column("publish_account_id", sa.Integer(), nullable=True)),
            ("published_content_id", sa.Column("published_content_id", sa.Integer(), nullable=True)),
            ("generation_task_id", sa.Column("generation_task_id", sa.Integer(), nullable=True)),
            ("first_touch_time", sa.Column("first_touch_time", sa.DateTime(), nullable=True)),
            ("attribution_chain", sa.Column("attribution_chain", sa.JSON(), nullable=True)),
        ]
        for col_name, col_def in leads_columns:
            if not _column_exists(inspector, "leads", col_name):
                op.add_column("leads", col_def)

        # 添加外键约束（幂等）
        try:
            op.create_foreign_key("fk_leads_campaign_id", "leads", "campaigns", ["campaign_id"], ["id"])
        except Exception:
            pass
        try:
            op.create_foreign_key(
                "fk_leads_publish_account_id", "leads", "publish_accounts", ["publish_account_id"], ["id"]
            )
        except Exception:
            pass
        try:
            op.create_foreign_key(
                "fk_leads_published_content_id", "leads", "published_contents", ["published_content_id"], ["id"]
            )
        except Exception:
            pass

    # ========== 9. 为 customers 表添加评分/归因字段 ==========
    if _table_exists(inspector, "customers"):
        customers_columns = [
            ("lead_source_attribution_id", sa.Column("lead_source_attribution_id", sa.Integer(), nullable=True)),
            ("acquisition_channel", sa.Column("acquisition_channel", sa.String(100), nullable=True)),
            ("qualification_score", sa.Column("qualification_score", sa.String(1), nullable=True)),
            ("auto_score_reason", sa.Column("auto_score_reason", sa.Text(), nullable=True)),
        ]
        for col_name, col_def in customers_columns:
            if not _column_exists(inspector, "customers", col_name):
                op.add_column("customers", col_def)

        # 添加外键约束（幂等）
        try:
            op.create_foreign_key(
                "fk_customers_lead_source_attribution_id",
                "customers",
                "lead_source_attributions",
                ["lead_source_attribution_id"],
                ["id"],
            )
        except Exception:
            pass


def downgrade():
    """回滚迁移"""
    # 删除 customers 表新增字段
    for col_name in ["auto_score_reason", "qualification_score", "acquisition_channel", "lead_source_attribution_id"]:
        try:
            op.drop_column("customers", col_name)
        except Exception:
            pass

    # 删除 leads 表新增字段
    for col_name in [
        "attribution_chain",
        "first_touch_time",
        "generation_task_id",
        "published_content_id",
        "publish_account_id",
        "campaign_id",
    ]:
        try:
            op.drop_column("leads", col_name)
        except Exception:
            pass

    # 删除新表（注意顺序：先删有FK依赖的）
    tables_to_drop = [
        "follow_up_records",
        "lead_source_attributions",
        "published_contents",
        "publish_accounts",
        "campaigns",
        "auto_rewrite_templates",
        "platform_compliance_rules",
    ]
    for table_name in tables_to_drop:
        try:
            op.drop_table(table_name)
        except Exception:
            pass
