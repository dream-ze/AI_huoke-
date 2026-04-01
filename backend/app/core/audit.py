"""
审计日志模块

提供统一的审计日志记录功能，用于追踪用户操作行为。
"""

import logging
from datetime import datetime
from typing import Optional

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
) -> None:
    """
    记录审计日志

    Args:
        user_id: 执行操作的用户ID
        action: 操作类型 (如 "create", "update", "delete", "export")
        resource: 资源类型 (如 "material", "knowledge", "customer")
        resource_id: 资源ID (可选)
        result: 操作结果 (success/failure)
        detail: 详细信息 (可选)

    Example:
        log_audit(
            user_id=1,
            action="delete",
            resource="material",
            resource_id="123",
            result="success",
            detail="批量删除素材"
        )
    """
    log_message = (
        f"AUDIT | user={user_id} | action={action} | resource={resource} | "
        f"resource_id={resource_id or 'N/A'} | result={result} | "
        f"detail={detail or 'N/A'} | timestamp={datetime.utcnow().isoformat()}"
    )

    if result == "success":
        audit_logger.info(log_message)
    else:
        audit_logger.warning(log_message)


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
