"""素材异步任务模块 - 素材入库、知识库同步、向量化等后台处理"""

import logging
from typing import List, Optional

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def async_process_material(self, material_id: int):
    """异步执行素材处理流水线

    处理流程：
    1. 读取素材内容
    2. 执行内容清洗
    3. 执行质量评估
    4. 更新素材状态

    Args:
        material_id: 素材ID

    Returns:
        dict: 处理结果
    """
    from app.core.database import SessionLocal

    logger.info(f"开始素材处理流水线: material_id={material_id}")
    db = SessionLocal()
    try:
        from app.models.models import MvpMaterialItem
        from app.services.cleaning_service import CleaningService
        from app.services.quality_screening_service import QualityScreeningService

        # 获取素材
        material = db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()

        if not material:
            logger.error(f"素材不存在: material_id={material_id}")
            return {"status": "error", "reason": "material_not_found"}

        # 内容清洗
        cleaning_service = CleaningService(db)
        cleaned_content = cleaning_service.clean_content(material.content)

        # 质量评估
        quality_service = QualityScreeningService(db)
        quality_result = quality_service.evaluate(material.content)

        # 更新素材
        material.quality_score = quality_result.get("score", 0)
        if hasattr(material, "quality_score"):
            material.quality_score = quality_result.get("score", 0)
        if hasattr(material, "risk_score"):
            material.risk_score = quality_result.get("risk_score", 0)

        db.commit()

        logger.info(f"素材处理完成: material_id={material_id}, quality={quality_result.get('score')}")
        return {
            "status": "success",
            "material_id": material_id,
            "quality_score": quality_result.get("score"),
            "cleaned_length": len(cleaned_content),
        }
    except Exception as exc:
        logger.error(f"素材处理失败: material_id={material_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=20,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def async_sync_to_knowledge(self, material_ids: List[int]):
    """异步批量同步素材到知识库

    将素材内容转换为知识库条目，支持向量化检索

    Args:
        material_ids: 素材ID列表

    Returns:
        dict: 同步结果统计
    """
    from app.core.database import SessionLocal

    logger.info(f"开始批量同步知识库: {len(material_ids)}个素材")
    db = SessionLocal()
    try:
        from app.models.models import MvpMaterialItem
        from app.services.pipeline_service import PipelineService

        pipeline_service = PipelineService(db)
        results = {"total": len(material_ids), "success": 0, "skipped": 0, "failed": 0, "details": []}

        for material_id in material_ids:
            try:
                # 检查素材是否存在
                material = db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()

                if not material:
                    results["failed"] += 1
                    results["details"].append({"material_id": material_id, "status": "failed", "reason": "not_found"})
                    continue

                # 执行知识库构建
                sync_result = pipeline_service.build_knowledge(material_id)

                if sync_result.get("success"):
                    results["success"] += 1
                    results["details"].append(
                        {
                            "material_id": material_id,
                            "status": "success",
                            "knowledge_id": sync_result.get("knowledge_id"),
                            "chunk_count": sync_result.get("chunk_count", 0),
                        }
                    )
                elif sync_result.get("message") == "Knowledge already exists":
                    results["skipped"] += 1
                    results["details"].append(
                        {"material_id": material_id, "status": "skipped", "reason": "already_exists"}
                    )
                else:
                    results["failed"] += 1
                    results["details"].append(
                        {"material_id": material_id, "status": "failed", "reason": sync_result.get("error", "unknown")}
                    )

            except Exception as e:
                logger.error(f"素材同步失败: material_id={material_id}, error={e}")
                results["failed"] += 1
                results["details"].append({"material_id": material_id, "status": "failed", "reason": str(e)})

        logger.info(f"知识库同步完成: 成功{results['success']}, 跳过{results['skipped']}, 失败{results['failed']}")
        return results
    except Exception as exc:
        logger.error(f"批量知识库同步失败: error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def async_vectorize_knowledge(self, knowledge_item_id: int):
    """异步执行知识条目向量化

    对知识库条目进行分块、向量化并存储

    Args:
        knowledge_item_id: 知识条目ID

    Returns:
        dict: 向量化结果
    """
    from app.core.database import SessionLocal

    logger.info(f"开始知识条目向量化: knowledge_item_id={knowledge_item_id}")
    db = SessionLocal()
    try:
        from app.models.models import MvpKnowledgeChunk, MvpKnowledgeItem
        from app.services.embedding_service import EmbeddingService

        # 获取知识条目
        knowledge = db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id == knowledge_item_id).first()

        if not knowledge:
            logger.error(f"知识条目不存在: knowledge_item_id={knowledge_item_id}")
            return {"status": "error", "reason": "knowledge_not_found"}

        # 执行向量化
        embedding_service = EmbeddingService(db)

        # 对内容分块
        content = knowledge.content
        chunk_size = 500  # 每块最大字符数
        chunks = []

        # 简单分块策略：按段落分割
        paragraphs = content.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # 为每个块生成embedding并存储
        chunk_records = []
        for i, chunk_text in enumerate(chunks):
            try:
                embedding = embedding_service.get_embedding(chunk_text)

                chunk_record = MvpKnowledgeChunk(
                    knowledge_item_id=knowledge_item_id,
                    chunk_index=i,
                    content=chunk_text,
                    embedding=str(embedding) if embedding else None,
                )
                db.add(chunk_record)
                chunk_records.append(chunk_record)
            except Exception as e:
                logger.warning(f"块向量化失败: knowledge_id={knowledge_item_id}, chunk={i}, error={e}")

        db.commit()

        logger.info(f"知识条目向量化完成: knowledge_id={knowledge_item_id}, chunks={len(chunk_records)}")
        return {"status": "success", "knowledge_item_id": knowledge_item_id, "chunk_count": len(chunk_records)}
    except Exception as exc:
        logger.error(f"知识条目向量化失败: knowledge_item_id={knowledge_item_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,
)
def async_batch_vectorize(self, knowledge_ids: List[int]):
    """批量异步向量化知识条目

    Args:
        knowledge_ids: 知识条目ID列表

    Returns:
        dict: 批量处理结果
    """
    logger.info(f"开始批量向量化: {len(knowledge_ids)}个知识条目")
    results = {"total": len(knowledge_ids), "success": 0, "failed": 0, "total_chunks": 0}

    for kid in knowledge_ids:
        try:
            result = async_vectorize_knowledge.delay(kid)
            results["success"] += 1
            if result.get("chunk_count"):
                results["total_chunks"] += result["chunk_count"]
        except Exception as e:
            logger.error(f"分发向量化任务失败: knowledge_id={kid}, error={e}")
            results["failed"] += 1

    logger.info(f"批量向量化分发完成: 成功{results['success']}, 失败{results['failed']}")
    return results


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def async_ingest_raw_content(
    self,
    owner_id: int,
    platform: str,
    title: Optional[str],
    content_text: str,
    source_url: Optional[str] = None,
    author_name: Optional[str] = None,
):
    """异步入库原始内容

    将原始内容入库到素材库

    Args:
        owner_id: 所有者用户ID
        platform: 平台标识
        title: 标题
        content_text: 内容文本
        source_url: 来源URL
        author_name: 作者名称

    Returns:
        dict: 入库结果
    """
    from app.core.database import SessionLocal

    logger.info(f"开始异步入库: owner_id={owner_id}, platform={platform}")
    db = SessionLocal()
    try:
        from app.collector.services.pipeline import AcquisitionIntakeService

        # 使用采集入库服务
        result = AcquisitionIntakeService.ingest_item(
            db=db,
            owner_id=owner_id,
            source_channel="async_task",
            raw_item={
                "platform": platform,
                "title": title,
                "content_text": content_text,
                "source_url": source_url,
                "author_name": author_name,
            },
        )

        logger.info(f"入库完成: material_id={result.get('material_id')}")
        return {
            "status": "success",
            "material_id": result.get("material_id"),
            "inbox_item_id": result.get("inbox_item_id"),
        }
    except Exception as exc:
        logger.error(f"入库失败: owner_id={owner_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def async_process_inbox_items(self, inbox_item_ids: List[int], owner_id: int):
    """异步批量处理收件箱项目

    将收件箱项目批量处理为素材

    Args:
        inbox_item_ids: 收件箱项目ID列表
        owner_id: 所有者用户ID

    Returns:
        dict: 处理结果统计
    """
    from app.core.database import SessionLocal

    logger.info(f"开始批量处理收件箱: {len(inbox_item_ids)}个项目")
    db = SessionLocal()
    try:
        from app.services.mvp_inbox_service import MvpInboxService

        inbox_service = MvpInboxService(db)
        results = {"total": len(inbox_item_ids), "success": 0, "failed": 0, "material_ids": []}

        for item_id in inbox_item_ids:
            try:
                # 批准入库
                result = inbox_service.approve_to_material(item_id, owner_id)
                if result.get("material_id"):
                    results["success"] += 1
                    results["material_ids"].append(result["material_id"])
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"收件箱项目处理失败: item_id={item_id}, error={e}")
                results["failed"] += 1

        logger.info(f"收件箱批量处理完成: 成功{results['success']}, 失败{results['failed']}")
        return results
    except Exception as exc:
        logger.error(f"批量收件箱处理失败: error={exc}")
        raise
    finally:
        db.close()
