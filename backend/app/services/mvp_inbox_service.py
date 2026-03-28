"""MVP 收件箱服务"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import MvpInboxItem, MvpMaterialItem, MvpTag, MvpMaterialTagRel


class MvpInboxService:
    def __init__(self, db: Session):
        self.db = db

    def list_inbox(self, page=1, size=20, status=None, platform=None, 
                   source_type=None, risk_level=None, duplicate_status=None, keyword=None):
        """列表+筛选+分页"""
        try:
            q = self.db.query(MvpInboxItem)
            if status:
                q = q.filter(MvpInboxItem.biz_status == status)
            if platform:
                q = q.filter(MvpInboxItem.platform == platform)
            if source_type:
                q = q.filter(MvpInboxItem.source_type == source_type)
            if risk_level:
                q = q.filter(MvpInboxItem.risk_level == risk_level)
            if duplicate_status:
                q = q.filter(MvpInboxItem.duplicate_status == duplicate_status)
            if keyword:
                q = q.filter(or_(
                    MvpInboxItem.title.ilike(f"%{keyword}%"),
                    MvpInboxItem.content.ilike(f"%{keyword}%"),
                    MvpInboxItem.keyword.ilike(f"%{keyword}%")
                ))
            total = q.count()
            items = q.order_by(MvpInboxItem.created_at.desc()).offset((page - 1) * size).limit(size).all()
            return {"items": items, "total": total, "page": page, "size": size}
        except Exception as e:
            return {"items": [], "total": 0, "page": page, "size": size, "error": str(e)}

    def get_item(self, item_id: int):
        """获取单条收件箱条目"""
        try:
            return self.db.query(MvpInboxItem).filter(MvpInboxItem.id == item_id).first()
        except Exception:
            return None

    def to_material(self, item_id: int):
        """入素材库：创建MvpMaterialItem + 自动标签识别"""
        item = self.get_item(item_id)
        if not item:
            raise ValueError("收件箱条目不存在")
        if item.biz_status == "to_material":
            raise ValueError("已入素材库")
        
        try:
            # 创建素材
            material = MvpMaterialItem(
                platform=item.platform,
                title=item.title,
                content=item.content,
                source_url=item.source_url,
                author=item.author,
                risk_level=item.risk_level,
                source_inbox_id=item.id
            )
            self.db.add(material)
            self.db.flush()  # 获取ID
            
            # 自动标签识别
            from app.services.mvp_tag_service import MvpTagService
            tag_svc = MvpTagService(self.db)
            tag_svc.auto_tag_material(material.id, item.content)
            
            # 更新收件箱状态
            item.biz_status = "to_material"
            self.db.commit()
            return material
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"入素材库失败: {str(e)}")

    def mark_hot(self, item_id: int):
        """标记爆款"""
        item = self.get_item(item_id)
        if not item:
            raise ValueError("收件箱条目不存在")
        try:
            item.score = max(item.score, 80.0)  # 标记爆款提升分数
            self.db.commit()
            return item
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"标记失败: {str(e)}")

    def discard(self, item_id: int):
        """丢弃"""
        item = self.get_item(item_id)
        if not item:
            raise ValueError("收件箱条目不存在")
        try:
            item.biz_status = "discarded"
            self.db.commit()
            return item
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"丢弃失败: {str(e)}")

    def create_item(self, data: dict):
        """手动创建收件箱条目"""
        try:
            item = MvpInboxItem(
                platform=data.get("platform", "xiaohongshu"),
                title=data.get("title", ""),
                content=data.get("content", ""),
                author=data.get("author"),
                source_url=data.get("source_url"),
                source_type=data.get("source_type", "manual"),
                keyword=data.get("keyword"),
            )
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"创建失败: {str(e)}")

    def batch_to_material(self, item_ids: list):
        """批量入素材库"""
        results = {"success": [], "failed": []}
        for item_id in item_ids:
            try:
                material = self.to_material(item_id)
                results["success"].append({"item_id": item_id, "material_id": material.id})
            except Exception as e:
                results["failed"].append({"item_id": item_id, "error": str(e)})
        return results
