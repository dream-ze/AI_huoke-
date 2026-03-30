"""MVP 素材库服务"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.models.models import MvpMaterialItem, MvpTag, MvpMaterialTagRel, MvpKnowledgeItem, MvpGenerationResult


class MvpMaterialService:
    def __init__(self, db: Session):
        self.db = db

    def list_materials(self, page=1, size=20, platform=None, tag_id=None,
                       audience=None, style=None, is_hot=None, keyword=None):
        """列出素材列表，支持筛选和分页"""
        try:
            q = self.db.query(MvpMaterialItem).options(joinedload(MvpMaterialItem.tags))
            if platform:
                q = q.filter(MvpMaterialItem.platform == platform)
            if is_hot is not None:
                q = q.filter(MvpMaterialItem.is_hot == is_hot)
            if keyword:
                q = q.filter(or_(
                    MvpMaterialItem.title.ilike(f"%{keyword}%"),
                    MvpMaterialItem.content.ilike(f"%{keyword}%")
                ))
            if tag_id:
                q = q.join(MvpMaterialTagRel).filter(MvpMaterialTagRel.tag_id == tag_id)
            if audience:
                q = q.join(MvpMaterialTagRel, MvpMaterialItem.id == MvpMaterialTagRel.material_id)\
                     .join(MvpTag, MvpMaterialTagRel.tag_id == MvpTag.id)\
                     .filter(MvpTag.type == "audience", MvpTag.name == audience)
            if style:
                q = q.join(MvpMaterialTagRel, MvpMaterialItem.id == MvpMaterialTagRel.material_id)\
                     .join(MvpTag, MvpMaterialTagRel.tag_id == MvpTag.id)\
                     .filter(MvpTag.type == "style", MvpTag.name == style)
            
            total = q.count()
            items = q.order_by(MvpMaterialItem.created_at.desc()).offset((page - 1) * size).limit(size).all()
            
            # 为每个item加载tags
            result = []
            for item in items:
                result.append({
                    **{c.name: getattr(item, c.name) for c in item.__table__.columns},
                    "tags": [{"id": t.id, "name": t.name, "type": t.type} for t in item.tags]
                })
            return {"items": result, "total": total, "page": page, "size": size}
        except Exception as e:
            return {"items": [], "total": 0, "page": page, "size": size, "error": str(e)}

    def get_material(self, material_id: int):
        """获取素材详情，包含标签、知识条目和生成历史"""
        try:
            item = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if not item:
                return None
            
            tags = self.db.query(MvpTag).join(MvpMaterialTagRel).filter(
                MvpMaterialTagRel.material_id == item.id
            ).all()
            
            knowledge = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.source_material_id == item.id
            ).all()
            
            generations = self.db.query(MvpGenerationResult).filter(
                MvpGenerationResult.source_material_id == item.id
            ).order_by(MvpGenerationResult.created_at.desc()).all()
            
            return {
                **{c.name: getattr(item, c.name) for c in item.__table__.columns},
                "tags": [{"id": t.id, "name": t.name, "type": t.type} for t in tags],
                "knowledge_items": [{"id": k.id, "title": k.title, "category": k.category} for k in knowledge],
                "generation_history": [
                    {"id": g.id, "output_title": g.output_title, "version": g.version, "created_at": str(g.created_at)} 
                    for g in generations
                ]
            }
        except Exception:
            return None

    def create_material(self, data: dict):
        """创建素材"""
        try:
            material = MvpMaterialItem(
                platform=data.get("platform", "xiaohongshu"),
                title=data.get("title", ""),
                content=data.get("content", ""),
                source_url=data.get("source_url"),
                author=data.get("author"),
                like_count=data.get("like_count", 0),
                comment_count=data.get("comment_count", 0),
                is_hot=data.get("is_hot", False),
                risk_level=data.get("risk_level", "low"),
            )
            self.db.add(material)
            self.db.commit()
            self.db.refresh(material)
            return material
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"创建素材失败: {str(e)}")

    def toggle_hot(self, material_id: int):
        """切换爆款状态"""
        try:
            item = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if not item:
                raise ValueError("素材不存在")
            item.is_hot = not item.is_hot
            self.db.commit()
            return item
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"操作失败: {str(e)}")

    def update_material(self, material_id: int, data: dict):
        """更新素材信息"""
        try:
            item = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if not item:
                raise ValueError("素材不存在")
            
            for key in ["title", "content", "platform", "author", "is_hot", "risk_level"]:
                if key in data:
                    setattr(item, key, data[key])
            
            self.db.commit()
            return item
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"更新失败: {str(e)}")

    def delete_material(self, material_id: int):
        """删除素材"""
        try:
            item = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if not item:
                raise ValueError("素材不存在")
            self.db.delete(item)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"删除失败: {str(e)}")

    def increment_use_count(self, material_id: int):
        """增加使用次数"""
        try:
            item = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if item:
                item.use_count += 1
                self.db.commit()
        except Exception:
            self.db.rollback()
