"""
MVP知识库服务 - 门面类
实际实现已拆分到 mvp_knowledge_crud_service.py 和 mvp_knowledge_search_service.py
保留此类以兼容现有导入。
"""

import logging
from typing import Any, Dict, List, Optional

from app.services.mvp_knowledge_crud_service import LIBRARY_TYPES, MvpKnowledgeCrudService
from app.services.mvp_knowledge_search_service import MvpKnowledgeSearchService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MvpKnowledgeService:
    """门面类 - 委托调用CRUD和搜索子服务

    所有现有的 `from app.services.mvp_knowledge_service import MvpKnowledgeService` 继续工作。
    """

    def __init__(self, db: Session):
        self.db = db
        self._crud = MvpKnowledgeCrudService(db)
        self._search = MvpKnowledgeSearchService(db)

    # ==================== 读取操作委托 ====================

    def list_knowledge(
        self,
        page=1,
        size=20,
        platform=None,
        audience=None,
        style=None,
        category=None,
        keyword=None,
        topic=None,
        content_type=None,
        library_type=None,
    ):
        """列出知识库条目"""
        return self._crud.list_knowledge(
            page=page,
            size=size,
            platform=platform,
            audience=audience,
            style=style,
            category=category,
            keyword=keyword,
            topic=topic,
            content_type=content_type,
            library_type=library_type,
        )

    def get_knowledge(self, knowledge_id: int):
        """获取知识条目详情"""
        return self._crud.get_knowledge(knowledge_id)

    def get_categories(self) -> list:
        """获取所有分类"""
        return self._crud.get_categories()

    def get_library_stats(self) -> List[dict]:
        """获取各分库统计"""
        return self._crud.get_library_stats()

    def list_by_library(self, library_type: str, page: int = 1, size: int = 20, keyword: str = "") -> dict:
        """按分库类型列出知识条目"""
        return self._crud.list_by_library(library_type, page, size, keyword)

    # ==================== 创建操作委托 ====================

    def create_knowledge(self, data: dict):
        """手动创建知识条目"""
        return self._crud.create_knowledge(data)

    def build_from_material(self, material_id: int):
        """从素材构建结构化知识"""
        return self._crud.build_from_material(material_id)

    def batch_build_from_materials(self, material_ids: List[int]) -> dict:
        """批量从素材构建知识"""
        return self._crud.batch_build_from_materials(material_ids)

    def auto_ingest_from_raw(
        self,
        title: str,
        content: str,
        platform: str = "unknown",
        source_url: Optional[str] = None,
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        """自动入库Pipeline：接收原始内容，清洗去重，结构化抽取，直接入知识库

        协调搜索服务（提取字段）和CRUD服务（入库）
        """
        # 使用搜索服务提取结构化字段
        extracted_fields = self._search.extract_all_fields(title, content)

        # 使用CRUD服务入库
        return self._crud.auto_ingest_from_raw(
            title=title,
            content=content,
            platform=platform,
            source_url=source_url,
            author=author,
            extracted_fields=extracted_fields,
        )

    def auto_ingest_batch(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量自动入库Pipeline

        协调搜索服务（提取字段）和CRUD服务（入库）
        """
        # 批量提取字段
        extracted_fields_list = []
        for item in items:
            extracted = self._search.extract_all_fields(item.get("title", ""), item.get("content", ""))
            extracted_fields_list.append(extracted)

        # 使用CRUD服务批量入库
        return self._crud.auto_ingest_batch(items, extracted_fields_list)

    # ==================== 更新操作委托 ====================

    def update_knowledge(self, knowledge_id: int, data: dict):
        """更新知识条目"""
        return self._crud.update_knowledge(knowledge_id, data)

    # ==================== 删除操作委托 ====================

    def delete_knowledge(self, knowledge_id: int):
        """删除知识条目"""
        return self._crud.delete_knowledge(knowledge_id)

    # ==================== 搜索操作委托 ====================

    def search_knowledge(self, query: str, platform=None, audience=None, limit=5):
        """关键词检索知识"""
        return self._search.search_knowledge(query, platform, audience, limit)

    def search_for_generation(
        self,
        platform: str,
        audience: str,
        topic: str = None,
        content_type: str = None,
        account_type: str = None,
        goal: str = None,
    ) -> dict:
        """为内容生成提供多维度知识召回"""
        return self._search.search_for_generation(
            platform=platform,
            audience=audience,
            topic=topic,
            content_type=content_type,
            account_type=account_type,
            goal=goal,
        )

    async def search_for_generation_v2(
        self,
        platform: str = "",
        audience: str = "",
        topic: str = "",
        content_type: str = "",
        account_type: str = "",
        goal: str = "",
        embedding_model: str = "volcano",
    ) -> dict:
        """升级版: 使用混合检索从多个分库并发召回知识"""
        return await self._search.search_for_generation_v2(
            platform=platform,
            audience=audience,
            topic=topic,
            content_type=content_type,
            account_type=account_type,
            goal=goal,
            embedding_model=embedding_model,
        )

    # ==================== 辅助方法委托 ====================

    def auto_classify_library_type(self, knowledge_item) -> str:
        """根据内容自动分类到分库"""
        return self._crud.auto_classify_library_type(knowledge_item)
