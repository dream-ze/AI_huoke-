"""
工作流与提醒模块

包含：
- WorkflowTask: 工作流任务
- SkillExecution: Skill执行记录
- ReminderConfig: 提醒配置
- ReminderLog: 提醒日志
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class WorkflowTask(Base):
    """工作流任务"""

    __tablename__ = "workflow_tasks"

    id = Column(Integer, primary_key=True, index=True)
    workflow_type = Column(String(64), nullable=False)
    current_skill = Column(String(64), nullable=True)
    status = Column(String(32), default="pending")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    trace_id = Column(String(64), nullable=False, index=True)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", backref="workflow_tasks")


class SkillExecution(Base):
    """Skill 执行记录"""

    __tablename__ = "skill_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_task_id = Column(Integer, ForeignKey("workflow_tasks.id"), nullable=False)
    skill_name = Column(String(64), nullable=False)
    status = Column(String(32), default="pending")
    duration_ms = Column(Integer, nullable=True)
    input_snapshot = Column(JSON, nullable=True)
    output_snapshot = Column(JSON, nullable=True)
    error_detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow_task = relationship("WorkflowTask", backref="skill_executions")


class ReminderConfig(Base):
    """提醒配置"""

    __tablename__ = "reminder_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    webhook_url = Column(String(512), nullable=True)
    enabled = Column(Boolean, default=True)
    daily_summary_time = Column(String(8), default="09:00")
    urgent_interval_hours = Column(Integer, default=1)
    new_customer_hours = Column(Integer, default=24)
    high_intent_days = Column(Integer, default=2)
    normal_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="reminder_config")


class ReminderLog(Base):
    """提醒日志"""

    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    reminder_type = Column(String(32), nullable=False)
    channel = Column(String(32), default="wecom")
    status = Column(String(16), default="sent")
    message_preview = Column(Text, nullable=True)
    error_detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="reminder_logs")
    customer = relationship("Customer", backref="reminder_logs")


__all__ = ["WorkflowTask", "SkillExecution", "ReminderConfig", "ReminderLog"]
