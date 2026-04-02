"""平台规则管理路由模块 - 提供规则的动态 CRUD 管理"""

from typing import Optional

from app.core.audit import log_audit
from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas import (
    PlatformRuleCreate,
    PlatformRuleImportResponse,
    PlatformRuleListResponse,
    PlatformRuleReloadCacheResponse,
    PlatformRuleResponse,
    PlatformRuleUpdate,
)
from app.services.platform_rule_service import PlatformRuleService
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/rules", tags=["Platform Rules"])


@router.post("/platform-rules", response_model=PlatformRuleResponse)
def create_platform_rule(
    data: PlatformRuleCreate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("compliance", "write")),
):
    """
    创建平台合规规则

    需要 compliance:write 权限
    """
    service = PlatformRuleService(db)

    rule = service.create_rule(
        platform=data.platform,
        keyword_or_pattern=data.keyword_or_pattern,
        risk_level=data.risk_level,
        suggestion=data.suggestion,
        rule_category=data.rule_category,
        description=data.description,
    )

    # 记录审计日志
    log_audit(
        user_id=user["user_id"],
        action="create",
        resource="platform_rule",
        resource_id=str(rule.id),
        result="success",
        detail=f"创建平台规则: {data.platform} - {data.keyword_or_pattern}",
        new_value={
            "platform": data.platform,
            "keyword_or_pattern": data.keyword_or_pattern,
            "risk_level": data.risk_level,
            "rule_category": data.rule_category,
        },
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    return rule


@router.get("/platform-rules", response_model=PlatformRuleListResponse)
def list_platform_rules(
    platform: Optional[str] = Query(None, description="平台名称筛选"),
    is_active: Optional[bool] = Query(None, description="是否激活筛选"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("compliance", "read")),
):
    """
    查询平台规则列表

    支持按平台和激活状态筛选，需要 compliance:read 权限
    """
    service = PlatformRuleService(db)
    result = service.list_rules(
        platform=platform,
        is_active=is_active,
        page=page,
        size=size,
    )

    # 序列化响应
    items = []
    for rule in result["items"]:
        items.append(
            PlatformRuleResponse(
                id=rule.id,
                platform=rule.platform,
                keyword_or_pattern=rule.keyword_or_pattern,
                risk_level=rule.risk_level,
                suggestion=rule.suggestion,
                rule_category=rule.rule_category,
                description=rule.description,
                is_active=rule.is_active,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
            )
        )

    return PlatformRuleListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"],
    )


@router.get("/platform-rules/{rule_id}", response_model=PlatformRuleResponse)
def get_platform_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("compliance", "read")),
):
    """
    查询单条平台规则详情

    需要 compliance:read 权限
    """
    service = PlatformRuleService(db)
    rule = service.get_rule_by_id(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    return PlatformRuleResponse(
        id=rule.id,
        platform=rule.platform,
        keyword_or_pattern=rule.keyword_or_pattern,
        risk_level=rule.risk_level,
        suggestion=rule.suggestion,
        rule_category=rule.rule_category,
        description=rule.description,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.put("/platform-rules/{rule_id}", response_model=PlatformRuleResponse)
def update_platform_rule(
    rule_id: int,
    data: PlatformRuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("compliance", "write")),
):
    """
    更新平台规则

    需要 compliance:write 权限
    """
    service = PlatformRuleService(db)

    # 获取原规则用于审计日志
    old_rule = service.get_rule_by_id(rule_id)
    if not old_rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    old_value = {
        "keyword_or_pattern": old_rule.keyword_or_pattern,
        "risk_level": old_rule.risk_level,
        "suggestion": old_rule.suggestion,
        "rule_category": old_rule.rule_category,
        "description": old_rule.description,
        "is_active": old_rule.is_active,
    }

    rule = service.update_rule(
        rule_id=rule_id,
        keyword_or_pattern=data.keyword_or_pattern,
        risk_level=data.risk_level,
        suggestion=data.suggestion,
        rule_category=data.rule_category,
        description=data.description,
        is_active=data.is_active,
    )

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    # 记录审计日志
    new_value = {
        "keyword_or_pattern": rule.keyword_or_pattern,
        "risk_level": rule.risk_level,
        "suggestion": rule.suggestion,
        "rule_category": rule.rule_category,
        "description": rule.description,
        "is_active": rule.is_active,
    }

    log_audit(
        user_id=user["user_id"],
        action="update",
        resource="platform_rule",
        resource_id=str(rule_id),
        result="success",
        detail=f"更新平台规则: {rule.platform} - {rule.keyword_or_pattern}",
        old_value=old_value,
        new_value=new_value,
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    return PlatformRuleResponse(
        id=rule.id,
        platform=rule.platform,
        keyword_or_pattern=rule.keyword_or_pattern,
        risk_level=rule.risk_level,
        suggestion=rule.suggestion,
        rule_category=rule.rule_category,
        description=rule.description,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/platform-rules/{rule_id}")
def delete_platform_rule(
    rule_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("compliance", "write")),
):
    """
    删除平台规则（软删除，设置 is_active=False）

    需要 compliance:write 权限
    """
    service = PlatformRuleService(db)

    # 获取原规则用于审计日志
    old_rule = service.get_rule_by_id(rule_id)
    if not old_rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    rule = service.delete_rule(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    # 记录审计日志
    log_audit(
        user_id=user["user_id"],
        action="delete",
        resource="platform_rule",
        resource_id=str(rule_id),
        result="success",
        detail=f"软删除平台规则: {old_rule.platform} - {old_rule.keyword_or_pattern}",
        old_value={
            "platform": old_rule.platform,
            "keyword_or_pattern": old_rule.keyword_or_pattern,
            "is_active": old_rule.is_active,
        },
        new_value={"is_active": False},
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    return {"message": "规则已删除", "rule_id": rule_id}


@router.post("/platform-rules/import", response_model=PlatformRuleImportResponse)
def import_platform_rules_from_yaml(
    request: Request,
    platform: str = Query(..., description="要导入的平台名称"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("compliance", "write")),
):
    """
    从 YAML 文件批量导入规则到数据库

    跳过已存在的规则（以 keyword_or_pattern 判断），需要 compliance:write 权限
    """
    service = PlatformRuleService(db)
    result = service.import_from_yaml(platform)

    # 记录审计日志
    log_audit(
        user_id=user["user_id"],
        action="import",
        resource="platform_rule",
        result="success" if result["imported_count"] >= 0 else "failure",
        detail=f"YAML导入规则: platform={platform}, imported={result['imported_count']}",
        new_value=result,
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    return PlatformRuleImportResponse(
        platform=platform,
        imported_count=result["imported_count"],
        skipped_count=result["skipped_count"],
        total_count=result["total_count"],
        message=result["message"],
    )


@router.post("/platform-rules/reload-cache", response_model=PlatformRuleReloadCacheResponse)
def reload_platform_rules_cache(
    request: Request,
    platform: Optional[str] = Query(None, description="指定平台，不指定则刷新所有"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("compliance", "write")),
):
    """
    手动刷新规则缓存

    清除缓存并重新加载，需要 compliance:write 权限
    """
    service = PlatformRuleService(db)
    platforms = service.reload_cache(platform)

    # 记录审计日志
    log_audit(
        user_id=user["user_id"],
        action="reload_cache",
        resource="platform_rule",
        result="success",
        detail=f"刷新规则缓存: platforms={platforms}",
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    return PlatformRuleReloadCacheResponse(
        success=True,
        platforms=platforms,
        message=f"缓存已刷新: {', '.join(platforms)}",
    )
