"""采集入库 Pipeline 服务 - 串联清洗、筛选、入库全流程"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.models import MvpInboxItem, MvpMaterialItem, MvpKnowledgeItem, MvpKnowledgeChunk
from app.services.cleaning_service import CleaningService
from app.services.extraction_service import ExtractionService
from app.services.quality_screening_service import QualityScreeningService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class PipelineService:
    """采集入库 Pipeline 服务"""
    
    def __init__(self, db: Session):
        self.db = db
        # 初始化下游服务
        self.cleaning = CleaningService(db)
        self.embedding = EmbeddingService()
        
        # ExtractionService 需要从 settings 获取配置
        try:
            from app.core.config import settings
            self.extraction = ExtractionService(
                ollama_base_url=getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
                model=getattr(settings, 'OLLAMA_MODEL', 'qwen')
            )
        except Exception as e:
            logger.warning(f"Failed to init ExtractionService: {e}")
            self.extraction = None
        
        # QualityScreeningService 依赖 extraction
        self.screening = QualityScreeningService(db, extraction_service=self.extraction)
    
    async def ingest_from_collector(self, raw_data: dict) -> dict:
        """采集数据入收件箱
        
        Args:
            raw_data: 采集数据，格式:
                {
                    platform: str, title: str, content: str,
                    author_name: str, publish_time: str, url: str,
                    source_id: str, like_count: int, comment_count: int,
                    favorite_count: int
                }
        
        Returns:
            {success: bool, item_id: int, clean_status: str, error: str}
        """
        try:
            # 1. 创建 MvpInboxItem
            item = MvpInboxItem(
                platform=raw_data.get("platform", "unknown"),
                source_id=raw_data.get("source_id"),
                title=raw_data.get("title", "")[:500],
                content=raw_data.get("content", ""),
                author=raw_data.get("author_name"),
                author_name=raw_data.get("author_name"),
                source_url=raw_data.get("url"),
                url=raw_data.get("url"),
                source_type="collect",
                like_count=raw_data.get("like_count", 0),
                comment_count=raw_data.get("comment_count", 0),
                favorite_count=raw_data.get("favorite_count", 0),
                clean_status="pending",
                material_status="not_in",
            )
            
            # 解析发布时间
            if raw_data.get("publish_time"):
                try:
                    if isinstance(raw_data["publish_time"], str):
                        item.publish_time = datetime.fromisoformat(raw_data["publish_time"].replace('Z', '+00:00'))
                    else:
                        item.publish_time = raw_data["publish_time"]
                except Exception as e:
                    logger.warning(f"Failed to parse publish_time: {e}")
            
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            
            # 2. 自动触发清洗
            clean_result = self.cleaning.clean_item(item.id)
            clean_status = clean_result.get("success", False) and "cleaned" or "failed"
            
            return {
                "success": True,
                "item_id": item.id,
                "clean_status": clean_status,
                "is_duplicate": clean_result.get("is_duplicate", False)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"ingest_from_collector failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def promote_to_material(self, inbox_item_id: int) -> dict:
        """收件箱→素材库
        
        流程:
        1. 查找 inbox item，检查 clean_status == 'cleaned'
        2. 如果 quality_status == 'pending'，先自动触发质量筛选
        3. 创建 MvpMaterialItem，复制基础字段，设置 inbox_item_id 外键
        4. 运行 Ollama 结构化抽取，填充 tags_json/topic/persona
        5. 更新 inbox item 的 material_status = 'in_material'
        
        Args:
            inbox_item_id: 收件箱条目ID
        
        Returns:
            {success: bool, material_id: int, inbox_item_id: int, error: str}
        """
        try:
            # 1. 查找 inbox item
            item = self.db.query(MvpInboxItem).filter(MvpInboxItem.id == inbox_item_id).first()
            if not item:
                return {"success": False, "error": "Item not found"}
            
            if item.clean_status != "cleaned":
                return {"success": False, "error": f"Item not cleaned yet (status: {item.clean_status})"}
            
            # 检查是否已入素材库
            if item.material_status == "in_material":
                existing = self.db.query(MvpMaterialItem).filter(
                    MvpMaterialItem.inbox_item_id == inbox_item_id
                ).first()
                if existing:
                    return {
                        "success": True,
                        "material_id": existing.id,
                        "inbox_item_id": inbox_item_id,
                        "message": "Already in material library"
                    }
            
            # 2. 如果 quality_status == 'pending'，先触发质量筛选
            if item.quality_status == "pending" and self.extraction:
                try:
                    await self.screening.screen_item(inbox_item_id)
                    self.db.refresh(item)
                except Exception as e:
                    logger.warning(f"Quality screening failed (non-blocking): {e}")
            
            # 3. 创建 MvpMaterialItem
            material = MvpMaterialItem(
                platform=item.platform,
                title=item.title,
                content=item.content,
                source_url=item.source_url or item.url,
                like_count=item.like_count or 0,
                comment_count=item.comment_count or 0,
                author=item.author or item.author_name,
                is_hot=getattr(item, 'quality_score', 0) >= 70,
                risk_level=item.risk_level or "low",
                inbox_item_id=item.id,
                quality_score=item.quality_score,
                risk_score=item.risk_score,
            )
            
            # 4. 运行 Ollama 结构化抽取
            if self.extraction:
                try:
                    extraction = await self.extraction.extract_structured(
                        item.content or "", item.platform or ""
                    )
                    # 填充 tags_json/topic/persona
                    tags = {
                        "audience": extraction.get("audience"),
                        "scene": extraction.get("scene"),
                        "style": extraction.get("style"),
                        "content_type": extraction.get("content_type"),
                    }
                    material.tags_json = json.dumps(tags, ensure_ascii=False)
                    material.topic = extraction.get("topic")
                    material.persona = extraction.get("audience")
                except Exception as e:
                    logger.warning(f"Extraction failed (non-blocking): {e}")
            
            self.db.add(material)
            
            # 5. 更新 inbox item 的 material_status
            item.material_status = "in_material"
            
            self.db.commit()
            self.db.refresh(material)
            
            return {
                "success": True,
                "material_id": material.id,
                "inbox_item_id": inbox_item_id
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"promote_to_material failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def build_knowledge(self, material_id: int) -> dict:
        """素材库→知识库
        
        流程:
        1. 读取 MvpMaterialItem
        2. 创建 MvpKnowledgeItem（带结构化字段）
        3. 对内容分块（按段落，每块不超过500字）
        4. 每个 chunk 生成 embedding
        5. 创建 MvpKnowledgeChunk 记录
        
        Args:
            material_id: 素材ID
        
        Returns:
            {success: bool, knowledge_id: int, chunk_count: int, error: str}
        """
        try:
            # 1. 读取素材
            material = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if not material:
                return {"success": False, "error": "Material not found"}
            
            # 检查是否已有知识条目
            existing = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.source_material_id == material_id
            ).first()
            if existing:
                return {
                    "success": True,
                    "knowledge_id": existing.id,
                    "chunk_count": 0,
                    "message": "Knowledge already exists"
                }
            
            # 2. 创建 MvpKnowledgeItem
            knowledge = MvpKnowledgeItem(
                title=material.title,
                content=material.content,
                platform=material.platform,
                source_material_id=material_id,
                source_url=material.source_url,
                author=material.author,
                like_count=material.like_count,
                comment_count=material.comment_count,
            )
            
            # 尝试从 tags_json 解析结构化字段
            if material.tags_json:
                try:
                    tags = json.loads(material.tags_json) if isinstance(material.tags_json, str) else material.tags_json
                    knowledge.audience = tags.get("audience")
                    knowledge.style = tags.get("style")
                except Exception:
                    pass
            
            knowledge.topic = material.topic
            knowledge.persona = material.persona
            
            self.db.add(knowledge)
            self.db.flush()  # 获取 knowledge.id
            
            # 3. 内容分块（按段落，每块不超过500字）
            content = material.content or ""
            chunks = self._split_content(content, max_chunk_size=500)
            
            # 4. 为每个 chunk 生成 embedding 并创建记录
            chunk_count = 0
            for idx, chunk_text in enumerate(chunks):
                if not chunk_text.strip():
                    continue
                
                chunk = MvpKnowledgeChunk(
                    knowledge_id=knowledge.id,
                    chunk_type="paragraph",
                    chunk_index=idx,
                    content=chunk_text,
                    token_count=len(chunk_text),
                )
                
                # 生成 embedding
                try:
                    embedding = await self.embedding.generate_embedding(chunk_text)
                    if embedding:
                        # 直接写入 List[float] 到 Vector 列
                        chunk.embedding = embedding
                except Exception as e:
                    logger.warning(f"Embedding generation failed for chunk {idx}: {e}")
                
                self.db.add(chunk)
                chunk_count += 1
            
            self.db.commit()
            self.db.refresh(knowledge)
            
            return {
                "success": True,
                "knowledge_id": knowledge.id,
                "chunk_count": chunk_count
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"build_knowledge failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def batch_promote_to_material(self, item_ids: List[int]) -> dict:
        """批量入素材库
        
        Args:
            item_ids: 收件箱条目ID列表
        
        Returns:
            {total: int, success: int, failed: int, details: list}
        """
        results = {
            "total": len(item_ids),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for item_id in item_ids:
            try:
                result = await self.promote_to_material(item_id)
                if result.get("success"):
                    results["success"] += 1
                else:
                    results["failed"] += 1
                results["details"].append({
                    "item_id": item_id,
                    "success": result.get("success", False),
                    "material_id": result.get("material_id"),
                    "error": result.get("error")
                })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "item_id": item_id,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def batch_ignore(self, item_ids: List[int]) -> dict:
        """批量忽略 - 更新 material_status='ignored'
        
        Args:
            item_ids: 收件箱条目ID列表
        
        Returns:
            {total: int, success: int, failed: int}
        """
        results = {
            "total": len(item_ids),
            "success": 0,
            "failed": 0
        }
        
        for item_id in item_ids:
            try:
                item = self.db.query(MvpInboxItem).filter(MvpInboxItem.id == item_id).first()
                if item:
                    item.material_status = "ignored"
                    results["success"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                logger.error(f"batch_ignore failed for item {item_id}: {e}")
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"batch_ignore commit failed: {e}")
        
        return results
    
    async def full_pipeline(self, raw_data: dict) -> dict:
        """完整链路：采集→清洗→筛选→入素材→入知识库（一键自动）
        
        Args:
            raw_data: 采集数据
        
        Returns:
            {
                success: bool,
                item_id: int,
                material_id: int,
                knowledge_id: int,
                error: str
            }
        """
        try:
            # 1. 采集入收件箱 + 清洗
            ingest_result = await self.ingest_from_collector(raw_data)
            if not ingest_result.get("success"):
                return ingest_result
            
            item_id = ingest_result["item_id"]
            
            # 2. 质量筛选（如果清洗成功）
            if ingest_result.get("clean_status") == "cleaned" and self.extraction:
                try:
                    await self.screening.screen_item(item_id)
                except Exception as e:
                    logger.warning(f"Quality screening failed (non-blocking): {e}")
            
            # 3. 入素材库
            material_result = await self.promote_to_material(item_id)
            if not material_result.get("success"):
                return {
                    "success": True,
                    "item_id": item_id,
                    "material_id": None,
                    "knowledge_id": None,
                    "message": "Ingested to inbox but failed to promote to material",
                    "error": material_result.get("error")
                }
            
            material_id = material_result["material_id"]
            
            # 4. 入知识库
            knowledge_result = await self.build_knowledge(material_id)
            
            return {
                "success": True,
                "item_id": item_id,
                "material_id": material_id,
                "knowledge_id": knowledge_result.get("knowledge_id"),
                "chunk_count": knowledge_result.get("chunk_count", 0)
            }
        except Exception as e:
            logger.error(f"full_pipeline failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _split_content(self, content: str, max_chunk_size: int = 500) -> List[str]:
        """内容分块
        
        按段落分割，每块不超过 max_chunk_size 字符
        """
        if not content:
            return []
        
        # 按段落分割
        paragraphs = content.split('\n\n')
        if len(paragraphs) == 1:
            paragraphs = content.split('\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前块加上新段落不超过限制，则合并
            if len(current_chunk) + len(para) + 1 <= max_chunk_size:
                current_chunk = f"{current_chunk}\n{para}".strip()
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果段落本身超过限制，需要切分
                if len(para) > max_chunk_size:
                    for i in range(0, len(para), max_chunk_size):
                        chunks.append(para[i:i + max_chunk_size])
                    current_chunk = ""
                else:
                    current_chunk = para
        
        # 保存最后一块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
