"""混合检索服务 - 关键词+向量+元数据过滤+rerank

改造说明 (Task #4):
- 向量检索使用 pgvector 原生 cosine_distance 算子 (<=>)
- 不再手动解析 JSON embedding + 计算相似度
- 使用 SQLAlchemy 的 pgvector 支持

改造说明 (Task #18):
- 添加查询耗时日志
- 优化批量查询避免N+1问题
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

from app.models.models import MvpKnowledgeChunk, MvpKnowledgeItem
from app.services.embedding_service import get_embedding_service
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ChunkSearchResult:
    """检索结果"""

    def __init__(
        self,
        chunk_id: int,
        knowledge_id: int,
        content: str,
        chunk_type: str,
        metadata: dict,
        score: float,
        source: str,
        knowledge_item: dict = None,
    ):
        self.chunk_id = chunk_id
        self.knowledge_id = knowledge_id
        self.content = content
        self.chunk_type = chunk_type
        self.metadata = metadata
        self.score = score  # 相关性分数 0~1
        self.source = source  # "keyword" / "vector" / "merged"
        self.knowledge_item = knowledge_item or {}

    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "knowledge_id": self.knowledge_id,
            "content": self.content,
            "chunk_type": self.chunk_type,
            "metadata": self.metadata,
            "score": self.score,
            "source": self.source,
            "knowledge_item": self.knowledge_item,
        }


class HybridSearchService:
    """混合检索服务"""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = get_embedding_service()

    async def search(
        self,
        query: str = "",
        library_type: Optional[str] = None,
        platform: Optional[str] = None,
        audience: Optional[str] = None,
        topic: Optional[str] = None,
        content_type: Optional[str] = None,
        account_type: Optional[str] = None,
        goal: Optional[str] = None,
        top_k: int = 8,
        keyword_top: int = 20,
        vector_top: int = 20,
        merge_top: int = 30,
        embedding_model: str = "volcano",
        enable_rerank: bool = True,
    ) -> List[ChunkSearchResult]:
        """混合检索

        流程: 元数据过滤 → 关键词召回 → 向量召回 → 合并去重 → rerank

        改造说明 (Task #12):
        - 向量检索失败降级为纯关键词检索
        - 元数据过滤放宽：严格过滤无结果时逐步放宽条件
        - 日志增强：记录每个检索步骤的结果数量

        改造说明 (Task #18):
        - 添加各阶段耗时日志
        - 批量查询优化
        """
        total_start = time.time()

        # Step 1: 元数据过滤
        step_start = time.time()
        filtered_knowledge_ids = self._metadata_filter(
            library_type=library_type,
            platform=platform,
            audience=audience,
            topic=topic,
            content_type=content_type,
        )
        logger.info(
            f"元数据过滤: {len(filtered_knowledge_ids)} candidates, 耗时: {(time.time()-step_start)*1000:.1f}ms"
        )

        # 如果严格过滤为空，放宽条件重试
        if not filtered_knowledge_ids:
            logger.warning("严格过滤无结果，放宽条件重试")
            step_start = time.time()
            filtered_knowledge_ids = self._metadata_filter_relaxed(
                library_type=library_type,
                platform=platform,
            )
            logger.info(
                f"放宽过滤: {len(filtered_knowledge_ids)} candidates, 耗时: {(time.time()-step_start)*1000:.1f}ms"
            )

        # 如果仍然为空，查全量
        if not filtered_knowledge_ids:
            logger.warning("放宽过滤仍无结果，使用全量知识库")
            step_start = time.time()
            filtered_knowledge_ids = self._get_all_knowledge_ids()
            logger.info(
                f"全量知识库: {len(filtered_knowledge_ids)} candidates, 耗时: {(time.time()-step_start)*1000:.1f}ms"
            )

        # Step 2: 关键词召回 Top N
        step_start = time.time()
        keyword_results = self._keyword_search(
            query=query,
            knowledge_ids=filtered_knowledge_ids,
            top_k=keyword_top,
        )
        logger.info(f"关键词召回: {len(keyword_results)} results, 耗时: {(time.time()-step_start)*1000:.1f}ms")

        # Step 3: 向量召回（带降级）
        vector_results = []
        try:
            step_start = time.time()
            query_embedding = await self.embedding_service.generate_embedding(query)
            if query_embedding:
                vector_results = await self._vector_recall(query_embedding, filtered_knowledge_ids, limit=vector_top)
                logger.info(f"向量召回: {len(vector_results)} results, 耗时: {(time.time()-step_start)*1000:.1f}ms")
            else:
                logger.warning("Embedding 生成失败，跳过向量召回")
        except Exception as e:
            logger.warning(f"向量检索异常，降级为纯关键词: {e}")

        # Step 4: 合并去重 Top M
        step_start = time.time()
        merged = self._merge_and_dedupe(keyword_results, vector_results, top_k=merge_top)
        logger.info(f"合并结果: {len(merged)} results, 耗时: {(time.time()-step_start)*1000:.1f}ms")

        if not merged:
            logger.info(f"混合检索总耗时: {(time.time()-total_start)*1000:.1f}ms, 无结果")
            return []

        # Step 5: Rerank 取前 K 条
        if enable_rerank and len(merged) > top_k:
            step_start = time.time()
            reranked = await self._rerank(query, merged, top_k=top_k, model=embedding_model)
            logger.info(f"Rerank完成: {len(reranked)} results, 耗时: {(time.time()-step_start)*1000:.1f}ms")
            logger.info(f"混合检索总耗时: {(time.time()-total_start)*1000:.1f}ms")
            return reranked

        logger.info(f"混合检索总耗时: {(time.time()-total_start)*1000:.1f}ms, 返回{len(merged[:top_k])}条结果")
        return merged[:top_k]

    def _metadata_filter(
        self,
        library_type: Optional[str] = None,
        platform: Optional[str] = None,
        audience: Optional[str] = None,
        topic: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> List[int]:
        """元数据过滤，返回符合条件的knowledge_ids"""
        query = self.db.query(MvpKnowledgeItem.id)

        if library_type:
            query = query.filter(MvpKnowledgeItem.library_type == library_type)
        if platform:
            query = query.filter(MvpKnowledgeItem.platform == platform)
        if audience:
            query = query.filter(MvpKnowledgeItem.audience == audience)
        if topic:
            query = query.filter(MvpKnowledgeItem.topic == topic)
        if content_type:
            query = query.filter(MvpKnowledgeItem.content_type == content_type)

        results = query.limit(500).all()
        return [r[0] for r in results]

    def _metadata_filter_relaxed(
        self,
        library_type: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> List[int]:
        """放宽元数据过滤 - 只保留最基础的过滤条件

        去掉 audience/topic/content_type 等过滤
        只保留 library_type 和 platform 过滤
        """
        query = self.db.query(MvpKnowledgeItem.id)

        if library_type:
            query = query.filter(MvpKnowledgeItem.library_type == library_type)
        if platform:
            query = query.filter(MvpKnowledgeItem.platform == platform)

        results = query.limit(500).all()
        return [r[0] for r in results]

    def _get_all_knowledge_ids(self) -> List[int]:
        """获取全量知识库ID"""
        items = self.db.query(MvpKnowledgeItem.id).limit(1000).all()
        return [item.id for item in items]

    def _keyword_search(
        self,
        query: str,
        knowledge_ids: List[int],
        top_k: int = 20,
    ) -> List[ChunkSearchResult]:
        """关键词检索（优化版 - 批量查询避免N+1）"""
        if not query or not knowledge_ids:
            return []

        # 在chunks表中搜索
        keywords = [kw.strip() for kw in query.split() if kw.strip()]
        if not keywords:
            keywords = [query]

        # 构建 OR 条件: content 包含任一关键词
        conditions = []
        for kw in keywords:
            conditions.append(MvpKnowledgeChunk.content.ilike(f"%{kw}%"))

        # 使用joinedload或批量查询优化
        chunks = (
            self.db.query(MvpKnowledgeChunk)
            .filter(
                MvpKnowledgeChunk.knowledge_id.in_(knowledge_ids),
                or_(*conditions) if conditions else True,
            )
            .limit(top_k * 2)  # 多取一些用于排序筛选
            .all()
        )

        # 批量获取所有相关的knowledge_item信息（避免N+1查询）
        knowledge_ids_needed = list(set(chunk.knowledge_id for chunk in chunks))
        knowledge_items_map = self._get_knowledge_items_batch(knowledge_ids_needed)

        results = []
        for chunk in chunks:
            # 计算关键词匹配分数
            content_lower = (chunk.content or "").lower()
            match_count = sum(1 for kw in keywords if kw.lower() in content_lower)
            score = match_count / max(len(keywords), 1)

            metadata = {}
            if chunk.metadata_json:
                try:
                    metadata = json.loads(chunk.metadata_json)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse metadata: {e}")
                    metadata = {}

            # 从批量查询结果中获取knowledge_item信息
            ki = knowledge_items_map.get(chunk.knowledge_id, {})

            results.append(
                ChunkSearchResult(
                    chunk_id=chunk.id,
                    knowledge_id=chunk.knowledge_id,
                    content=chunk.content,
                    chunk_type=chunk.chunk_type,
                    metadata=metadata,
                    score=score,
                    source="keyword",
                    knowledge_item=ki,
                )
            )

        # 按分数降序排列
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    async def _vector_search(
        self,
        query: str,
        knowledge_ids: List[int],
        top_k: int = 20,
        model: str = "volcano",
    ) -> List[ChunkSearchResult]:
        """向量检索 - 使用 pgvector 原生 cosine_distance 算子

        注意：此方法已由 search() 直接调用 _vector_recall 替代
        保留此方法以兼容其他调用方
        """
        if not query or not knowledge_ids:
            return []

        try:
            # 生成 query 的 embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            if not query_embedding:
                logger.warning("向量生成失败，跳过向量检索")
                return []

            return await self._vector_recall(query_embedding, knowledge_ids, limit=top_k)
        except Exception as e:
            logger.warning(f"向量检索异常: {e}")
            return []

    async def _vector_recall(
        self, query_embedding: List[float], candidate_ids: List[int], limit: int = 20
    ) -> List[ChunkSearchResult]:
        """使用 pgvector 原生向量检索（优化版 - 批量查询避免N+1）

        使用 cosine_distance (<=>) 算子，距离越小越相似
        相似度分数 = 1 - distance

        注意：如果 pgvector 扩展不可用，将返回空列表并优雅降级
        """
        start_time = time.time()
        try:
            # 使用 pgvector 的 cosine_distance 算子进行检索
            # 注意: pgvector 的 <=> 返回的是距离，范围 [0, 2]，越小越相似
            results_query = (
                self.db.query(
                    MvpKnowledgeChunk, MvpKnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance")
                )
                .filter(MvpKnowledgeChunk.knowledge_id.in_(candidate_ids), MvpKnowledgeChunk.embedding.isnot(None))
                .order_by("distance")
                .limit(limit)
            )

            rows = results_query.all()

            # 批量获取所有相关的knowledge_item信息（避免N+1查询）
            knowledge_ids_needed = list(set(row[0].knowledge_id for row in rows))
            knowledge_items_map = self._get_knowledge_items_batch(knowledge_ids_needed)

            results = []
            for chunk, distance in rows:
                try:
                    # cosine_distance 范围 [0, 2]，转换为相似度分数 [1, -1]
                    # 通常距离 < 1 表示相似，我们映射到 0-1 范围便于展示
                    similarity = 1.0 - (distance / 2.0)

                    metadata = {}
                    if chunk.metadata_json:
                        try:
                            metadata = json.loads(chunk.metadata_json)
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse metadata: {e}")
                            metadata = {}

                    # 从批量查询结果中获取knowledge_item信息
                    ki = knowledge_items_map.get(chunk.knowledge_id, {})

                    results.append(
                        ChunkSearchResult(
                            chunk_id=chunk.id,
                            knowledge_id=chunk.knowledge_id,
                            content=chunk.content,
                            chunk_type=chunk.chunk_type,
                            metadata=metadata,
                            score=similarity,
                            source="vector",
                            knowledge_item=ki,
                        )
                    )
                except Exception as e:
                    logger.debug(f"向量检索跳过 chunk {chunk.id}: {e}")
                    continue

            # 按相似度降序排列（pgvector 已经按距离升序排列，这里保持一致）
            results.sort(key=lambda x: x.score, reverse=True)
            logger.debug(f"向量检索DB查询耗时: {(time.time()-start_time)*1000:.1f}ms, 返回{len(results)}条结果")
            return results

        except Exception as e:
            # pgvector 扩展不可用时的优雅降级
            error_msg = str(e)
            if "extension" in error_msg.lower() and "vector" in error_msg.lower():
                logger.warning("pgvector 扩展不可用，跳过向量检索，降级为纯关键词检索")
            else:
                logger.warning(f"向量检索失败，降级为纯关键词检索: {e}")
            return []

    def _merge_and_dedupe(
        self,
        keyword_results: List[ChunkSearchResult],
        vector_results: List[ChunkSearchResult],
        top_k: int = 30,
    ) -> List[ChunkSearchResult]:
        """合并去重两路结果"""
        seen_ids = set()
        merged = []

        # 先加入关键词结果
        for r in keyword_results:
            if r.chunk_id not in seen_ids:
                seen_ids.add(r.chunk_id)
                merged.append(r)

        # 再加入向量结果
        for r in vector_results:
            if r.chunk_id not in seen_ids:
                seen_ids.add(r.chunk_id)
                merged.append(r)
            else:
                # 已存在，取两者最高分
                for m in merged:
                    if m.chunk_id == r.chunk_id:
                        m.score = max(m.score, r.score)
                        m.source = "merged"
                        break

        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:top_k]

    async def _rerank(
        self,
        query: str,
        candidates: List[ChunkSearchResult],
        top_k: int = 8,
        model: str = "volcano",
    ) -> List[ChunkSearchResult]:
        """使用LLM对候选结果进行rerank

        集成 RerankService，支持 LLM 打分和 embedding 相似度降级
        """
        if not candidates or len(candidates) <= 1:
            return candidates[:top_k]

        try:
            from app.services.rerank_service import RerankService

            reranker = RerankService()

            # 将 ChunkSearchResult 转换为 Dict 格式
            doc_dicts = []
            for c in candidates[:20]:  # 最多20条进行rerank
                doc_dicts.append(
                    {
                        "chunk_id": c.chunk_id,
                        "knowledge_id": c.knowledge_id,
                        "title": c.knowledge_item.get("title", "") if c.knowledge_item else "",
                        "content": c.content,
                        "chunk_type": c.chunk_type,
                        "metadata": c.metadata,
                        "score": c.score,
                        "source": c.source,
                        "knowledge_item": c.knowledge_item,
                    }
                )

            # 调用 RerankService 进行重排
            reranked_dicts = await reranker.rerank(query, doc_dicts, top_k=top_k)

            # 将结果转回 ChunkSearchResult 格式
            reranked = []
            for doc in reranked_dicts:
                result = ChunkSearchResult(
                    chunk_id=doc["chunk_id"],
                    knowledge_id=doc["knowledge_id"],
                    content=doc["content"],
                    chunk_type=doc["chunk_type"],
                    metadata=doc.get("metadata", {}),
                    score=doc.get("rerank_score", doc.get("score", 0)) / 10.0,  # 归一化到 0-1
                    source="reranked",
                    knowledge_item=doc.get("knowledge_item", {}),
                )
                reranked.append(result)

            logger.info(f"Rerank 完成: {len(reranked)} results")
            return reranked

        except Exception as e:
            logger.warning(f"Rerank 失败，使用原始排序: {e}")
            return candidates[:top_k]

    def _get_knowledge_item_info(self, knowledge_id: int) -> dict:
        """获取knowledge_item的基本信息（单条查询，保留用于兼容）"""
        item = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id == knowledge_id).first()
        if not item:
            return {}
        return self._knowledge_item_to_dict(item)

    def _get_knowledge_items_batch(self, knowledge_ids: List[int]) -> Dict[int, dict]:
        """批量获取knowledge_item信息（优化N+1查询）

        Args:
            knowledge_ids: 知识项ID列表

        Returns:
            Dict[int, dict]: 以knowledge_id为键的字典
        """
        if not knowledge_ids:
            return {}

        items = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id.in_(knowledge_ids)).all()

        return {item.id: self._knowledge_item_to_dict(item) for item in items}

    def _knowledge_item_to_dict(self, item: MvpKnowledgeItem) -> dict:
        """将MvpKnowledgeItem转换为字典"""
        return {
            "id": item.id,
            "title": item.title or "",
            "platform": item.platform or "",
            "audience": item.audience or "",
            "topic": getattr(item, "topic", "") or "",
            "content_type": getattr(item, "content_type", "") or "",
            "library_type": item.library_type or "",
            "category": item.category or "",
            "risk_level": getattr(item, "risk_level", "") or "",
            "use_count": item.use_count or 0,
        }


def get_hybrid_search_service(db: Session) -> HybridSearchService:
    return HybridSearchService(db)
