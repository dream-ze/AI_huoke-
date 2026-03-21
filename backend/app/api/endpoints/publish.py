from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.schemas import (
    PublishRecordCreate,
    PublishRecordUpdate,
    PublishRecordResponse
)
from app.services.dashboard_service import DashboardService
from app.models import PublishRecord, RewrittenContent
from fastapi import HTTPException, status

router = APIRouter(prefix="/api/publish", tags=["publish"])


@router.post("/create", response_model=PublishRecordResponse)
def create_publish_record(
    record_data: PublishRecordCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create publish record"""
    # Verify content exists
    rewritten = db.query(RewrittenContent).filter(
        RewrittenContent.id == record_data.rewritten_content_id
    ).first()
    
    if not rewritten:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rewritten content not found"
        )
    
    publish_record = PublishRecord(**record_data.model_dump())
    db.add(publish_record)
    db.commit()
    db.refresh(publish_record)
    return publish_record


@router.get("/list")
def list_publish_records(
    platform: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """List publish records"""
    query = db.query(PublishRecord)
    
    if platform:
        query = query.filter(PublishRecord.platform == platform)
    
    records = query.order_by(PublishRecord.publish_time.desc())\
        .offset(skip).limit(limit).all()
    return records


@router.get("/{record_id}", response_model=PublishRecordResponse)
def get_publish_record(
    record_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get specific publish record"""
    record = db.query(PublishRecord).filter(PublishRecord.id == record_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publish record not found"
        )
    
    return record


@router.put("/{record_id}", response_model=PublishRecordResponse)
def update_publish_record(
    record_id: int,
    record_data: PublishRecordUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update publish record metrics"""
    record = db.query(PublishRecord).filter(PublishRecord.id == record_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publish record not found"
        )
    
    update_data = record_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    
    db.commit()
    db.refresh(record)
    return record
