"""add loan business tag seed data

Revision ID: 20260402_05
Revises: 20260402_04
Create Date: 2026-04-02

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision = "20260402_05"
down_revision = "20260402_04"
branch_labels = None
depends_on = None

# 助贷业务标签种子数据
SEED_TAGS = [
    # 产品类型 product_type
    {"name": "信贷", "type": "product_type"},
    {"name": "抵押贷", "type": "product_type"},
    {"name": "企业贷", "type": "product_type"},
    {"name": "经营贷", "type": "product_type"},
    {"name": "消费贷", "type": "product_type"},
    # 用户资质 user_qualification
    {"name": "公积金", "type": "user_qualification"},
    {"name": "社保", "type": "user_qualification"},
    {"name": "个体户", "type": "user_qualification"},
    {"name": "企业主", "type": "user_qualification"},
    {"name": "征信花", "type": "user_qualification"},
    {"name": "负债高", "type": "user_qualification"},
    # 内容意图 content_intent
    {"name": "科普", "type": "content_intent"},
    {"name": "避坑", "type": "content_intent"},
    {"name": "案例", "type": "content_intent"},
    {"name": "引流", "type": "content_intent"},
    {"name": "转化", "type": "content_intent"},
    # 平台风格 platform_style
    {"name": "口播", "type": "platform_style"},
    {"name": "图文", "type": "platform_style"},
    {"name": "问答", "type": "platform_style"},
    {"name": "经验帖", "type": "platform_style"},
    # 风险等级 risk_level
    {"name": "低风险", "type": "risk_level"},
    {"name": "中风险", "type": "risk_level"},
    {"name": "高风险", "type": "risk_level"},
    # 转化倾向 conversion_tendency
    {"name": "强转化", "type": "conversion_tendency"},
    {"name": "弱转化", "type": "conversion_tendency"},
    {"name": "品牌向", "type": "conversion_tendency"},
]


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    """检查表是否存在"""
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    """升级：插入助贷标签种子数据（幂等）"""
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # 确保 mvp_tags 表存在
    if not _table_exists(inspector, "mvp_tags"):
        # 表不存在则跳过，由基础迁移创建
        return

    # 获取当前时间
    now = datetime.utcnow()

    # 检查已存在的标签（基于 name + type 唯一约束）
    existing = set()
    result = bind.execute(sa.text("SELECT name, type FROM mvp_tags"))
    for row in result:
        existing.add((row[0], row[1]))

    # 插入不存在的标签
    tags_table = sa.table(
        "mvp_tags",
        sa.column("name", sa.String),
        sa.column("type", sa.String),
        sa.column("created_at", sa.DateTime),
    )

    tags_to_insert = []
    for tag in SEED_TAGS:
        key = (tag["name"], tag["type"])
        if key not in existing:
            tags_to_insert.append(
                {
                    "name": tag["name"],
                    "type": tag["type"],
                    "created_at": now,
                }
            )

    if tags_to_insert:
        op.bulk_insert(tags_table, tags_to_insert)


def downgrade() -> None:
    """回滚：删除本次迁移添加的标签种子数据"""
    bind = op.get_bind()

    # 构建删除条件
    conditions = []
    for tag in SEED_TAGS:
        conditions.append(f"(name = '{tag['name']}' AND type = '{tag['type']}')")

    if conditions:
        delete_sql = f"DELETE FROM mvp_tags WHERE {' OR '.join(conditions)}"
        bind.execute(sa.text(delete_sql))
