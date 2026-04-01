"""AI异步任务模块 - 处理LLM调用、批量生成、合规检查等耗时AI操作"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def async_generate_content(self, generation_task_id: int, user_id: int):
    """异步执行内容生成任务

    Args:
        generation_task_id: 生成任务ID
        user_id: 用户ID

    Returns:
        dict: 包含状态和任务ID的结果
    """
    from app.core.database import SessionLocal
    from app.services.mvp_generate_service import MvpGenerateService

    logger.info(f"开始异步生成任务: task_id={generation_task_id}, user_id={user_id}")
    db = SessionLocal()
    try:
        service = MvpGenerateService(db)
        # 调用实际生成逻辑 - 获取任务参数并执行
        from app.models.models import GenerationTask as GenTask

        task = db.query(GenTask).filter(GenTask.id == generation_task_id).first()
        if not task:
            logger.error(f"生成任务不存在: task_id={generation_task_id}")
            return {"status": "error", "reason": "task_not_found"}

        result = service.generate_multi_version(
            source_type=getattr(task, "source_type", "manual"),
            source_id=getattr(task, "source_id", None),
            manual_text=getattr(task, "manual_text", None),
            target_platform=getattr(task, "target_platform", "xiaohongshu"),
            audience=getattr(task, "audience", ""),
            style=getattr(task, "style", ""),
            enable_knowledge=getattr(task, "enable_knowledge", False),
            enable_rewrite=getattr(task, "enable_rewrite", False),
            version_count=getattr(task, "version_count", 3),
            extra_requirements=getattr(task, "extra_requirements", ""),
        )

        logger.info(f"生成任务完成: task_id={generation_task_id}")
        return {"status": "success", "task_id": generation_task_id, "result": result}
    except Exception as exc:
        logger.error(f"生成任务失败: task_id={generation_task_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def async_compliance_check(self, content_id: int, content_text: str = None):
    """异步执行合规检查

    Args:
        content_id: 内容ID
        content_text: 待检查的文本内容（可选，如果不提供则从数据库读取）

    Returns:
        dict: 包含状态、内容ID和合规检查结果
    """
    from app.core.database import SessionLocal
    from app.services.mvp_compliance_service import MvpComplianceService

    logger.info(f"开始合规检查: content_id={content_id}")
    db = SessionLocal()
    try:
        service = MvpComplianceService(db)

        # 如果没有提供文本，从数据库读取
        if not content_text:
            from app.models.models import MvpGenerationResult

            result = db.query(MvpGenerationResult).filter(MvpGenerationResult.id == content_id).first()
            if not result:
                logger.error(f"内容不存在: content_id={content_id}")
                return {"status": "error", "reason": "content_not_found"}
            content_text = result.output_text

        # 执行合规检查
        compliance_result = service.check(content_text)

        # 更新内容的合规状态
        from app.models.models import MvpGenerationResult

        db.query(MvpGenerationResult).filter(MvpGenerationResult.id == content_id).update(
            {"compliance_status": compliance_result.get("status", "unknown")}
        )
        db.commit()

        logger.info(f"合规检查完成: content_id={content_id}, status={compliance_result.get('status')}")
        return {"status": "success", "content_id": content_id, "compliance": compliance_result}
    except Exception as exc:
        logger.error(f"合规检查失败: content_id={content_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def async_batch_generate(self, task_ids: list, user_id: int):
    """批量异步生成

    将多个生成任务分发到队列中执行

    Args:
        task_ids: 任务ID列表
        user_id: 用户ID

    Returns:
        list: 每个任务的分发结果
    """
    logger.info(f"开始批量生成: {len(task_ids)}个任务, user_id={user_id}")
    results = []

    for task_id in task_ids:
        try:
            # 分发单个生成任务到队列
            async_generate_content.delay(task_id, user_id)
            results.append({"task_id": task_id, "dispatched": True})
            logger.debug(f"任务已分发: task_id={task_id}")
        except Exception as e:
            logger.error(f"任务分发失败: task_id={task_id}, error={e}")
            results.append({"task_id": task_id, "dispatched": False, "error": str(e)})

    success_count = sum(1 for r in results if r["dispatched"])
    logger.info(f"批量生成分发完成: 成功{success_count}/{len(task_ids)}")
    return results


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=20,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def async_tag_identification(self, content_id: int, content_text: str):
    """异步执行标签识别

    Args:
        content_id: 内容ID
        content_text: 待识别标签的文本内容

    Returns:
        dict: 包含状态和识别出的标签
    """
    from app.core.database import SessionLocal
    from app.services.mvp_tag_service import MvpTagService

    logger.info(f"开始标签识别: content_id={content_id}")
    db = SessionLocal()
    try:
        service = MvpTagService(db)
        tags = service.identify_tags(content_text)

        logger.info(f"标签识别完成: content_id={content_id}, tags={tags}")
        return {"status": "success", "content_id": content_id, "tags": tags}
    except Exception as exc:
        logger.error(f"标签识别失败: content_id={content_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def async_hot_rewrite(self, material_id: int, style: str = "professional"):
    """异步执行爆文改写

    Args:
        material_id: 素材ID
        style: 改写风格

    Returns:
        dict: 包含状态和改写结果
    """
    from app.core.database import SessionLocal
    from app.services.mvp_rewrite_service import MvpRewriteService

    logger.info(f"开始爆文改写: material_id={material_id}, style={style}")
    db = SessionLocal()
    try:
        # 获取素材内容
        from app.models.models import MvpMaterialItem

        material = db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()

        if not material:
            logger.error(f"素材不存在: material_id={material_id}")
            return {"status": "error", "reason": "material_not_found"}

        service = MvpRewriteService(db)
        result = service.rewrite_hot(material.content, style=style)

        logger.info(f"爆文改写完成: material_id={material_id}")
        return {"status": "success", "material_id": material_id, "result": result}
    except Exception as exc:
        logger.error(f"爆文改写失败: material_id={material_id}, error={exc}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def async_full_pipeline(self, request_data: dict, user_id: int):
    """异步执行完整生成流水线

    包含：标签识别 → 知识检索 → 多版本生成 → 合规审核

    Args:
        request_data: 完整流水线请求参数
        user_id: 用户ID

    Returns:
        dict: 包含完整流水线执行结果
    """
    from app.core.database import SessionLocal
    from app.services.mvp_generate_service import MvpGenerateService

    logger.info(f"开始完整流水线生成: user_id={user_id}")
    db = SessionLocal()
    try:
        service = MvpGenerateService(db)

        # 调用完整流水线生成
        result = service.generate_full_pipeline(request_data)

        logger.info(f"完整流水线生成完成: user_id={user_id}")
        return {"status": "success", "user_id": user_id, "result": result}
    except Exception as exc:
        logger.error(f"完整流水线生成失败: user_id={user_id}, error={exc}")
        raise
    finally:
        db.close()
