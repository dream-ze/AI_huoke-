from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models import Customer, Lead, PublishTask, User
from app.schemas import (
    LeadAssignRequest,
    LeadConvertCustomerRequest,
    LeadCreate,
    LeadResponse,
    LeadStatusUpdate,
    LeadTraceResponse,
    CustomerResponse,
)

router = APIRouter(prefix="/api/lead", tags=["lead"])


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
    if owner_id is None:
        query = query.filter(Lead.owner_id == current_user["user_id"])
    else:
        query = query.filter(Lead.owner_id == owner_id)
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
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id)
        .filter(or_(Lead.owner_id == current_user["user_id"], Lead.publish_task_id.isnot(None)))
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

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
