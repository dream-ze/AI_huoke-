"""统一状态机定义 - 智获客 2.0"""

from enum import Enum


class ContentStatus(str, Enum):
    """内容状态流转"""

    COLLECTED = "collected"
    CLEANED = "cleaned"
    CLASSIFIED = "classified"
    KNOWLEDGE_READY = "knowledge_ready"
    GENERATED = "generated"
    COMPLIANCE_PASSED = "compliance_passed"
    COMPLIANCE_REJECTED = "compliance_rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class LeadStatus(str, Enum):
    """线索状态流转"""

    NEW = "new"
    ENGAGED = "engaged"
    QUALIFIED = "qualified"
    HIGH_INTENT = "high_intent"
    MANUAL_TAKEOVER = "manual_takeover"
    CONVERTED = "converted"
    LOST = "lost"


class CustomerStatus(str, Enum):
    """客户状态流转"""

    NEW = "new"
    PENDING_FOLLOW = "pending_follow"
    CONTACTED = "contacted"
    NEGOTIATING = "negotiating"
    DEAL_CLOSED = "deal_closed"
    CHURNED = "churned"


class WorkflowTaskStatus(str, Enum):
    """工作流任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
