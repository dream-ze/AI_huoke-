"""
线索管理 API 端点

职责：
- 请求参数校验
- 调用 LeadService 方法
- 返回响应
"""

import logging
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import verify_token
from app.models import Customer, Lead, PublishedContent, PublishTask, User
from app.models.crm import LeadProfile
from app.schemas import (
    AttributionChainResponse,
    CustomerResponse,
    LeadAssignRequest,
    LeadBatchImportRequest,
    LeadBatchImportResponse,
    LeadConvertCustomerRequest,
    LeadCreate,
    LeadFromPublishRequest,
    LeadResponse,
    LeadStatusUpdate,
    LeadTraceResponse,
)
from app.services.attribution_service import AttributionService
from app.services.lead_service import LeadService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lead", tags=["lead"])


# ═══════════ 统计端点（必须在 /{lead_id} 路由之前）═══════════


@router.get("/stats/attribution")
def get_lead_attribution(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    线索来源归因分析
    分析哪个平台/哪条内容带来最多线索
    """
    service = LeadService(db)
    return service.get_attribution_stats(db, current_user["user_id"], days)


@router.get("/stats/funnel")
def get_lead_funnel(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    转化漏斗统计
    返回各阶段数量与转化率
    """
    service = LeadService(db)
    return service.get_lead_funnel_stats(db, current_user["user_id"], days)


@router.get("/stats/by-grade/{grade}")
def get_leads_by_grade(
    grade: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    按分级查询线索
    grade: A/B/C/D
    """
    service = LeadService(db)
    return service.get_leads_by_grade(db, current_user["user_id"], grade, skip, limit)


# ═══════════ CRUD 端点 ═══════════


@router.post("/create", response_model=LeadResponse)
def create_lead(
    payload: LeadCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """创建线索，自动触发评分和分级"""
    service = LeadService(db)
    return service.create_lead(db, payload, current_user["user_id"])


@router.get("/list", response_model=list[LeadResponse])
def list_leads(
    status: str | None = Query(None),
    owner_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """查询线索列表"""
    # 权限校验
    if owner_id is not None and owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="No access to this lead scope")

    service = LeadService(db)
    return service.list_leads(db, current_user["user_id"], status, skip, limit)


@router.put("/{lead_id}/status", response_model=LeadResponse)
def update_lead_status(
    lead_id: int,
    payload: LeadStatusUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """更新线索状态"""
    service = LeadService(db)
    return service.update_status(db, lead_id, payload.status, current_user["user_id"])


@router.post("/{lead_id}/assign", response_model=LeadResponse)
def assign_lead_owner(
    lead_id: int,
    payload: LeadAssignRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """分派线索给销售"""
    service = LeadService(db)
    new_owner_id = payload.owner_id or current_user["user_id"]
    return service.assign_lead(db, lead_id, new_owner_id, current_user["user_id"])


@router.get("/{lead_id}/trace", response_model=LeadTraceResponse)
def get_lead_trace(
    lead_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获取线索追溯信息"""
    service = LeadService(db)
    return service.get_lead_trace(db, lead_id, current_user["user_id"])


@router.post("/{lead_id}/convert-customer", response_model=CustomerResponse)
def convert_lead_to_customer(
    lead_id: int,
    payload: LeadConvertCustomerRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """线索转客户"""
    service = LeadService(db)
    return service.convert_to_customer(db, lead_id, payload, current_user["user_id"])


@router.post("/{lead_id}/rescore")
def rescore_lead(
    lead_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """手动触发线索重新评分"""
    service = LeadService(db)
    # 权限校验
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="No access to this lead")

    return service.auto_score(db, lead_id)


@router.post("/batch-import")
def batch_import_leads(
    leads_data: list[LeadCreate],
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """批量导入线索"""
    service = LeadService(db)
    return service.batch_import_leads(db, leads_data, current_user["user_id"])


# ═══════════ 线索入口与自动归因端点 ═══════════


@router.post("/from-publish")
def create_lead_from_publish(
    payload: LeadFromPublishRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    从发布内容创建线索（线索回流入口）

    自动逻辑：
    - 通过 published_content_id 反查 campaign_id、publish_account_id、generation_result_id
    - 创建线索
    - 自动创建归因记录
    - 自动进行 ABCD 分级
    """
    try:
        # 1. 查询发布内容获取归因信息
        published_content = (
            db.query(PublishedContent).filter(PublishedContent.id == payload.published_content_id).first()
        )

        if not published_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Published content {payload.published_content_id} not found",
            )

        # 2. 创建线索
        lead_data = LeadCreate(
            platform=payload.platform,
            title=f"来自{published_content.title or '发布内容'}的线索",
            source="published_content",
            post_url=published_content.post_url,
            wechat_adds=1 if payload.channel == "加微" else 0,
            leads=1,
            valid_leads=1,
            status="new",
            intention_level="medium",
            note=payload.notes,
        )

        lead_service = LeadService(db)
        lead_response = lead_service.create_lead(db, lead_data, current_user["user_id"])
        lead_id = lead_response["id"]

        # 3. 更新线索的归因字段
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            lead.campaign_id = published_content.campaign_id
            lead.publish_account_id = published_content.publish_account_id
            lead.published_content_id = payload.published_content_id
            lead.generation_task_id = published_content.generation_result_id
            lead.attribution_chain = {
                "platform": payload.platform,
                "account_id": published_content.publish_account_id,
                "content_id": payload.published_content_id,
                "campaign_id": published_content.campaign_id,
                "channel": payload.channel,
                "audience_tags": payload.audience_tags,
            }
            db.flush()

        # 4. 创建线索画像（包含联系信息）
        profile_data = {
            "lead_id": lead_id,
            "extracted_phone": payload.contact_info.get("phone"),
            "extracted_wechat": payload.contact_info.get("wechat"),
        }
        profile = LeadProfile(**profile_data)
        db.add(profile)
        db.flush()

        # 5. 自动创建归因记录
        attribution_data = {
            "platform": payload.platform,
            "account_id": published_content.publish_account_id,
            "content_id": payload.published_content_id,
            "campaign_id": published_content.campaign_id,
            "audience_tags": payload.audience_tags,
            "channel": payload.channel,
            "first_contact_time": datetime.utcnow(),
            "touchpoint_url": published_content.post_url,
            "attribution_type": "last_touch",
        }
        attribution = AttributionService.create_attribution(db, lead_id, attribution_data)

        # 6. 自动评分分级（create_lead 已调用，这里获取最新结果）
        score_result = lead_service.auto_score(db, lead_id)

        db.commit()

        # 7. 获取归因链信息
        attribution_chain = AttributionService.get_attribution_chain(db, lead_id)

        logger.info(
            f"从发布内容创建线索成功: lead_id={lead_id}, "
            f"published_content_id={payload.published_content_id}, "
            f"grade={score_result['grade']}"
        )

        return {
            "lead": lead_response,
            "attribution": {
                "attribution_id": attribution.id if attribution else None,
                "chain": attribution_chain,
            },
            "scoring": score_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"从发布内容创建线索失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create lead from publish: {str(e)}"
        )


@router.post("/batch-import-v2", response_model=LeadBatchImportResponse)
def batch_import_leads_v2(
    payload: LeadBatchImportRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    批量导入线索（增强版）

    返回详细的导入统计信息
    """
    service = LeadService(db)
    result = service.batch_import_leads(db, payload.leads, current_user["user_id"])

    return LeadBatchImportResponse(
        total=result.get("total", 0),
        success=result.get("success", 0),
        failed=result.get("failed", 0),
        duplicates=result.get("duplicates", 0),
        created_ids=result.get("created_ids", []),
        failed_details=result.get("failed_details", []),
    )


@router.get("/{lead_id}/attribution", response_model=AttributionChainResponse)
def get_lead_attribution_chain(
    lead_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    查看完整归因链

    返回归因链详情：平台→账号→内容→活动→人群→渠道
    """
    # 权限校验
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if lead.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this lead")

    # 获取归因链
    chain = AttributionService.get_attribution_chain(db, lead_id)

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribution chain not found for this lead")

    return AttributionChainResponse(**chain)
