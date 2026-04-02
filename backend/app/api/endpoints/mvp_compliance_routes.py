"""MVP合规审核路由模块"""

from typing import Optional

from app.core.database import get_db
from app.core.permissions import require_roles
from app.schemas.mvp_schemas import (
    ComplianceCheckRequest,
    ComplianceRuleRequest,
    ComplianceTestRequest,
    FourLayerCheckRequest,
)
from app.services.mvp_compliance_service import MvpComplianceService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/compliance/check")
def compliance_check(req: ComplianceCheckRequest, db: Session = Depends(get_db)):
    """合规检查"""
    svc = MvpComplianceService(db)
    return svc.check(req.text)


@router.get("/compliance/rules")
def list_compliance_rules(
    rule_type: str = "", risk_level: str = "", page: int = 1, size: int = 20, db: Session = Depends(get_db)
):
    """规则列表"""
    from app.models.models import MvpComplianceRule

    query = db.query(MvpComplianceRule)
    if rule_type:
        query = query.filter(MvpComplianceRule.rule_type == rule_type)
    if risk_level:
        query = query.filter(MvpComplianceRule.risk_level == risk_level)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {
        "items": [
            {
                "id": r.id,
                "rule_type": r.rule_type,
                "keyword": r.keyword,
                "pattern": getattr(r, "pattern", None),
                "risk_level": r.risk_level,
                "description": getattr(r, "description", None),
                "suggestion": getattr(r, "suggestion", None),
                "is_active": getattr(r, "is_active", True),
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.post("/compliance/rules")
def create_compliance_rule(
    req: ComplianceRuleRequest, db: Session = Depends(get_db), _user=Depends(require_roles("admin"))
):
    """创建规则 - 仅管理员"""
    from app.models.models import MvpComplianceRule

    rule = MvpComplianceRule(
        rule_type=req.rule_type,
        keyword=req.keyword,
        risk_level=req.risk_level,
    )
    # 如果模型有额外字段则设置
    if hasattr(rule, "pattern") and req.pattern:
        rule.pattern = req.pattern
    if hasattr(rule, "description") and req.description:
        rule.description = req.description
    if hasattr(rule, "suggestion") and req.suggestion:
        rule.suggestion = req.suggestion
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"success": True, "id": rule.id}


@router.put("/compliance/rules/{rule_id}")
def update_compliance_rule(
    rule_id: int, req: ComplianceRuleRequest, db: Session = Depends(get_db), _user=Depends(require_roles("admin"))
):
    """更新规则 - 仅管理员"""
    from app.models.models import MvpComplianceRule

    rule = db.query(MvpComplianceRule).filter(MvpComplianceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    rule.rule_type = req.rule_type
    rule.keyword = req.keyword
    rule.risk_level = req.risk_level
    if hasattr(rule, "pattern"):
        rule.pattern = req.pattern
    if hasattr(rule, "description"):
        rule.description = req.description
    if hasattr(rule, "suggestion"):
        rule.suggestion = req.suggestion
    db.commit()
    return {"success": True, "id": rule.id}


@router.delete("/compliance/rules/{rule_id}")
def delete_compliance_rule(rule_id: int, db: Session = Depends(get_db), _user=Depends(require_roles("admin"))):
    """删除规则 - 仅管理员"""
    from app.models.models import MvpComplianceRule

    rule = db.query(MvpComplianceRule).filter(MvpComplianceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    db.delete(rule)
    db.commit()
    return {"success": True}


@router.post("/compliance/test")
def test_compliance_rule(req: ComplianceTestRequest, db: Session = Depends(get_db)):
    """输入文本，用所有规则检测风险"""
    svc = MvpComplianceService(db)
    result = svc.check(req.text)
    return result


@router.post("/compliance/four-layer-check")
def four_layer_compliance_check(req: FourLayerCheckRequest, db: Session = Depends(get_db)):
    """
    四层合规检测 - 返回详细的分层检测结果

    四层检测体系：
    - 第一层：硬规则拦截（助贷专用敏感词）
    - 第二层：语义风险识别（暗示性违规表达）
    - 第三层：平台规则映射（平台特定规则）
    - 第四层：自动降风险改写建议

    红黄绿灯分级：
    - 红灯 (red): 命中硬规则或高风险语义 → 禁止发
    - 黄灯 (yellow): 中等风险表达或平台规则 → 建议改
    - 绿灯 (green): 无风险或低风险 → 可发
    """
    svc = MvpComplianceService(db)
    result = svc.four_layer_check(req.text, platform=req.platform)
    return result


@router.get("/compliance/traffic-light")
def get_traffic_light_analysis(
    text: str = Query(..., min_length=1, max_length=10000, description="待检测文本"),
    platform: Optional[str] = Query(None, description="平台名称"),
    db: Session = Depends(get_db),
):
    """
    快速获取红黄绿灯分级 - 适用于前端实时检测
    """
    svc = MvpComplianceService(db)
    result = svc.four_layer_check(text, platform=platform)
    return {
        "traffic_light": result["traffic_light"],
        "overall_risk_score": result["overall_risk_score"],
        "is_compliant": result["is_compliant"],
        "hit_count": {
            "layer1": result["layer_results"]["layer1_hard_rules"]["hit_count"],
            "layer2": result["layer_results"]["layer2_semantic_risks"]["hit_count"],
            "layer3": result["layer_results"]["layer3_platform_rules"]["hit_count"],
        },
        "rewrite_suggestions": result["rewrite_suggestions"][:5],  # 最多返回5条建议
    }
