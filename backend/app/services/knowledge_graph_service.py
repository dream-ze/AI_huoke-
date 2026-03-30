"""知识图谱服务 - 知识条目关系建模和图遍历检索增强

Task #18: 知识图谱
- 基于 embedding 余弦相似度发现相似主题
- 基于 audience/platform 字段匹配同人群/同平台
- 基于 library_type 发现互补内容
- 图遍历扩展相关条目
"""
import json
import logging
from typing import List, Dict, Optional, Any, Set
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, union_all

from app.models.models import MvpKnowledgeItem, MvpKnowledgeChunk, MvpKnowledgeRelation
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


# 关系类型常量
RELATION_SIMILAR_TOPIC = "similar_topic"      # 相似主题（向量相似）
RELATION_SAME_AUDIENCE = "same_audience"       # 同人群
RELATION_SAME_PLATFORM = "same_platform"       # 同平台
RELATION_COMPLEMENTARY = "complementary"       # 互补内容
RELATION_DERIVED_FROM = "derived_from"         # 衍生自


class KnowledgeGraphService:
    """知识图谱服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = get_embedding_service()
    
    async def build_relations(self, knowledge_id: int) -> List[Dict]:
        """为指定知识条目自动发现并建立关系
        
        - 基于 embedding 余弦相似度发现相似主题（cosine_distance < 0.2 即相似度 > 0.8）
        - 基于 audience/platform 字段匹配同人群/同平台
        - 基于 library_type 发现互补内容
        """
        # 获取目标知识条目
        target = self.db.query(MvpKnowledgeItem).filter(
            MvpKnowledgeItem.id == knowledge_id
        ).first()
        
        if not target:
            raise ValueError(f"知识条目 {knowledge_id} 不存在")
        
        relations_created = []
        
        # 1. 基于向量相似度发现相似主题
        similar_relations = await self._build_similarity_relations(target)
        relations_created.extend(similar_relations)
        
        # 2. 基于元数据匹配构建关系
        metadata_relations = await self._build_metadata_relations(target)
        relations_created.extend(metadata_relations)
        
        self.db.commit()
        return relations_created
    
    async def _build_similarity_relations(self, target: MvpKnowledgeItem) -> List[Dict]:
        """基于向量相似度构建相似主题关系
            
        注意：如果 pgvector 扩展不可用，将跳过向量相似度计算
        """
        relations = []
    
        try:
            # 获取目标的 embedding
            target_chunks = self.db.query(MvpKnowledgeChunk).filter(
                MvpKnowledgeChunk.knowledge_id == target.id,
                MvpKnowledgeChunk.embedding.isnot(None)
            ).limit(3).all()
    
            if not target_chunks:
                logger.info(f"知识条目 {target.id} 没有 embedding，跳过相似度计算")
                return relations
    
            # 使用第一个 chunk 的 embedding 作为代表
            target_embedding = target_chunks[0].embedding
    
            # 查找相似的知识条目（通过 chunk 表）
            # cosine_distance < 0.25 表示相似度 > 0.875
            distance_expr = MvpKnowledgeChunk.embedding.cosine_distance(target_embedding)
            similar_chunks = (
                self.db.query(
                    MvpKnowledgeChunk,
                    distance_expr.label("distance")
                )
                .filter(
                    MvpKnowledgeChunk.knowledge_id != target.id,
                    MvpKnowledgeChunk.embedding.isnot(None),
                    distance_expr < 0.25  # 直接用表达式过滤
                )
                .order_by(distance_expr)
                .limit(10)
                .all()
            )
    
            for chunk, distance in similar_chunks:
                # 计算相似度分数 (distance 0~2, 转换为 0~1)
                similarity = 1.0 - (distance / 2.0)
                weight = min(1.0, similarity)
    
                # 创建关系
                relation = self._create_or_update_relation(
                    source_id=target.id,
                    target_id=chunk.knowledge_id,
                    relation_type=RELATION_SIMILAR_TOPIC,
                    weight=weight,
                    metadata={"distance": float(distance), "similarity": similarity}
                )
                if relation:
                    relations.append({
                        "source_id": target.id,
                        "target_id": chunk.knowledge_id,
                        "relation_type": RELATION_SIMILAR_TOPIC,
                        "weight": weight
                    })
    
        except Exception as e:
            # pgvector 扩展不可用时的优雅降级
            error_msg = str(e)
            if "extension" in error_msg.lower() and "vector" in error_msg.lower():
                logger.warning(f"pgvector 扩展不可用，跳过向量相似度关系构建")
            else:
                logger.warning(f"向量相似度计算失败，跳过: {e}")
    
        return relations
    
    async def _build_metadata_relations(self, target: MvpKnowledgeItem) -> List[Dict]:
        """基于元数据匹配构建关系"""
        relations = []
        
        # 同人群关系
        if target.audience:
            same_audience_items = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.id != target.id,
                MvpKnowledgeItem.audience == target.audience
            ).limit(20).all()
            
            for item in same_audience_items:
                relation = self._create_or_update_relation(
                    source_id=target.id,
                    target_id=item.id,
                    relation_type=RELATION_SAME_AUDIENCE,
                    weight=0.6,
                    metadata={"audience": target.audience}
                )
                if relation:
                    relations.append({
                        "source_id": target.id,
                        "target_id": item.id,
                        "relation_type": RELATION_SAME_AUDIENCE,
                        "weight": 0.6
                    })
        
        # 同平台关系
        if target.platform:
            same_platform_items = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.id != target.id,
                MvpKnowledgeItem.platform == target.platform
            ).limit(20).all()
            
            for item in same_platform_items:
                relation = self._create_or_update_relation(
                    source_id=target.id,
                    target_id=item.id,
                    relation_type=RELATION_SAME_PLATFORM,
                    weight=0.5,
                    metadata={"platform": target.platform}
                )
                if relation:
                    relations.append({
                        "source_id": target.id,
                        "target_id": item.id,
                        "relation_type": RELATION_SAME_PLATFORM,
                        "weight": 0.5
                    })
        
        # 互补内容关系（不同 library_type 但有相同 topic）
        if target.topic:
            complementary_items = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.id != target.id,
                MvpKnowledgeItem.topic == target.topic,
                MvpKnowledgeItem.library_type != target.library_type
            ).limit(10).all()
            
            for item in complementary_items:
                relation = self._create_or_update_relation(
                    source_id=target.id,
                    target_id=item.id,
                    relation_type=RELATION_COMPLEMENTARY,
                    weight=0.7,
                    metadata={"topic": target.topic}
                )
                if relation:
                    relations.append({
                        "source_id": target.id,
                        "target_id": item.id,
                        "relation_type": RELATION_COMPLEMENTARY,
                        "weight": 0.7
                    })
        
        return relations
    
    def _create_or_update_relation(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        weight: float,
        metadata: Dict = None
    ) -> Optional[MvpKnowledgeRelation]:
        """创建或更新关系（避免重复）"""
        # 检查是否已存在
        existing = self.db.query(MvpKnowledgeRelation).filter(
            MvpKnowledgeRelation.source_id == source_id,
            MvpKnowledgeRelation.target_id == target_id,
            MvpKnowledgeRelation.relation_type == relation_type
        ).first()
        
        if existing:
            # 更新权重
            existing.weight = weight
            if metadata:
                existing.metadata_json = json.dumps(metadata, ensure_ascii=False)
            return existing
        
        # 创建新关系
        relation = MvpKnowledgeRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None
        )
        self.db.add(relation)
        return relation
    
    async def batch_build_relations(self, batch_size: int = 100) -> Dict:
        """批量扫描所有知识条目，构建全图关系
        
        Args:
            batch_size: 每批处理数量，默认100
            
        Returns:
            构建统计信息
        """
        # 获取所有有 embedding 的知识条目 ID
        total_items = self.db.query(MvpKnowledgeItem.id).count()
        
        stats = {
            "total_items": total_items,
            "processed": 0,
            "relations_created": 0,
            "errors": 0
        }
        
        # 分批处理
        offset = 0
        while offset < total_items:
            items = self.db.query(MvpKnowledgeItem).offset(offset).limit(batch_size).all()
            
            for item in items:
                try:
                    relations = await self.build_relations(item.id)
                    stats["relations_created"] += len(relations)
                    stats["processed"] += 1
                except Exception as e:
                    logger.error(f"构建关系失败 [{item.id}]: {e}")
                    stats["errors"] += 1
            
            offset += batch_size
            logger.info(f"批量构建进度: {stats['processed']}/{total_items}")
        
        return stats
    
    async def get_related_items(
        self,
        knowledge_id: int,
        relation_type: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """获取关联知识条目（图遍历1跳）
        
        Args:
            knowledge_id: 知识条目ID
            relation_type: 关系类型过滤（可选）
            limit: 返回数量限制
            
        Returns:
            关联知识条目列表
        """
        # 构建查询：获取出边和入边
        query_out = self.db.query(
            MvpKnowledgeRelation,
            MvpKnowledgeItem
        ).join(
            MvpKnowledgeItem,
            MvpKnowledgeRelation.target_id == MvpKnowledgeItem.id
        ).filter(
            MvpKnowledgeRelation.source_id == knowledge_id
        )
        
        query_in = self.db.query(
            MvpKnowledgeRelation,
            MvpKnowledgeItem
        ).join(
            MvpKnowledgeItem,
            MvpKnowledgeRelation.source_id == MvpKnowledgeItem.id
        ).filter(
            MvpKnowledgeRelation.target_id == knowledge_id
        )
        
        if relation_type:
            query_out = query_out.filter(MvpKnowledgeRelation.relation_type == relation_type)
            query_in = query_in.filter(MvpKnowledgeRelation.relation_type == relation_type)
        
        # 执行查询
        outgoing = query_out.limit(limit).all()
        incoming = query_in.limit(limit).all()
        
        results = []
        seen_ids = set()
        
        for relation, item in outgoing:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                results.append({
                    "id": item.id,
                    "title": item.title,
                    "platform": item.platform,
                    "audience": item.audience,
                    "topic": item.topic,
                    "library_type": item.library_type,
                    "relation_type": relation.relation_type,
                    "weight": relation.weight,
                    "direction": "outgoing"
                })
        
        for relation, item in incoming:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                results.append({
                    "id": item.id,
                    "title": item.title,
                    "platform": item.platform,
                    "audience": item.audience,
                    "topic": item.topic,
                    "library_type": item.library_type,
                    "relation_type": relation.relation_type,
                    "weight": relation.weight,
                    "direction": "incoming"
                })
        
        # 按权重排序
        results.sort(key=lambda x: x["weight"], reverse=True)
        return results[:limit]
    
    async def get_knowledge_graph(
        self,
        library_type: str = None,
        limit: int = 50
    ) -> Dict:
        """获取知识图谱数据（nodes + edges 格式，用于前端可视化）
        
        Args:
            library_type: 分库类型过滤（可选）
            limit: 节点数量限制
            
        Returns:
            {"nodes": [...], "edges": [...]}
        """
        # 查询知识条目
        items_query = self.db.query(MvpKnowledgeItem)
        if library_type:
            items_query = items_query.filter(MvpKnowledgeItem.library_type == library_type)
        
        items = items_query.limit(limit).all()
        item_ids = {item.id for item in items}
        
        # 构建节点
        nodes = []
        for item in items:
            nodes.append({
                "id": item.id,
                "title": item.title[:50] if item.title else "",
                "platform": item.platform,
                "audience": item.audience,
                "topic": item.topic,
                "library_type": item.library_type,
                "use_count": item.use_count or 0,
                "is_hot": getattr(item, 'is_hot', False) or False
            })
        
        # 查询关系（只返回涉及的节点之间的边）
        relations = self.db.query(MvpKnowledgeRelation).filter(
            or_(
                MvpKnowledgeRelation.source_id.in_(item_ids),
                MvpKnowledgeRelation.target_id.in_(item_ids)
            )
        ).limit(limit * 5).all()
        
        # 构建边
        edges = []
        for rel in relations:
            edges.append({
                "source": rel.source_id,
                "target": rel.target_id,
                "type": rel.relation_type,
                "weight": rel.weight
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        }
    
    async def enhanced_search(
        self,
        query: str,
        top_k: int = 5,
        expand_limit: int = 3
    ) -> List[Dict]:
        """图增强检索：先向量检索，再沿关系图扩展相关条目
        
        Args:
            query: 查询文本
            top_k: 初始检索数量
            expand_limit: 每个结果扩展的相关条目数量
            
        Returns:
            增强检索结果列表
        """
        from app.services.hybrid_search_service import HybridSearchService
        
        # 1. 初始向量检索
        hybrid_search = HybridSearchService(self.db)
        initial_results = await hybrid_search.search(
            query=query,
            top_k=top_k,
            enable_rerank=False
        )
        
        if not initial_results:
            return []
        
        # 2. 图扩展
        expanded_results = []
        seen_ids = set()
        
        for result in initial_results:
            knowledge_id = result.knowledge_id
            
            if knowledge_id in seen_ids:
                continue
            seen_ids.add(knowledge_id)
            
            # 添加原始结果
            expanded_results.append({
                "id": knowledge_id,
                "title": result.knowledge_item.get("title", ""),
                "content": result.content[:200] if result.content else "",
                "score": result.score,
                "source": "primary",
                "chunk_id": result.chunk_id
            })
            
            # 扩展相关条目
            related = await self.get_related_items(knowledge_id, limit=expand_limit)
            for rel_item in related:
                if rel_item["id"] not in seen_ids:
                    seen_ids.add(rel_item["id"])
                    # 获取内容
                    item = self.db.query(MvpKnowledgeItem).filter(
                        MvpKnowledgeItem.id == rel_item["id"]
                    ).first()
                    if item:
                        expanded_results.append({
                            "id": item.id,
                            "title": item.title,
                            "content": (item.summary or item.content)[:200] if item.content else "",
                            "score": result.score * rel_item["weight"],  # 降低分数
                            "source": f"expanded_via_{rel_item['relation_type']}",
                            "relation_weight": rel_item["weight"]
                        })
        
        # 按分数排序
        expanded_results.sort(key=lambda x: x["score"], reverse=True)
        return expanded_results
    
    async def cluster_topics(self, min_cluster_size: int = 2) -> List[Dict]:
        """主题聚类：基于关系图发现主题簇
        
        使用简单的连通分量算法发现主题簇
        
        Args:
            min_cluster_size: 最小簇大小
            
        Returns:
            [{"topic": "...", "items": [...], "count": N}]
        """
        # 获取所有关系
        relations = self.db.query(MvpKnowledgeRelation).filter(
            MvpKnowledgeRelation.relation_type == RELATION_SIMILAR_TOPIC
        ).all()
        
        # 构建邻接表
        graph = defaultdict(set)
        for rel in relations:
            graph[rel.source_id].add(rel.target_id)
            graph[rel.target_id].add(rel.source_id)
        
        # 找连通分量（BFS）
        visited = set()
        clusters = []
        
        for node in graph:
            if node in visited:
                continue
            
            # BFS 遍历
            cluster = []
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                cluster.append(current)
                queue.extend(graph[current] - visited)
            
            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)
        
        # 获取簇内条目信息
        results = []
        for idx, cluster in enumerate(clusters):
            items = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.id.in_(cluster)
            ).all()
            
            # 统计主要 topic
            topic_counts = defaultdict(int)
            for item in items:
                if item.topic:
                    topic_counts[item.topic] += 1
            
            main_topic = max(topic_counts.items(), key=lambda x: x[1])[0] if topic_counts else f"cluster_{idx}"
            
            results.append({
                "topic": main_topic,
                "item_ids": cluster,
                "items": [
                    {"id": item.id, "title": item.title, "topic": item.topic}
                    for item in items[:10]
                ],
                "count": len(items)
            })
        
        # 按簇大小排序
        results.sort(key=lambda x: x["count"], reverse=True)
        return results
    
    async def get_graph_stats(self) -> Dict:
        """图谱统计：节点数、边数、平均度、最大连通分量等"""
        # 节点数
        node_count = self.db.query(func.count(MvpKnowledgeItem.id)).scalar() or 0
        
        # 边数
        edge_count = self.db.query(func.count(MvpKnowledgeRelation.id)).scalar() or 0
        
        # 各类型关系统计
        relation_type_stats = self.db.query(
            MvpKnowledgeRelation.relation_type,
            func.count(MvpKnowledgeRelation.id)
        ).group_by(MvpKnowledgeRelation.relation_type).all()
        
        relation_stats = {r[0]: r[1] for r in relation_type_stats}
        
        # 平均度（每个节点的平均边数）
        avg_degree = (edge_count * 2 / node_count) if node_count > 0 else 0
        
        # 有关系的节点数（使用 UNION 去重避免重复计数）
        source_ids = self.db.query(MvpKnowledgeRelation.source_id.label("node_id"))
        target_ids = self.db.query(MvpKnowledgeRelation.target_id.label("node_id"))
        subq = union_all(source_ids, target_ids).subquery()
        nodes_with_relations = self.db.query(
            func.count(func.distinct(subq.c.node_id))
        ).scalar() or 0
        
        # 有 embedding 的节点数
        nodes_with_embedding = self.db.query(
            func.count(func.distinct(MvpKnowledgeChunk.knowledge_id))
        ).filter(
            MvpKnowledgeChunk.embedding.isnot(None)
        ).scalar() or 0
        
        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "avg_degree": round(avg_degree, 2),
            "nodes_with_relations": nodes_with_relations,
            "nodes_with_embedding": nodes_with_embedding,
            "relation_type_stats": relation_stats,
            "connectivity_ratio": round(nodes_with_relations / node_count, 2) if node_count > 0 else 0
        }


def get_knowledge_graph_service(db: Session) -> KnowledgeGraphService:
    return KnowledgeGraphService(db)
