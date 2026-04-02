"""
MVP核心模型模块

包含：
- MvpInboxItem: MVP收件箱条目
- MvpMaterialItem: MVP素材库条目
- MvpTag: MVP标签
- MvpMaterialTagRel: MVP素材-标签关联
- MvpKnowledgeItem: MVP知识库条目
- MvpKnowledgeChunk: MVP知识库切块
- MvpPromptTemplate: MVP提示词模板
- MvpGenerationResult: MVP生成结果
- MvpComplianceRule: MVP合规规则
- MvpGenerationFeedback: MVP生成反馈
- MvpKnowledgeQualityScore: MVP知识质量评分
- MvpKnowledgeRelation: MVP知识关系
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# pgvector 向量支持（可选，未安装时降级）
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # pgvector未安装时降级


class MvpInboxItem(Base):
    """MVP收件箱条目 - 采集内容进入的第一站"""

    __tablename__ = "mvp_inbox_items"
    __table_args__ = (Index("idx_inbox_platform_created", "platform", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="xiaohongshu")
    source_id = Column(String(200), nullable=True)  # 平台内容ID
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_preview = Column(Text, nullable=True)  # 内容摘要（前200字）
    author = Column(String(200), nullable=True)
    author_name = Column(String(200), nullable=True)  # 作者（冗余字段，便于查询）
    publish_time = Column(DateTime, nullable=True)  # 发布时间
    source_url = Column(String(1000), nullable=True)
    url = Column(String(500), nullable=True)  # 原始链接（冗余字段）
    source_type = Column(String(50), nullable=False, default="collect")  # collect / manual
    keyword = Column(String(200), nullable=True)
    risk_level = Column(String(20), nullable=False, default="low")  # low / medium / high
    duplicate_status = Column(String(20), nullable=False, default="unique")  # unique / suspected / duplicate
    score = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, default=0.0)  # 质量评分
    risk_score = Column(Float, default=0.0)  # 风险评分
    tech_status = Column(String(30), nullable=False, default="parsed")  # raw / parsed / enriched
    biz_status = Column(String(30), nullable=False, default="pending")  # pending / to_material / discarded
    clean_status = Column(String(20), default="pending")  # pending/cleaned/failed
    quality_status = Column(String(20), default="pending")  # pending/good/normal/low
    risk_status = Column(String(20), default="normal")  # normal/low_risk/high_risk
    material_status = Column(String(20), default="not_in")  # not_in/in_material/ignored
    rewrite_ready = Column(Boolean, default=False)  # 质量达标+风险可控，可进入仿写池
    cleaned_at = Column(DateTime, nullable=True)
    screened_at = Column(DateTime, nullable=True)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MvpMaterialItem(Base):
    """MVP素材库条目 - 经过筛选的优质素材"""

    __tablename__ = "mvp_material_items"
    __table_args__ = (
        Index("idx_material_platform", "platform"),
        Index("idx_material_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String(1000), nullable=True)
    like_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    author = Column(String(200), nullable=True)
    is_hot = Column(Boolean, nullable=False, default=False)
    risk_level = Column(String(20), nullable=False, default="low")
    use_count = Column(Integer, nullable=False, default=0)
    source_inbox_id = Column(Integer, ForeignKey("mvp_inbox_items.id"), nullable=True)
    inbox_item_id = Column(Integer, ForeignKey("mvp_inbox_items.id"), nullable=True)  # 关联收件箱条目
    quality_score = Column(Float, nullable=True)  # 质量评分
    risk_score = Column(Float, nullable=True)  # 风险评分
    rewrite_ready = Column(Boolean, default=False)  # 质量达标+风险可控，可进入仿写池
    tags_json = Column(Text, nullable=True)  # JSON格式标签
    topic = Column(String(100), nullable=True)  # 主题
    persona = Column(String(100), nullable=True)  # 人设/受众画像
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    tags = relationship("MvpTag", secondary="mvp_material_tag_rel", back_populates="materials")
    knowledge_items = relationship("MvpKnowledgeItem", back_populates="source_material")
    generation_results = relationship("MvpGenerationResult", back_populates="source_material")


class MvpTag(Base):
    """MVP标签 - 用于素材分类

    标签维度类型 (type 字段):
    - platform: 平台来源 (xiaohongshu/douyin/zhihu/weixin)
    - audience: 目标受众 (负债人群/上班族/个体户/大学生/宝妈群体/中年人群)
    - style: 内容风格 (避坑型/种草型/专业型/口语型)
    - topic: 主题分类 (车贷/房贷/网贷/信用卡/征信)
    - scenario: 使用场景 (急需用钱/以贷养贷/首次贷款/经营周转/消费分期)
    - content_type: 内容类型 (干货型/故事型/测评型/问答型/清单型)

    助贷业务专用维度:
    - product_type: 产品类型 (信贷/抵押贷/企业贷/经营贷/消费贷)
    - user_qualification: 用户资质 (公积金/社保/个体户/企业主/征信花/负债高)
    - content_intent: 内容意图 (科普/避坑/案例/引流/转化)
    - platform_style: 平台风格 (口播/图文/问答/经验帖)
    - risk_level: 风险等级 (低风险/中风险/高风险)
    - conversion_tendency: 转化倾向 (强转化/弱转化/品牌向)
    """

    __tablename__ = "mvp_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 标签维度，见类文档说明
    created_at = Column(DateTime, server_default=func.now())

    # unique constraint on (name, type)
    __table_args__ = (UniqueConstraint("name", "type", name="uq_mvp_tag_name_type"),)

    materials = relationship("MvpMaterialItem", secondary="mvp_material_tag_rel", back_populates="tags")


class MvpMaterialTagRel(Base):
    """MVP素材-标签关联表"""

    __tablename__ = "mvp_material_tag_rel"

    material_id = Column(Integer, ForeignKey("mvp_material_items.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("mvp_tags.id", ondelete="CASCADE"), primary_key=True)


class MvpKnowledgeItem(Base):
    """MVP知识库条目 - 提取的可复用知识"""

    __tablename__ = "mvp_knowledge_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    platform = Column(String(50), nullable=True)
    audience = Column(String(100), nullable=True)
    style = Column(String(100), nullable=True)
    source_material_id = Column(Integer, ForeignKey("mvp_material_items.id"), nullable=True)
    use_count = Column(Integer, nullable=False, default=0)
    embedding = Column(Vector(768), nullable=True) if Vector else Column(Text, nullable=True)  # 向量化字段
    created_at = Column(DateTime, server_default=func.now())

    # 增强字段 - 结构化内容分类
    topic = Column(String(100), nullable=True, comment="内容主题：loan/credit/online_loan/housing_fund")
    content_type = Column(String(50), nullable=True, comment="内容类型：案例/知识/规则/模板")
    opening_type = Column(String(50), nullable=True, comment="开头方式：提问/数据/故事/痛点")
    hook_sentence = Column(Text, nullable=True, comment="爆点句/钩子句")
    cta_style = Column(String(100), nullable=True, comment="转化方式：私信/评论/关注")
    risk_level = Column(String(20), nullable=True, comment="风险等级：low/medium/high")
    summary = Column(Text, nullable=True, comment="内容摘要")

    source_material = relationship("MvpMaterialItem", back_populates="knowledge_items")

    # 分库与层级
    library_type = Column(
        String(50), default="industry_phrases", index=True
    )  # hot_content/industry_phrases/platform_rules/audience_profile/account_positioning/prompt_templates/compliance_rules
    layer = Column(String(30), default="structured")  # raw/structured/rule/generation

    # 原始素材信息
    source_url = Column(String(500), nullable=True)
    author = Column(String(200), nullable=True)

    # 互动数据
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)

    # 增强字段
    emotion_intensity = Column(String(20), nullable=True)  # low/medium/high
    conversion_goal = Column(String(50), nullable=True)  # private_message/consultation/conversion
    is_hot = Column(Boolean, default=False)

    # 索引定义
    __table_args__ = (
        Index("idx_knowledge_platform_audience_topic", "platform", "audience", "topic"),
        Index("idx_knowledge_library_type_created", "library_type", "created_at"),
        Index("idx_knowledge_is_hot_platform", "is_hot", "platform"),
    )


class MvpKnowledgeChunk(Base):
    """MVP知识库切块表 - 支持向量检索"""

    __tablename__ = "mvp_knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_id = Column(Integer, ForeignKey("mvp_knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_type = Column(String(30), nullable=False)  # post/paragraph/rule/template
    chunk_index = Column(Integer, default=0)  # 切块序号
    content = Column(Text, nullable=False)  # 切块内容
    metadata_json = Column(Text, nullable=True)  # JSON格式元数据
    # 向量数据：使用 pgvector Vector 类型 (768维)
    embedding = Column(Vector(768), nullable=True) if Vector else Column(Text, nullable=True)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

    # 关系
    knowledge_item = relationship("MvpKnowledgeItem", backref="chunks")


class MvpPromptTemplate(Base):
    """MVP提示词模板"""

    __tablename__ = "mvp_prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=True)
    audience = Column(String(100), nullable=True)
    style = Column(String(100), nullable=True)
    template = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class MvpGenerationResult(Base):
    """MVP内容生成结果"""

    __tablename__ = "mvp_generation_results"

    id = Column(Integer, primary_key=True, index=True)
    source_material_id = Column(Integer, ForeignKey("mvp_material_items.id"), nullable=True)
    input_text = Column(Text, nullable=False)
    output_title = Column(String(500), nullable=True)
    output_text = Column(Text, nullable=False)
    version = Column(String(50), nullable=False)  # professional / casual / seeding
    platform = Column(String(50), nullable=True)
    audience = Column(String(100), nullable=True)
    style = Column(String(100), nullable=True)
    is_final = Column(Boolean, nullable=False, default=False)
    # 结构化输出字段
    opening_hook = Column(Text, nullable=True, comment="开头钩子")
    cta_section = Column(Text, nullable=True, comment="行动引导段")
    risk_disclaimer = Column(Text, nullable=True, comment="风险点说明")
    alternative_v1 = Column(Text, nullable=True, comment="低风险替代版本")
    alternative_v2 = Column(Text, nullable=True, comment="高转化替代版本")
    output_structure = Column(JSON, nullable=True, comment="完整结构化输出JSON")
    compliance_status = Column(String(30), nullable=True)  # passed / warning / blocked
    created_at = Column(DateTime, server_default=func.now())

    source_material = relationship("MvpMaterialItem", back_populates="generation_results")


class MvpComplianceRule(Base):
    """MVP合规规则"""

    __tablename__ = "mvp_compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String(50), nullable=False)  # keyword / regex / semantic
    keyword = Column(String(200), nullable=False)
    suggestion = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=False, default="medium")  # low / medium / high


class MvpGenerationFeedback(Base):
    """生成结果反馈表 - 收集用户对AI生成内容的反馈"""

    __tablename__ = "mvp_generation_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generation_id = Column(String(100), nullable=False, index=True)  # 生成任务ID
    query = Column(Text, nullable=False)  # 原始查询/请求参数
    generated_text = Column(Text, nullable=False)  # 生成的文本
    feedback_type = Column(String(20), nullable=False, index=True)  # adopted/modified/rejected
    modified_text = Column(Text, nullable=True)  # 用户修改后的文本（如果有）
    rating = Column(Integer, nullable=True)  # 1-5 评分
    feedback_tags = Column(Text, nullable=True)  # JSON: ["太长", "不够专业", "数据错误"]
    knowledge_ids_used = Column(Text, nullable=True)  # JSON: 引用的知识库条目IDs
    created_at = Column(DateTime, default=func.now(), index=True)


class MvpKnowledgeQualityScore(Base):
    """知识库条目质量评分表 - 持续学习机制"""

    __tablename__ = "mvp_knowledge_quality_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(
        Integer, ForeignKey("mvp_knowledge_items.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    reference_count = Column(Integer, default=0)  # 被引用次数
    positive_feedback = Column(Integer, default=0)  # 正面反馈次数
    negative_feedback = Column(Integer, default=0)  # 负面反馈次数
    neutral_feedback = Column(Integer, default=0)  # 中性反馈次数（修改后采纳）
    quality_score = Column(Float, default=0.5)  # 综合质量分 0-1
    weight_boost = Column(Float, default=1.0)  # 检索权重加成 0.5-1.5
    last_referenced_at = Column(DateTime, nullable=True)  # 最后引用时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    knowledge_item = relationship("MvpKnowledgeItem", backref="quality_score")


class MvpKnowledgeRelation(Base):
    """知识条目关系表 - 知识图谱"""

    __tablename__ = "mvp_knowledge_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("mvp_knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("mvp_knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type = Column(
        String(50), nullable=False
    )  # similar_topic, same_audience, same_platform, complementary, derived_from
    weight = Column(Float, default=0.5)  # 关系强度 0-1
    metadata_json = Column(Text, nullable=True)  # 额外元数据 JSON
    created_at = Column(DateTime, default=func.now())

    source = relationship("MvpKnowledgeItem", foreign_keys=[source_id], backref="outgoing_relations")
    target = relationship("MvpKnowledgeItem", foreign_keys=[target_id], backref="incoming_relations")

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation_type", name="uq_knowledge_relation_source_target_type"),
    )


class PlatformComplianceRule(Base):
    """平台合规规则 - 针对特定平台的合规规则"""

    __tablename__ = "platform_compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)  # xiaohongshu/douyin/zhihu/weixin 等
    rule_category = Column(String(100), nullable=True)  # 规则分类：引流禁止/利率承诺/资质承诺等
    keyword_or_pattern = Column(String(500), nullable=False)  # 关键词或正则表达式
    risk_level = Column(String(20), nullable=False, default="medium")  # low/medium/high
    description = Column(Text, nullable=True)  # 规则描述
    suggestion = Column(Text, nullable=True)  # 修改建议
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_platform_compliance_platform", "platform"),
        Index("idx_platform_compliance_active", "is_active"),
    )


class AutoRewriteTemplate(Base):
    """自动改写模板 - 合规改写建议模板"""

    __tablename__ = "auto_rewrite_templates"

    id = Column(Integer, primary_key=True, index=True)
    trigger_pattern = Column(String(500), nullable=False)  # 触发模式（关键词）
    risk_level = Column(String(20), nullable=False, default="medium")  # low/medium/high
    safe_alternative = Column(Text, nullable=False)  # 安全替代文案
    platform_scope = Column(String(200), nullable=True)  # 适用平台（逗号分隔，空表示全平台）
    category = Column(String(100), nullable=True)  # 分类：承诺类/利率类/资质类等
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_auto_rewrite_active", "is_active"),
        Index("idx_auto_rewrite_category", "category"),
    )


__all__ = [
    "MvpInboxItem",
    "MvpMaterialItem",
    "MvpTag",
    "MvpMaterialTagRel",
    "MvpKnowledgeItem",
    "MvpKnowledgeChunk",
    "MvpPromptTemplate",
    "MvpGenerationResult",
    "MvpComplianceRule",
    "MvpGenerationFeedback",
    "MvpKnowledgeQualityScore",
    "MvpKnowledgeRelation",
    "PlatformComplianceRule",
    "AutoRewriteTemplate",
    # Tag Type 常量
    "TAG_TYPE_DIMENSIONS",
    "TAG_TYPE_BASE_DIMENSIONS",
    "TAG_TYPE_LOAN_DIMENSIONS",
]


# ============================================================
# 标签维度常量定义
# ============================================================

# 基础标签维度
TAG_TYPE_BASE_DIMENSIONS = [
    "platform",  # 平台来源
    "audience",  # 目标受众
    "style",  # 内容风格
    "topic",  # 主题分类
    "scenario",  # 使用场景
    "content_type",  # 内容类型
]

# 助贷业务专用标签维度
TAG_TYPE_LOAN_DIMENSIONS = [
    "product_type",  # 产品类型
    "user_qualification",  # 用户资质
    "content_intent",  # 内容意图
    "platform_style",  # 平台风格
    "risk_level",  # 风险等级
    "conversion_tendency",  # 转化倾向
]

# 所有标签维度
TAG_TYPE_DIMENSIONS = TAG_TYPE_BASE_DIMENSIONS + TAG_TYPE_LOAN_DIMENSIONS
