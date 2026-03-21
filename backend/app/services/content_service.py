from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models import ContentAsset, User
from app.schemas import ContentAssetCreate, ContentAssetUpdate
from fastapi import HTTPException, status


class ContentService:
    @staticmethod
    def create_content(db: Session, user_id: int, content_data: ContentAssetCreate) -> ContentAsset:
        """Create new content asset"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        content = ContentAsset(
            owner_id=user_id,
            **content_data.model_dump()
        )
        db.add(content)
        db.commit()
        db.refresh(content)
        return content

    @staticmethod
    def get_user_contents(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list:
        """Get user's content assets"""
        return db.query(ContentAsset).filter(
            ContentAsset.owner_id == user_id
        ).order_by(
            desc(ContentAsset.created_at)
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_content(db: Session, user_id: int, content_id: int) -> ContentAsset:
        """Get specific content"""
        content = db.query(ContentAsset).filter(
            (ContentAsset.id == content_id) & (ContentAsset.owner_id == user_id)
        ).first()
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found"
            )
        return content

    @staticmethod
    def update_content(db: Session, user_id: int, content_id: int, content_data: ContentAssetUpdate) -> ContentAsset:
        """Update content asset"""
        content = ContentService.get_content(db, user_id, content_id)
        
        update_data = content_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(content, field, value)
        
        db.commit()
        db.refresh(content)
        return content

    @staticmethod
    def delete_content(db: Session, user_id: int, content_id: int) -> bool:
        """Delete content"""
        content = ContentService.get_content(db, user_id, content_id)
        db.delete(content)
        db.commit()
        return True

    @staticmethod
    def search_by_topic(db: Session, user_id: int, topic: str) -> list:
        """Search content by topic/keyword"""
        return db.query(ContentAsset).filter(
            (ContentAsset.owner_id == user_id) &
            ((ContentAsset.title.ilike(f"%{topic}%")) | (ContentAsset.content.ilike(f"%{topic}%")))
        ).order_by(desc(ContentAsset.created_at)).all()
