from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.schemas import ContentAssetCreate, ContentAssetUpdate, ContentAssetResponse
from app.services import ContentService

router = APIRouter(prefix="/api/content", tags=["content"])


@router.post("/create", response_model=ContentAssetResponse)
def create_content(
    content_data: ContentAssetCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create new content asset"""
    content = ContentService.create_content(db, current_user["user_id"], content_data)
    return content


@router.get("/list")
def list_content(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """List user's content assets"""
    contents = ContentService.get_user_contents(db, current_user["user_id"], skip, limit)
    return contents


@router.get("/{content_id}", response_model=ContentAssetResponse)
def get_content(
    content_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get specific content"""
    content = ContentService.get_content(db, current_user["user_id"], content_id)
    return content


@router.put("/{content_id}", response_model=ContentAssetResponse)
def update_content(
    content_id: int,
    content_data: ContentAssetUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update content"""
    content = ContentService.update_content(db, current_user["user_id"], content_id, content_data)
    return content


@router.delete("/{content_id}")
def delete_content(
    content_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Delete content"""
    ContentService.delete_content(db, current_user["user_id"], content_id)
    return {"message": "Content deleted successfully"}


@router.get("/search/topic")
def search_by_topic(
    topic: str = Query(..., min_length=1),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Search content by topic"""
    results = ContentService.search_by_topic(db, current_user["user_id"], topic)
    return results
