"""
审计日志模块

提供统一的审计日志记录功能，用于追踪用户操作行为。
同时支持日志文件记录和数据库持久化。
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

# 创建专用的审计日志记录器
audit_logger = logging.getLogger("audit")

# 确保审计日志记录器有处理器
if not audit_logger.handlers:
    # 如果没有配置过，添加一个默认的控制台处理器
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)


def log_audit(
    user_id: int,
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    result: str = "success",
    detail: Optional[str] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    ip_address: Optional[str] = None,
    db: Optional[Session] = None,
) -> None:
    """
    记录审计日志（同时写日志文件和数据库）

    Args:
        user_id: 执行操作的用户ID
        action: 操作类型 (如 "create", "update", "delete", "export", "approve", "assign")
        resource: 资源类型 (如 "material", "knowledge", "customer", "content")
        resource_id: 资源ID (可选)
        result: 操作结果 (success/failure)
        detail: 详细信息 (可选)
        old_value: 变更前的值，支持任意类型，会自动序列化为JSON (可选)
        new_value: 变更后的值，支持任意类型，会自动序列化为JSON (可选)
        ip_address: 操作IP地址 (可选)
        db: 数据库会话，如果提供则同时写入数据库 (可选)

    Example:
        log_audit(
            user_id=1,
            action="delete",
            resource="material",
            resource_id="123",
            result="success",
            detail="批量删除素材",
            ip_address="192.168.1.1",
            db=db_session
        )
    """
    # 序列化old_value和new_value为JSON字符串
    old_value_str = None
    new_value_str = None
    try:
        if old_value is not None:
            old_value_str = json.dumps(old_value, ensure_ascii=False, default=str)
        if new_value is not None:
            new_value_str = json.dumps(new_value, ensure_ascii=False, default=str)
    except Exception:
        pass  # 序列化失败时保持为None

    # 写日志文件
    log_message = (
        f"AUDIT | user={user_id} | action={action} | resource={resource} | "
        f"resource_id={resource_id or 'N/A'} | result={result} | "
        f"detail={detail or 'N/A'} | ip={ip_address or 'N/A'} | "
        f"timestamp={datetime.utcnow().isoformat()}"
    )

    if result == "success":
        audit_logger.info(log_message)
    else:
        audit_logger.warning(log_message)

    # 写入数据库（如果提供了db会话）
    if db is not None:
        try:
            from app.models.audit import AuditLog

            audit_record = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=str(resource_id) if resource_id else None,
                old_value=old_value_str,
                new_value=new_value_str,
                detail=detail,
                result=result,
                ip_address=ip_address,
            )
            db.add(audit_record)
            db.commit()
        except Exception as e:
            # 数据库写入失败不影响主流程，只记录错误日志
            audit_logger.error(f"Failed to persist audit log to database: {e}")
            try:
                db.rollback()
            except Exception:
                pass


def log_permission_denied(
    user_id: int, permission: str, resource: Optional[str] = None, resource_id: Optional[str] = None
) -> None:
    """
    记录权限拒绝事件

    Args:
        user_id: 被拒绝的用户ID
        permission: 尝试访问的权限
        resource: 资源类型 (可选)
        resource_id: 资源ID (可选)
    """
    log_message = (
        f"PERMISSION_DENIED | user={user_id} | permission={permission} | "
        f"resource={resource or 'N/A'} | resource_id={resource_id or 'N/A'} | "
        f"timestamp={datetime.utcnow().isoformat()}"
    )
    audit_logger.warning(log_message)


def log_data_access(
    user_id: int, resource: str, action: str, filters: Optional[dict] = None, count: Optional[int] = None
) -> None:
    """
    记录数据访问事件（用于敏感数据查询）

    Args:
        user_id: 访问用户ID
        resource: 资源类型
        action: 操作类型 (如 "list", "export", "search")
        filters: 查询过滤条件 (可选)
        count: 返回的数据条数 (可选)
    """
    filters_str = str(filters) if filters else "N/A"
    log_message = (
        f"DATA_ACCESS | user={user_id} | resource={resource} | action={action} | "
        f"filters={filters_str} | count={count or 'N/A'} | "
        f"timestamp={datetime.utcnow().isoformat()}"
    )
    audit_logger.info(log_message)
