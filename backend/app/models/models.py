"""
兼容层 - 所有模型已拆分到独立文件

保留此文件以兼容现有的 from app.models.models import X

所有模型已按功能域拆分为以下模块：
- base.py: Base, TimestampMixin
- enums.py: PlatformType, ContentType, RiskLevel, IntentionLevel, CustomerStatus
- user.py: User
- content.py: ContentAsset, ContentBlock, ContentComment, ContentSnapshot, ContentInsight, RewrittenContent
- crm.py: Lead, Customer, LeadProfile
- publish.py: PublishRecord, PublishTask, PublishTaskFeedback
- collect.py: BrowserPluginCollection, InboxItem, CollectTask, EmployeeLinkSubmission, MaterialInbox, SourceContent, NormalizedContent, MaterialItem
- knowledge.py: KnowledgeDocument, KnowledgeChunk, Rule, PromptTemplate
- generation.py: GenerationTask
- mvp.py: MvpInboxItem, MvpMaterialItem, MvpTag, MvpMaterialTagRel, MvpKnowledgeItem, MvpKnowledgeChunk, MvpPromptTemplate, MvpGenerationResult, MvpComplianceRule, MvpGenerationFeedback, MvpKnowledgeQualityScore, MvpKnowledgeRelation
- insight.py: InsightTopic, InsightAuthorProfile, InsightContentItem, InsightCollectTask, ArkCallLog
- social.py: SocialAccount, Conversation, Message
- workflow.py: WorkflowTask, SkillExecution, ReminderConfig, ReminderLog
- topic.py: TopicPlan, TopicIdea, HotTopic, TrafficStrategy

推荐使用新的导入方式：
    from app.models import User, ContentAsset
"""

# 基础
from app.models.base import Base, TimestampMixin

# 采集模型
from app.models.collect import (
    BrowserPluginCollection,
    CollectTask,
    EmployeeLinkSubmission,
    InboxItem,
    MaterialInbox,
    MaterialItem,
    NormalizedContent,
    SourceContent,
)

# 内容资产模型
from app.models.content import (
    ContentAsset,
    ContentBlock,
    ContentComment,
    ContentInsight,
    ContentSnapshot,
    RewrittenContent,
)

# CRM模型
from app.models.crm import Customer, Lead, LeadProfile

# 枚举类型
from app.models.enums import ContentType, CustomerStatus, IntentionLevel, PlatformType, RiskLevel

# 生成任务模型
from app.models.generation import GenerationTask

# Insight分析模型
from app.models.insight import ArkCallLog, InsightAuthorProfile, InsightCollectTask, InsightContentItem, InsightTopic

# 知识库模型
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, PromptTemplate, Rule

# MVP模型
from app.models.mvp import (
    AutoRewriteTemplate,
    MvpComplianceRule,
    MvpGenerationFeedback,
    MvpGenerationResult,
    MvpInboxItem,
    MvpKnowledgeChunk,
    MvpKnowledgeItem,
    MvpKnowledgeQualityScore,
    MvpKnowledgeRelation,
    MvpMaterialItem,
    MvpMaterialTagRel,
    MvpPromptTemplate,
    MvpTag,
    PlatformComplianceRule,
)

# 发布模型
from app.models.publish import PublishRecord, PublishTask, PublishTaskFeedback

# 社交账号模型
from app.models.social import Conversation, Message, SocialAccount

# 选题计划模型
from app.models.topic import HotTopic, TopicIdea, TopicPlan, TrafficStrategy

# 用户模型
from app.models.user import User

# 工作流模型
from app.models.workflow import ReminderConfig, ReminderLog, SkillExecution, WorkflowTask

__all__ = [
    # 基础
    "Base",
    "TimestampMixin",
    # 枚举
    "PlatformType",
    "ContentType",
    "RiskLevel",
    "IntentionLevel",
    "CustomerStatus",
    # 用户
    "User",
    # 内容资产
    "ContentAsset",
    "ContentBlock",
    "ContentComment",
    "ContentSnapshot",
    "ContentInsight",
    "RewrittenContent",
    # CRM
    "Lead",
    "Customer",
    "LeadProfile",
    # 发布
    "PublishRecord",
    "PublishTask",
    "PublishTaskFeedback",
    # 采集
    "BrowserPluginCollection",
    "InboxItem",
    "CollectTask",
    "EmployeeLinkSubmission",
    "MaterialInbox",
    "SourceContent",
    "NormalizedContent",
    "MaterialItem",
    # 知识库
    "KnowledgeDocument",
    "KnowledgeChunk",
    "Rule",
    "PromptTemplate",
    # 生成任务
    "GenerationTask",
    # MVP
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
    # Insight
    "InsightTopic",
    "InsightAuthorProfile",
    "InsightContentItem",
    "InsightCollectTask",
    "ArkCallLog",
    # 社交
    "SocialAccount",
    "Conversation",
    "Message",
    # 工作流
    "WorkflowTask",
    "SkillExecution",
    "ReminderConfig",
    "ReminderLog",
    # 选题
    "TopicPlan",
    "TopicIdea",
    "HotTopic",
    "TrafficStrategy",
]
