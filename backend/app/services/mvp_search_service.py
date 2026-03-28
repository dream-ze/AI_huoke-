"""MVP 检索服务"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import MvpKnowledgeItem, MvpMaterialItem, MvpInboxItem


class MvpSearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, platform=None, audience=None, limit=10):
        """知识库检索（关键词匹配版，预留向量化）"""
        try:
            q = self.db.query(MvpKnowledgeItem)
            if platform:
                q = q.filter(MvpKnowledgeItem.platform == platform)
            if audience:
                q = q.filter(MvpKnowledgeItem.audience == audience)
            
            keywords = [kw.strip() for kw in query.split() if kw.strip()]
            if keywords:
                conditions = []
                for kw in keywords[:5]:
                    conditions.append(MvpKnowledgeItem.title.ilike(f"%{kw}%"))
                    conditions.append(MvpKnowledgeItem.content.ilike(f"%{kw}%"))
                q = q.filter(or_(*conditions))
            
            return q.order_by(MvpKnowledgeItem.use_count.desc()).limit(limit).all()
        except Exception:
            return []

    def search_materials(self, query: str, platform=None, is_hot=None, limit=10):
        """素材库检索"""
        try:
            q = self.db.query(MvpMaterialItem)
            if platform:
                q = q.filter(MvpMaterialItem.platform == platform)
            if is_hot is not None:
                q = q.filter(MvpMaterialItem.is_hot == is_hot)
            
            keywords = [kw.strip() for kw in query.split() if kw.strip()]
            if keywords:
                conditions = []
                for kw in keywords[:5]:
                    conditions.append(MvpMaterialItem.title.ilike(f"%{kw}%"))
                    conditions.append(MvpMaterialItem.content.ilike(f"%{kw}%"))
                q = q.filter(or_(*conditions))
            
            return q.order_by(MvpMaterialItem.use_count.desc()).limit(limit).all()
        except Exception:
            return []

    def search_inbox(self, query: str, platform=None, status=None, limit=10):
        """收件箱检索"""
        try:
            q = self.db.query(MvpInboxItem)
            if platform:
                q = q.filter(MvpInboxItem.platform == platform)
            if status:
                q = q.filter(MvpInboxItem.biz_status == status)
            
            keywords = [kw.strip() for kw in query.split() if kw.strip()]
            if keywords:
                conditions = []
                for kw in keywords[:5]:
                    conditions.append(MvpInboxItem.title.ilike(f"%{kw}%"))
                    conditions.append(MvpInboxItem.content.ilike(f"%{kw}%"))
                    conditions.append(MvpInboxItem.keyword.ilike(f"%{kw}%"))
                q = q.filter(or_(*conditions))
            
            return q.order_by(MvpInboxItem.created_at.desc()).limit(limit).all()
        except Exception:
            return []

    def unified_search(self, query: str, sources=None, platform=None, limit=20):
        """统一检索：同时搜索多个数据源"""
        if not sources:
            sources = ["knowledge", "material", "inbox"]
        
        results = {
            "knowledge": [],
            "material": [],
            "inbox": [],
            "total": 0
        }
        
        per_source_limit = max(limit // len(sources), 5)
        
        if "knowledge" in sources:
            results["knowledge"] = [
                {
                    "id": k.id,
                    "title": k.title,
                    "content_preview": k.content[:200] if k.content else "",
                    "category": k.category,
                    "platform": k.platform,
                    "source": "knowledge"
                }
                for k in self.search(query, platform=platform, limit=per_source_limit)
            ]
        
        if "material" in sources:
            results["material"] = [
                {
                    "id": m.id,
                    "title": m.title,
                    "content_preview": m.content[:200] if m.content else "",
                    "platform": m.platform,
                    "is_hot": m.is_hot,
                    "source": "material"
                }
                for m in self.search_materials(query, platform=platform, limit=per_source_limit)
            ]
        
        if "inbox" in sources:
            results["inbox"] = [
                {
                    "id": i.id,
                    "title": i.title,
                    "content_preview": i.content[:200] if i.content else "",
                    "platform": i.platform,
                    "status": i.biz_status,
                    "source": "inbox"
                }
                for i in self.search_inbox(query, platform=platform, limit=per_source_limit)
            ]
        
        results["total"] = len(results["knowledge"]) + len(results["material"]) + len(results["inbox"])
        
        return results

    def get_suggestions(self, prefix: str, limit=10):
        """搜索建议（基于历史搜索词和标题）"""
        try:
            # 从素材标题中提取建议
            materials = self.db.query(MvpMaterialItem.title).filter(
                MvpMaterialItem.title.ilike(f"%{prefix}%")
            ).limit(limit).all()
            
            suggestions = []
            for m in materials:
                # 提取包含前缀的关键词
                words = m.title.split()
                for word in words:
                    if prefix.lower() in word.lower() and word not in suggestions:
                        suggestions.append(word)
                        if len(suggestions) >= limit:
                            break
                if len(suggestions) >= limit:
                    break
            
            return suggestions[:limit]
        except Exception:
            return []

    def get_hot_keywords(self, limit=10):
        """获取热门关键词"""
        try:
            # 从高使用率素材中提取关键词
            hot_materials = self.db.query(MvpMaterialItem).filter(
                MvpMaterialItem.is_hot == True
            ).order_by(MvpMaterialItem.use_count.desc()).limit(50).all()
            
            # 简单的关键词统计
            keyword_count = {}
            for m in hot_materials:
                words = (m.title or "").split()
                for word in words:
                    if len(word) >= 2:  # 过滤单字符
                        keyword_count[word] = keyword_count.get(word, 0) + 1
            
            # 按频率排序
            sorted_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)
            return [kw for kw, _ in sorted_keywords[:limit]]
        except Exception:
            return []
