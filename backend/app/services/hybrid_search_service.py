"""混合检索服务 - 关键词+向量+元数据过滤+rerank"""
import json
import logging
import math
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text

from app.models.models import MvpKnowledgeItem, MvpKnowledgeChunk
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class ChunkSearchResult:
    """检索结果"""
    def __init__(self, chunk_id: int, knowledge_id: int, content: str,
                 chunk_type: str, metadata: dict, score: float,
                 source: str, knowledge_item: dict = None):
        self.chunk_id = chunk_id
        self.knowledge_id = knowledge_id
        self.content = content
        self.chunk_type = chunk_type
        self.metadata = metadata
        self.score = score      # 相关性分数 0~1
        self.source = source    # "keyword" / "vector" / "merged"
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
        """
        # Step 1: 构建元数据过滤的知识条目ID集合
        filtered_knowledge_ids = self._metadata_filter(
            library_type=library_type,
            platform=platform,
            audience=audience,
            topic=topic,
            content_type=content_type,
        )
        
        if not filtered_knowledge_ids:
            logger.info(f"元数据过滤后无结果: library_type={library_type}, platform={platform}")
            return []
        
        # Step 2: 关键词召回 Top N
        keyword_results = self._keyword_search(
            query=query,
            knowledge_ids=filtered_knowledge_ids,
            top_k=keyword_top,
        )
        
        # Step 3: 向量召回 Top N
        vector_results = await self._vector_search(
            query=query,
            knowledge_ids=filtered_knowledge_ids,
            top_k=vector_top,
            model=embedding_model,
        )
        
        # Step 4: 合并去重 Top M
        merged = self._merge_and_dedupe(keyword_results, vector_results, top_k=merge_top)
        
        if not merged:
            return []
        
        # Step 5: Rerank 取前 K 条
        if enable_rerank and len(merged) > top_k:
            reranked = await self._rerank(query, merged, top_k=top_k, model=embedding_model)
            return reranked
        
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
    
    def _keyword_search(
        self,
        query: str,
        knowledge_ids: List[int],
        top_k: int = 20,
    ) -> List[ChunkSearchResult]:
        """关键词检索"""
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
        
        chunks = (
            self.db.query(MvpKnowledgeChunk)
            .filter(
                MvpKnowledgeChunk.knowledge_id.in_(knowledge_ids),
                or_(*conditions) if conditions else True,
            )
            .limit(top_k)
            .all()
        )
        
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
                except:
                    pass
            
            # 获取关联的knowledge_item信息
            ki = self._get_knowledge_item_info(chunk.knowledge_id)
            
            results.append(ChunkSearchResult(
                chunk_id=chunk.id,
                knowledge_id=chunk.knowledge_id,
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                metadata=metadata,
                score=score,
                source="keyword",
                knowledge_item=ki,
            ))
        
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
        """向量检索"""
        if not query or not knowledge_ids:
            return []
        
        # 生成query的embedding
        query_embedding = await self.embedding_service.generate_embedding(query, model=model)
        if not query_embedding:
            logger.warning("向量生成失败，跳过向量检索")
            return []
        
        # 从数据库获取有embedding的chunks
        chunks = (
            self.db.query(MvpKnowledgeChunk)
            .filter(
                MvpKnowledgeChunk.knowledge_id.in_(knowledge_ids),
                MvpKnowledgeChunk.embedding.isnot(None),
                MvpKnowledgeChunk.embedding != "",
            )
            .limit(200)  # 限制计算量
            .all()
        )
        
        results = []
        for chunk in chunks:
            try:
                chunk_embedding = json.loads(chunk.embedding)
                if not chunk_embedding:
                    continue
                # 余弦相似度
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                
                metadata = {}
                if chunk.metadata_json:
                    try:
                        metadata = json.loads(chunk.metadata_json)
                    except:
                        pass
                
                ki = self._get_knowledge_item_info(chunk.knowledge_id)
                
                results.append(ChunkSearchResult(
                    chunk_id=chunk.id,
                    knowledge_id=chunk.knowledge_id,
                    content=chunk.content,
                    chunk_type=chunk.chunk_type,
                    metadata=metadata,
                    score=similarity,
                    source="vector",
                    knowledge_item=ki,
                ))
            except Exception as e:
                logger.debug(f"向量检索跳过chunk {chunk.id}: {e}")
                continue
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """计算余弦相似度"""
        if not vec_a or not vec_b:
            return 0.0
        
        min_len = min(len(vec_a), len(vec_b))
        vec_a = vec_a[:min_len]
        vec_b = vec_b[:min_len]
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
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
        """使用LLM对候选结果进行rerank"""
        try:
            from app.services.ai_service import AIService
            ai = AIService()
            
            # 构建候选摘要列表
            candidate_texts = []
            for i, c in enumerate(candidates[:20]):  # 最多20条进行rerank
                snippet = c.content[:200].replace("\n", " ")
                candidate_texts.append(f"{i+1}. {snippet}")
            
            prompt = f"""你是一个内容相关性评估专家。请根据用户的查询意图，对以下候选内容按相关性从高到低排序。

用户查询意图: {query}

候选内容:
{chr(10).join(candidate_texts)}

请只返回排序后的编号列表，用逗号分隔，如: 3,1,5,2,4
只返回前{top_k}个最相关的编号。"""

            result = await ai.call_llm(
                prompt=prompt,
                system_prompt="你是内容相关性评估专家，请按相关性排序候选内容。",
                use_cloud=(model == "volcano"),
            )
            
            # 解析排序结果
            if result:
                numbers = []
                for part in result.replace(" ", "").split(","):
                    try:
                        num = int(part.strip()) - 1  # 转为0-based
                        if 0 <= num < len(candidates):
                            numbers.append(num)
                    except:
                        continue
                
                if numbers:
                    reranked = []
                    seen = set()
                    for idx in numbers[:top_k]:
                        if idx not in seen:
                            seen.add(idx)
                            c = candidates[idx]
                            c.score = 1.0 - (len(reranked) / top_k)  # 重新赋分
                            reranked.append(c)
                    return reranked
        except Exception as e:
            logger.warning(f"Rerank失败，返回原始排序: {e}")
        
        return candidates[:top_k]
    
    def _get_knowledge_item_info(self, knowledge_id: int) -> dict:
        """获取knowledge_item的基本信息"""
        item = self.db.query(MvpKnowledgeItem).filter(
            MvpKnowledgeItem.id == knowledge_id
        ).first()
        if not item:
            return {}
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
