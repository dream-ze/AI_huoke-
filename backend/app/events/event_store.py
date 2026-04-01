"""基于数据库的轻量事件记录 - 节点状态变化记录"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """事件类型"""

    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_CANCELLED = "workflow.cancelled"

    SKILL_STARTED = "skill.started"
    SKILL_COMPLETED = "skill.completed"
    SKILL_FAILED = "skill.failed"
    SKILL_RETRYING = "skill.retrying"

    CONTENT_STATUS_CHANGED = "content.status_changed"
    LEAD_STATUS_CHANGED = "lead.status_changed"
    CUSTOMER_STATUS_CHANGED = "customer.status_changed"

    REMINDER_SENT = "reminder.sent"
    REMINDER_FAILED = "reminder.failed"


class EventStore:
    """
    事件存储服务。

    轻量实现：直接写入 skill_executions 表或独立的事件日志，
    不引入额外消息中间件（如 RabbitMQ/Kafka）。
    """

    def __init__(self, db: Session):
        self.db = db

    def emit(
        self,
        event_type: EventType,
        entity_type: str,
        entity_id: int,
        data: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        记录一个事件。

        Args:
            event_type: 事件类型
            entity_type: 实体类型（workflow_task / skill_execution / content / lead / customer）
            entity_id: 实体ID
            data: 事件附加数据
            trace_id: 链路追踪ID
            user_id: 触发用户ID

        Returns:
            事件记录字典
        """
        event = {
            "event_type": event_type.value,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "data": data or {},
            "trace_id": trace_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Event: {event_type.value} | " f"{entity_type}#{entity_id} | " f"trace={trace_id}")

        # 将事件记录到数据库（通过 SkillExecution 表的 output_snapshot 字段
        # 或者直接记录日志，后续可扩展为独立事件表）
        try:
            from app.models.models import SkillExecution

            if entity_type == "skill_execution" and entity_id:
                # 更新已有的 skill_execution 记录
                execution = self.db.query(SkillExecution).filter(SkillExecution.id == entity_id).first()
                if execution:
                    existing = execution.output_snapshot or {}
                    events = existing.get("events", [])
                    events.append(event)
                    existing["events"] = events
                    execution.output_snapshot = existing
                    self.db.flush()
        except Exception as e:
            logger.warning(f"Failed to persist event to DB: {e}")

        return event

    def emit_workflow_event(
        self,
        workflow_task_id: int,
        event_type: EventType,
        trace_id: str,
        user_id: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """记录工作流级别事件"""
        return self.emit(
            event_type=event_type,
            entity_type="workflow_task",
            entity_id=workflow_task_id,
            data=data,
            trace_id=trace_id,
            user_id=user_id,
        )

    def emit_skill_event(
        self,
        skill_execution_id: int,
        event_type: EventType,
        trace_id: str,
        skill_name: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """记录 Skill 级别事件"""
        event_data = {"skill_name": skill_name}
        if data:
            event_data.update(data)

        return self.emit(
            event_type=event_type,
            entity_type="skill_execution",
            entity_id=skill_execution_id,
            data=event_data,
            trace_id=trace_id,
        )

    def emit_status_change(
        self,
        entity_type: str,
        entity_id: int,
        old_status: str,
        new_status: str,
        trace_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """记录状态变化事件"""
        event_type_map = {
            "content": EventType.CONTENT_STATUS_CHANGED,
            "lead": EventType.LEAD_STATUS_CHANGED,
            "customer": EventType.CUSTOMER_STATUS_CHANGED,
        }

        event_type = event_type_map.get(entity_type)
        if not event_type:
            logger.warning(f"Unknown entity type for status change: {entity_type}")
            return {}

        return self.emit(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            data={"old_status": old_status, "new_status": new_status},
            trace_id=trace_id,
            user_id=user_id,
        )

    def get_events(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """查询实体的事件历史（基于日志，后续可扩展为DB查询）"""
        # 当前版本通过 SkillExecution.output_snapshot 中的 events 字段查询
        # 后续可扩展为独立事件表
        try:
            from app.models.models import SkillExecution

            if entity_type == "skill_execution":
                execution = self.db.query(SkillExecution).filter(SkillExecution.id == entity_id).first()
                if execution and execution.output_snapshot:
                    return execution.output_snapshot.get("events", [])[:limit]
        except Exception as e:
            logger.warning(f"Failed to query events: {e}")

        return []
