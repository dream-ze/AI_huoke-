import logging
from enum import Enum
from typing import Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.models import User
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


# 权限矩阵定义
ROLE_PERMISSIONS = {
    Role.ADMIN: {"*"},  # 全部权限
    Role.OPERATOR: {
        "content:read",
        "content:write",
        "content:delete",
        "material:read",
        "material:write",
        "material:delete",
        "knowledge:read",
        "knowledge:write",
        "lead:read",
        "lead:write",
        "customer:read",
        "customer:write",
        "generation:read",
        "generation:write",
        "publish:read",
        "publish:write",
        "insight:read",
        "compliance:read",
    },
    Role.VIEWER: {
        "content:read",
        "material:read",
        "knowledge:read",
        "lead:read",
        "customer:read",
        "generation:read",
        "publish:read",
        "insight:read",
        "compliance:read",
    },
}


def has_permission(user_role: str, permission: str) -> bool:
    """
    检查用户角色是否具有指定权限

    Args:
        user_role: 用户角色字符串 (admin/operator/viewer)
        permission: 权限标识 (如 "material:delete")

    Returns:
        bool: 是否具有该权限
    """
    try:
        role = Role(user_role.lower()) if user_role else Role.VIEWER
    except ValueError:
        # 未知角色，默认无权限
        logger.warning(f"未知角色: {user_role}")
        return False

    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms


def _get_user_with_role(db: Session, user_id: int) -> dict:
    """
    获取用户信息并返回包含角色的字典

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        dict: {"user_id": int, "role": str}

    Raises:
        HTTPException: 用户不存在时抛出401错误
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    role = (user.role or "operator").lower()
    return {
        "user_id": user.id,
        "role": role,
    }


def require_roles(*allowed_roles: str):
    """
    FastAPI Depends - 要求用户具有指定角色之一

    Args:
        *allowed_roles: 允许的角色列表 (如 "admin", "operator")

    Returns:
        依赖函数，返回用户信息字典

    Example:
        @router.post("/admin/endpoint")
        def admin_only(user = Depends(require_roles("admin"))):
            ...
    """

    def _checker(
        current_user: dict = Depends(verify_token),
        db: Session = Depends(get_db),
    ) -> dict:
        user_info = _get_user_with_role(db, current_user["user_id"])

        if allowed_roles and user_info["role"] not in allowed_roles:
            logger.warning(
                f"权限拒绝: 用户{user_info['user_id']}(角色={user_info['role']})" f"尝试访问需要{allowed_roles}的资源"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

        return user_info

    return _checker


def require_permission(resource: str, action: str):
    """
    FastAPI Depends - 要求用户具有特定资源操作权限

    Args:
        resource: 资源名称 (如 "material", "knowledge")
        action: 操作名称 (如 "read", "write", "delete")

    Returns:
        依赖函数，返回用户信息字典

    Example:
        @router.delete("/materials/{id}")
        def delete_material(
            id: int,
            user = Depends(require_permission("material", "delete"))
        ):
            ...
    """
    permission = f"{resource}:{action}"

    def _checker(
        current_user: dict = Depends(verify_token),
        db: Session = Depends(get_db),
    ) -> dict:
        user_info = _get_user_with_role(db, current_user["user_id"])

        if not has_permission(user_info["role"], permission):
            logger.warning(f"权限拒绝: 用户{user_info['user_id']}(角色={user_info['role']})" f"尝试执行 {permission}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"无权执行操作: {permission}")

        return user_info

    return _checker
