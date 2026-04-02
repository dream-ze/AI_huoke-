"""add loan compliance rules seed data

Revision ID: 20260402_07
Revises: 20260402_06
Create Date: 2026-04-02

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision = "20260402_07"
down_revision = "20260402_06"
branch_labels = None
depends_on = None

# ============================================================
# 助贷专用敏感词 - mvp_compliance_rules 表
# ============================================================

# 承诺下款类
COMPLIANCE_RULES_PROMISE = [
    {"rule_type": "keyword", "keyword": "包下款", "risk_level": "high", "suggestion": "帮您匹配适合的产品方案"},
    {"rule_type": "keyword", "keyword": "保证通过", "risk_level": "high", "suggestion": "协助提升通过率"},
    {"rule_type": "keyword", "keyword": "100%放款", "risk_level": "high", "suggestion": "为您匹配合适产品"},
    {"rule_type": "keyword", "keyword": "必下", "risk_level": "high", "suggestion": "为您推荐合适方案"},
    {"rule_type": "keyword", "keyword": "秒批", "risk_level": "high", "suggestion": "审批流程便捷"},
    {"rule_type": "keyword", "keyword": "秒到", "risk_level": "high", "suggestion": "放款时效较快"},
    {"rule_type": "keyword", "keyword": "包过", "risk_level": "high", "suggestion": "成功率较高"},
]

# 包装资料类
COMPLIANCE_RULES_PACKAGING = [
    {"rule_type": "keyword", "keyword": "包装银行流水", "risk_level": "high", "suggestion": "提供真实资质证明"},
    {"rule_type": "keyword", "keyword": "做假资料", "risk_level": "high", "suggestion": "准备合规材料"},
    {"rule_type": "keyword", "keyword": "代开证明", "risk_level": "high", "suggestion": "自行办理相关证明"},
    {"rule_type": "keyword", "keyword": "包装资料", "risk_level": "high", "suggestion": "完善资质材料"},
    {"rule_type": "keyword", "keyword": "虚假流水", "risk_level": "high", "suggestion": "提供真实银行流水"},
]

# 征信类
COMPLIANCE_RULES_CREDIT = [
    {"rule_type": "keyword", "keyword": "征信洗白", "risk_level": "high", "suggestion": "改善信用记录"},
    {"rule_type": "keyword", "keyword": "征信修复", "risk_level": "high", "suggestion": "规范征信管理"},
    {"rule_type": "keyword", "keyword": "消除逾期", "risk_level": "high", "suggestion": "按时还款改善记录"},
    {"rule_type": "keyword", "keyword": "洗白征信", "risk_level": "high", "suggestion": "合规维护信用"},
]

# 利率误导类
COMPLIANCE_RULES_INTEREST = [
    {"rule_type": "keyword", "keyword": "免息贷款", "risk_level": "high", "suggestion": "限时优惠活动"},
    {"rule_type": "keyword", "keyword": "全网最低", "risk_level": "high", "suggestion": "具有竞争力利率"},
]

# 诱导夸大类
COMPLIANCE_RULES_INDUCE = [
    {"rule_type": "keyword", "keyword": "内部渠道", "risk_level": "high", "suggestion": "正规产品渠道"},
    {"rule_type": "keyword", "keyword": "特殊通道", "risk_level": "high", "suggestion": "标准审批流程"},
    {"rule_type": "keyword", "keyword": "内部门路", "risk_level": "high", "suggestion": "正规渠道申请"},
]

# 合并所有合规规则
ALL_COMPLIANCE_RULES = (
    COMPLIANCE_RULES_PROMISE
    + COMPLIANCE_RULES_PACKAGING
    + COMPLIANCE_RULES_CREDIT
    + COMPLIANCE_RULES_INTEREST
    + COMPLIANCE_RULES_INDUCE
)

# ============================================================
# 自动改写模板 - auto_rewrite_templates 表
# ============================================================

AUTO_REWRITE_TEMPLATES = [
    # 承诺类
    {
        "trigger_pattern": "包下款",
        "safe_alternative": "帮您匹配适合的产品方案",
        "risk_level": "high",
        "category": "承诺类",
    },
    {"trigger_pattern": "保证通过", "safe_alternative": "协助提升通过率", "risk_level": "high", "category": "承诺类"},
    {"trigger_pattern": "秒批", "safe_alternative": "审批流程便捷", "risk_level": "high", "category": "承诺类"},
    {"trigger_pattern": "秒到", "safe_alternative": "放款时效较快", "risk_level": "high", "category": "承诺类"},
    {"trigger_pattern": "必过", "safe_alternative": "通过率较高", "risk_level": "high", "category": "承诺类"},
    {"trigger_pattern": "包过", "safe_alternative": "成功率较高", "risk_level": "high", "category": "承诺类"},
    # 征信类
    {"trigger_pattern": "无视征信", "safe_alternative": "多种产品方案可选", "risk_level": "high", "category": "征信类"},
    {"trigger_pattern": "不看征信", "safe_alternative": "多维度评估", "risk_level": "high", "category": "征信类"},
    {"trigger_pattern": "征信洗白", "safe_alternative": "改善信用记录", "risk_level": "high", "category": "征信类"},
    # 利率类
    {"trigger_pattern": "零利息", "safe_alternative": "利率优惠", "risk_level": "high", "category": "利率类"},
    {"trigger_pattern": "免息贷款", "safe_alternative": "限时优惠活动", "risk_level": "high", "category": "利率类"},
    {"trigger_pattern": "免息", "safe_alternative": "限时优惠", "risk_level": "medium", "category": "利率类"},
    # 渠道类
    {"trigger_pattern": "内部渠道", "safe_alternative": "正规产品渠道", "risk_level": "high", "category": "渠道类"},
    {"trigger_pattern": "特殊通道", "safe_alternative": "标准审批流程", "risk_level": "high", "category": "渠道类"},
    # 引流类
    {
        "trigger_pattern": "私信我",
        "safe_alternative": "了解更多可以留言咨询",
        "risk_level": "medium",
        "category": "引流类",
        "platform_scope": "xiaohongshu",
    },
    {
        "trigger_pattern": "加微信",
        "safe_alternative": "后台私信了解更多",
        "risk_level": "medium",
        "category": "引流类",
        "platform_scope": "xiaohongshu,douyin",
    },
]

# ============================================================
# 平台特定规则 - platform_compliance_rules 表
# ============================================================

PLATFORM_RULES_XIAOHONGSHU = [
    {
        "platform": "xiaohongshu",
        "rule_category": "引流禁止",
        "keyword_or_pattern": r"加微信",
        "risk_level": "high",
        "suggestion": "使用平台私信功能",
        "description": "禁止引导加微信",
    },
    {
        "platform": "xiaohongshu",
        "rule_category": "引流禁止",
        "keyword_or_pattern": r"加v",
        "risk_level": "high",
        "suggestion": "使用平台私信功能",
        "description": "禁止引导加V",
    },
    {
        "platform": "xiaohongshu",
        "rule_category": "引流禁止",
        "keyword_or_pattern": r"私信我",
        "risk_level": "medium",
        "suggestion": "引导用户留言互动",
        "description": "小红书限制直接私信引导",
    },
    {
        "platform": "xiaohongshu",
        "rule_category": "引流禁止",
        "keyword_or_pattern": r"[0-9]{11}",
        "risk_level": "high",
        "suggestion": "移除手机号，使用平台私信",
        "description": "禁止留手机号",
    },
    {
        "platform": "xiaohongshu",
        "rule_category": "引流禁止",
        "keyword_or_pattern": r"vx|VX|微信",
        "risk_level": "medium",
        "suggestion": "避免直接提及微信",
        "description": "避免提及微信",
    },
]

PLATFORM_RULES_DOUYIN = [
    {
        "platform": "douyin",
        "rule_category": "引流禁止",
        "keyword_or_pattern": r"加微信",
        "risk_level": "high",
        "suggestion": "使用抖音私信功能",
        "description": "抖音禁止引导加微信",
    },
    {
        "platform": "douyin",
        "rule_category": "引流禁止",
        "keyword_or_pattern": r"站外",
        "risk_level": "medium",
        "suggestion": "避免引导到站外",
        "description": "禁止引导到站外",
    },
    {
        "platform": "douyin",
        "rule_category": "金额承诺",
        "keyword_or_pattern": r"\d+万",
        "risk_level": "medium",
        "suggestion": "避免直接提及具体金额",
        "description": "抖音限制直接提及借贷金额",
    },
]

PLATFORM_RULES_ZHIHU = [
    {
        "platform": "zhihu",
        "rule_category": "营销风格",
        "keyword_or_pattern": r"私信我",
        "risk_level": "medium",
        "suggestion": "提供专业回答引导关注",
        "description": "知乎限制软文营销式表达",
    },
    {
        "platform": "zhihu",
        "rule_category": "营销风格",
        "keyword_or_pattern": r"点击链接",
        "risk_level": "medium",
        "suggestion": "避免直接引导点击",
        "description": "知乎限制直接引导点击",
    },
]

ALL_PLATFORM_RULES = PLATFORM_RULES_XIAOHONGSHU + PLATFORM_RULES_DOUYIN + PLATFORM_RULES_ZHIHU


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    """检查表是否存在"""
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    """升级：插入助贷合规规则种子数据（幂等）"""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    now = datetime.utcnow()

    # 1. 插入 mvp_compliance_rules
    if _table_exists(inspector, "mvp_compliance_rules"):
        existing_keywords = set()
        result = bind.execute(sa.text("SELECT keyword FROM mvp_compliance_rules"))
        for row in result:
            existing_keywords.add(row[0])

        rules_table = sa.table(
            "mvp_compliance_rules",
            sa.column("rule_type", sa.String),
            sa.column("keyword", sa.String),
            sa.column("risk_level", sa.String),
            sa.column("suggestion", sa.Text),
        )

        rules_to_insert = []
        for rule in ALL_COMPLIANCE_RULES:
            if rule["keyword"] not in existing_keywords:
                rules_to_insert.append(
                    {
                        "rule_type": rule["rule_type"],
                        "keyword": rule["keyword"],
                        "risk_level": rule["risk_level"],
                        "suggestion": rule["suggestion"],
                    }
                )

        if rules_to_insert:
            op.bulk_insert(rules_table, rules_to_insert)
            print(f"[mvp_compliance_rules] Inserted {len(rules_to_insert)} rules")

    # 2. 插入 auto_rewrite_templates
    if _table_exists(inspector, "auto_rewrite_templates"):
        existing_triggers = set()
        result = bind.execute(sa.text("SELECT trigger_pattern FROM auto_rewrite_templates"))
        for row in result:
            existing_triggers.add(row[0])

        templates_table = sa.table(
            "auto_rewrite_templates",
            sa.column("trigger_pattern", sa.String),
            sa.column("safe_alternative", sa.Text),
            sa.column("risk_level", sa.String),
            sa.column("category", sa.String),
            sa.column("platform_scope", sa.String),
            sa.column("is_active", sa.Boolean),
            sa.column("created_at", sa.DateTime),
        )

        templates_to_insert = []
        for tmpl in AUTO_REWRITE_TEMPLATES:
            if tmpl["trigger_pattern"] not in existing_triggers:
                templates_to_insert.append(
                    {
                        "trigger_pattern": tmpl["trigger_pattern"],
                        "safe_alternative": tmpl["safe_alternative"],
                        "risk_level": tmpl["risk_level"],
                        "category": tmpl.get("category"),
                        "platform_scope": tmpl.get("platform_scope"),
                        "is_active": True,
                        "created_at": now,
                    }
                )

        if templates_to_insert:
            op.bulk_insert(templates_table, templates_to_insert)
            print(f"[auto_rewrite_templates] Inserted {len(templates_to_insert)} templates")

    # 3. 插入 platform_compliance_rules
    if _table_exists(inspector, "platform_compliance_rules"):
        existing_rules = set()
        result = bind.execute(sa.text("SELECT platform, keyword_or_pattern FROM platform_compliance_rules"))
        for row in result:
            existing_rules.add((row[0], row[1]))

        platform_rules_table = sa.table(
            "platform_compliance_rules",
            sa.column("platform", sa.String),
            sa.column("rule_category", sa.String),
            sa.column("keyword_or_pattern", sa.String),
            sa.column("risk_level", sa.String),
            sa.column("suggestion", sa.Text),
            sa.column("description", sa.Text),
            sa.column("is_active", sa.Boolean),
            sa.column("created_at", sa.DateTime),
        )

        platform_rules_to_insert = []
        for rule in ALL_PLATFORM_RULES:
            key = (rule["platform"], rule["keyword_or_pattern"])
            if key not in existing_rules:
                platform_rules_to_insert.append(
                    {
                        "platform": rule["platform"],
                        "rule_category": rule["rule_category"],
                        "keyword_or_pattern": rule["keyword_or_pattern"],
                        "risk_level": rule["risk_level"],
                        "suggestion": rule["suggestion"],
                        "description": rule.get("description"),
                        "is_active": True,
                        "created_at": now,
                    }
                )

        if platform_rules_to_insert:
            op.bulk_insert(platform_rules_table, platform_rules_to_insert)
            print(f"[platform_compliance_rules] Inserted {len(platform_rules_to_insert)} rules")


def downgrade() -> None:
    """回滚：删除本次迁移添加的种子数据"""
    bind = op.get_bind()

    # 删除 mvp_compliance_rules
    keywords = [rule["keyword"] for rule in ALL_COMPLIANCE_RULES]
    if keywords:
        placeholders = ",".join([f"'{kw}'" for kw in keywords])
        bind.execute(sa.text(f"DELETE FROM mvp_compliance_rules WHERE keyword IN ({placeholders})"))

    # 删除 auto_rewrite_templates
    triggers = [tmpl["trigger_pattern"] for tmpl in AUTO_REWRITE_TEMPLATES]
    if triggers:
        placeholders = ",".join([f"'{t}'" for t in triggers])
        bind.execute(sa.text(f"DELETE FROM auto_rewrite_templates WHERE trigger_pattern IN ({placeholders})"))

    # 删除 platform_compliance_rules
    for rule in ALL_PLATFORM_RULES:
        bind.execute(
            sa.text(
                f"DELETE FROM platform_compliance_rules "
                f"WHERE platform = '{rule['platform']}' "
                f"AND keyword_or_pattern = '{rule['keyword_or_pattern']}'"
            )
        )
