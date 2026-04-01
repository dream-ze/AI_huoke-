from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import verify_token
from app.models import Customer, Lead, PublishTask, User
from app.schemas import (
    CustomerResponse,
    LeadAssignRequest,
    LeadConvertCustomerRequest,
    LeadCreate,
    LeadResponse,
    LeadStatusUpdate,
    LeadTraceResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

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
    start_date = datetime.utcnow() - timedelta(days=days)

    # 按平台分组统计
    platform_stats = (
        db.query(
            Lead.platform,
            func.count(Lead.id).label("lead_count"),
            func.sum(Lead.valid_leads).label("valid_count"),
            func.sum(Lead.conversions).label("conversion_count"),
        )
        .filter(Lead.owner_id == current_user["user_id"])
        .filter(Lead.created_at >= start_date)
        .group_by(Lead.platform)
        .all()
    )

    by_platform = []
    for row in platform_stats:
        lead_count = row.lead_count or 0
        valid_count = row.valid_count or 0
        conversion_count = row.conversion_count or 0
        conversion_rate = (conversion_count / lead_count) if lead_count > 0 else 0
        by_platform.append(
            {
                "platform": row.platform,
                "lead_count": lead_count,
                "valid_count": valid_count,
                "conversion_count": conversion_count,
                "conversion_rate": round(conversion_rate, 4),
            }
        )

    # 按来源分组统计
    source_stats = (
        db.query(
            Lead.source,
            func.count(Lead.id).label("lead_count"),
            func.sum(Lead.valid_leads).label("valid_count"),
            func.sum(Lead.conversions).label("conversion_count"),
        )
        .filter(Lead.owner_id == current_user["user_id"])
        .filter(Lead.created_at >= start_date)
        .group_by(Lead.source)
        .all()
    )

    by_source = []
    for row in source_stats:
        lead_count = row.lead_count or 0
        valid_count = row.valid_count or 0
        conversion_count = row.conversion_count or 0
        conversion_rate = (conversion_count / lead_count) if lead_count > 0 else 0
        by_source.append(
            {
                "source": row.source,
                "lead_count": lead_count,
                "valid_count": valid_count,
                "conversion_count": conversion_count,
                "conversion_rate": round(conversion_rate, 4),
            }
        )

    # 最佳引流内容 - 关联 PublishTask 获取 task_title
    top_content_query = (
        db.query(
            Lead.title,
            Lead.platform,
            Lead.publish_task_id,
            PublishTask.task_title,
            func.count(Lead.id).label("lead_count"),
            func.sum(Lead.conversions).label("conversions"),
        )
        .outerjoin(PublishTask, Lead.publish_task_id == PublishTask.id)
        .filter(Lead.owner_id == current_user["user_id"])
        .filter(Lead.created_at >= start_date)
        .group_by(Lead.title, Lead.platform, Lead.publish_task_id, PublishTask.task_title)
        .order_by(func.count(Lead.id).desc())
        .limit(10)
        .all()
    )

    top_content = []
    for row in top_content_query:
        top_content.append(
            {
                "title": row.task_title or row.title,
                "platform": row.platform,
                "lead_count": row.lead_count or 0,
                "conversions": row.conversions or 0,
            }
        )

    return {
        "by_platform": by_platform,
        "by_source": by_source,
        "top_content": top_content,
        "period_days": days,
    }


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
    start_date = datetime.utcnow() - timedelta(days=days)

    # published: PublishTask 表的总数（指定时间范围）
    published_count = (
        db.query(func.count(PublishTask.id))
        .filter(PublishTask.owner_id == current_user["user_id"])
        .filter(PublishTask.created_at >= start_date)
        .scalar()
        or 0
    )

    # leads_generated: Lead 表总数
    leads_generated_count = (
        db.query(func.count(Lead.id))
        .filter(Lead.owner_id == current_user["user_id"])
        .filter(Lead.created_at >= start_date)
        .scalar()
        or 0
    )

    # contacted: Lead 表 status 为 contacted 及之后状态的数量
    contacted_statuses = ["contacted", "qualified", "converted"]
    contacted_count = (
        db.query(func.count(Lead.id))
        .filter(Lead.owner_id == current_user["user_id"])
        .filter(Lead.created_at >= start_date)
        .filter(Lead.status.in_(contacted_statuses))
        .scalar()
        or 0
    )

    # qualified: Lead 表 status 为 qualified 及之后状态的数量
    qualified_statuses = ["qualified", "converted"]
    qualified_count = (
        db.query(func.count(Lead.id))
        .filter(Lead.owner_id == current_user["user_id"])
        .filter(Lead.created_at >= start_date)
        .filter(Lead.status.in_(qualified_statuses))
        .scalar()
        or 0
    )

    # converted: Lead 表 status 为 converted 的数量
    converted_count = (
        db.query(func.count(Lead.id))
        .filter(Lead.owner_id == current_user["user_id"])
        .filter(Lead.created_at >= start_date)
        .filter(Lead.status == "converted")
        .scalar()
        or 0
    )

    # 计算转化率（基于 published 作为基准）
    stages = [
        {
            "stage": "published",
            "stage_label": "发布内容",
            "count": published_count,
            "rate": 1.0,
        },
        {
            "stage": "leads_generated",
            "stage_label": "产生线索",
            "count": leads_generated_count,
            "rate": round(leads_generated_count / published_count, 4) if published_count > 0 else 0,
        },
        {
            "stage": "contacted",
            "stage_label": "已联系",
            "count": contacted_count,
            "rate": round(contacted_count / published_count, 4) if published_count > 0 else 0,
        },
        {
            "stage": "qualified",
            "stage_label": "已认定",
            "count": qualified_count,
            "rate": round(qualified_count / published_count, 4) if published_count > 0 else 0,
        },
        {
            "stage": "converted",
            "stage_label": "已转化",
            "count": converted_count,
            "rate": round(converted_count / published_count, 4) if published_count > 0 else 0,
        },
    ]

    return {
        "stages": stages,
        "period_days": days,
    }


# ═══════════ 工具函数与 CRUD 端点 ═══════════


def _lead_to_response(db: Session, lead: Lead, publish_record_id: int | None = None) -> dict:
    customer = db.query(Customer).filter(Customer.lead_id == lead.id).first()
    payload = LeadResponse.model_validate(lead).model_dump()
    payload["customer_id"] = customer.id if customer else None
    if publish_record_id is not None:
        payload["publish_record_id"] = publish_record_id
    return payload


@router.post("/create", response_model=LeadResponse)
def create_lead(
    payload: LeadCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    lead = Lead(owner_id=current_user["user_id"], **payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _lead_to_response(db, lead)


@router.get("/list", response_model=list[LeadResponse])
def list_leads(
    status: str | None = Query(None),
    owner_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    query = db.query(Lead)
    if owner_id is not None and owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="No access to this lead scope")

    query = query.filter(Lead.owner_id == current_user["user_id"])
    if status and status != "all":
        query = query.filter(Lead.status == status)
    leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    if not leads:
        return []

    lead_ids = [item.id for item in leads]
    customer_rows = db.query(Customer.id, Customer.lead_id).filter(Customer.lead_id.in_(lead_ids)).all()
    customer_map = {lead_id: customer_id for customer_id, lead_id in customer_rows if lead_id is not None}

    result = []
    for item in leads:
        payload = LeadResponse.model_validate(item).model_dump()
        payload["customer_id"] = customer_map.get(item.id)
        result.append(payload)
    return result


@router.put("/{lead_id}/status", response_model=LeadResponse)
def update_lead_status(
    lead_id: int,
    payload: LeadStatusUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="No access to this lead")

    setattr(lead, "status", payload.status)
    db.commit()
    db.refresh(lead)
    return _lead_to_response(db, lead)


@router.post("/{lead_id}/assign", response_model=LeadResponse)
def assign_lead_owner(
    lead_id: int,
    payload: LeadAssignRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="No access to this lead")

    new_owner_id = payload.owner_id or current_user["user_id"]
    owner = db.query(User).filter(User.id == new_owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner user not found")

    setattr(lead, "owner_id", int(new_owner_id))
    db.commit()
    db.refresh(lead)
    return _lead_to_response(db, lead)


@router.get("/{lead_id}/trace", response_model=LeadTraceResponse)
def get_lead_trace(
    lead_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="No access to this lead")

    customer = db.query(Customer).filter(Customer.lead_id == lead.id).first()
    publish_record_id = None
    publish_task_id = getattr(lead, "publish_task_id", None)
    if publish_task_id is not None:
        task = db.query(PublishTask).filter(PublishTask.id == publish_task_id).first()
        publish_record_id = task.publish_record_id if task else None

    return _lead_to_response(db, lead, publish_record_id=publish_record_id)


@router.post("/{lead_id}/convert-customer", response_model=CustomerResponse)
def convert_lead_to_customer(
    lead_id: int,
    payload: LeadConvertCustomerRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="No access to this lead")

    existing = db.query(Customer).filter(Customer.lead_id == lead.id).first()
    if existing:
        return existing

    customer = Customer(
        owner_id=lead.owner_id,
        nickname=payload.nickname or f"线索#{lead.id}",
        wechat_id=payload.wechat_id,
        phone=payload.phone,
        source_platform=lead.platform,
        source_content_id=None,
        lead_id=lead.id,
        tags=payload.tags or ["线索转客户"],
        intention_level=payload.intention_level or lead.intention_level,
        inquiry_content=payload.inquiry_content or lead.note,
        customer_status="new",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
