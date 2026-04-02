"""
模型包统一导出模块

所有模型按功能域拆分后，通过此模块统一导出，保持向后兼容。

新的推荐导入方式：
    from app.models import User, ContentAsset
    
或者按功能域导入：
    from app.models.user import User
    from app.models.content import ContentAsset
"""

# 归因模型
from app.models.attribution import LeadSourceAttribution

# 审计日志模型
from app.models.audit import AuditLog

# 基础
from app.models.base import Base, TimestampMixin

# 活动模型
from app.models.campaign import Campaign

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

# 跟进记录模型
from app.models.follow_up import FollowUpRecord

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

# 发布账号模型
from app.models.publish_account import PublishAccount

# 发布内容模型
from app.models.published_content import PublishedContent

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
    # 审计日志
    "AuditLog",
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
    # 归因
    "LeadSourceAttribution",
    # 活动
    "Campaign",
    # CRM
    "Lead",
    "Customer",
    "LeadProfile",
    # 跟进记录
    "FollowUpRecord",
    # 发布账号
    "PublishAccount",
    # 发布内容
    "PublishedContent",
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
