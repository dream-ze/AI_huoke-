"""
爆款内容采集分析中心 – API 端点

POST   /api/insight/topics               新建主题
GET    /api/insight/topics               主题列表
GET    /api/insight/topics/{id}          主题详情

POST   /api/insight/import               单条内容导入
POST   /api/insight/import/batch         批量导入（JSON数组）
GET    /api/insight/list                 内容列表（多维筛选）
GET    /api/insight/{id}                 内容详情
DELETE /api/insight/{id}                 删除内容

POST   /api/insight/analyze/{id}         AI深度分析单条内容
POST   /api/insight/analyze/batch        批量AI分析（队列）

GET    /api/insight/authors              账号档案列表
GET    /api/insight/authors/{id}         账号详情

POST   /api/insight/retrieve             检索召回（给生成模块）
GET    /api/insight/stats                统计数据
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import DistributedRateLimiter
from app.core.security import verify_token
from app.models.models import InsightAuthorProfile, InsightContentItem
from app.schemas.schemas import (
    InsightAnalyzeResponse,
    InsightAnalyzeBatchTaskResponse,
    InsightAuthorResponse,
    InsightBatchImport,
    InsightContentImport,
    InsightContentResponse,
    InsightRetrieveRequest,
    InsightRetrieveResponse,
    InsightTopicCreate,
    InsightTopicResponse,
)
from app.models import InsightCollectTask
from app.domains.ai_workbench.ai_service import AIService
from app.services.insight_service import InsightService

router = APIRouter(prefix="/api/insight", tags=["insight"])

insight_batch_limiter = DistributedRateLimiter(
    limit=settings.INSIGHT_BATCH_ANALYZE_RATE_LIMIT_PER_MINUTE,
    window_seconds=settings.INSIGHT_BATCH_ANALYZE_RATE_LIMIT_WINDOW_SECONDS,
    use_redis=settings.USE_REDIS_RATE_LIMIT,
    redis_url=settings.REDIS_URL,
    key_prefix=settings.RATE_LIMIT_KEY_PREFIX,
)


# ─────────────────────────────────────────────
# 主题管理
# ─────────────────────────────────────────────

@router.post("/topics", response_model=InsightTopicResponse)
def create_topic(
    req: InsightTopicCreate,
    _: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    topic = InsightService.create_topic(
        db,
        name=req.name,
        description=req.description,
        platform_focus=req.platform_focus,
        audience_tags=req.audience_tags,
        risk_notes=req.risk_notes,
    )
    return topic


@router.get("/topics", response_model=List[InsightTopicResponse])
def list_topics(
    _: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InsightService.list_topics(db)


@router.get("/topics/{topic_id}", response_model=InsightTopicResponse)
def get_topic(
    topic_id: int,
    _: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    topic = InsightService.get_topic(db, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="主题不存在")
    return topic


# ─────────────────────────────────────────────
# 内容导入
# ─────────────────────────────────────────────

@router.post("/import", response_model=InsightContentResponse)
def import_single(
    req: InsightContentImport,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """单条内容导入（手动录入 / 链接解析后提交 / 插件上传）"""
    item = InsightService.ingest_item(
        db,
        owner_id=current_user["user_id"],
        platform=req.platform,
        title=req.title,
        body_text=req.body_text,
        source_url=req.source_url,
        content_type=req.content_type,
        author_name=req.author_name,
        author_profile_url=req.author_profile_url,
        fans_count=req.fans_count,
        account_positioning=req.account_positioning,
        publish_time=req.publish_time,
        like_count=req.like_count,
        comment_count=req.comment_count,
        share_count=req.share_count,
        collect_count=req.collect_count,
        view_count=req.view_count,
        topic_name=req.topic_name,
        audience_tags=req.audience_tags,
        manual_note=req.manual_note,
        source_type=req.source_type,
        raw_payload=req.raw_payload,
    )
    return item


@router.post("/import/batch")
def import_batch(
    req: InsightBatchImport,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """批量导入（最多200条）"""
    items_data = [item.model_dump() for item in req.items]
    # topic_name 和 model 字段名一致，直接透传
    ok, skipped = InsightService.batch_ingest(
        db,
        owner_id=current_user["user_id"],
        items_data=items_data,
    )
    return {"imported": ok, "skipped": skipped, "total": len(req.items)}


# ─────────────────────────────────────────────
# 内容列表 / 详情 / 删除
# ─────────────────────────────────────────────

@router.get("/list", response_model=List[InsightContentResponse])
def list_items(
    platform: Optional[str] = Query(None),
    topic_id: Optional[int] = Query(None),
    is_hot: Optional[bool] = Query(None),
    heat_tier: Optional[str] = Query(None),
    ai_analyzed: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InsightService.list_items(
        db,
        owner_id=current_user["user_id"],
        platform=platform,
        topic_id=topic_id,
        is_hot=is_hot,
        heat_tier=heat_tier,
        ai_analyzed=ai_analyzed,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/{item_id}", response_model=InsightContentResponse)
def get_item(
    item_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    item = InsightService.get_item(db, item_id, current_user["user_id"])
    if not item:
        raise HTTPException(status_code=404, detail="内容不存在")
    return item


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    ok = InsightService.delete_item(db, item_id, current_user["user_id"])
    if not ok:
        raise HTTPException(status_code=404, detail="内容不存在")
    return {"deleted": True}


# ─────────────────────────────────────────────
# AI 分析
# ─────────────────────────────────────────────

@router.post("/analyze/{item_id}", response_model=InsightAnalyzeResponse)
async def analyze_item(
    item_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """AI深度分析单条内容：拆结构/识钩子/判热度/关联主题/更新知识库"""
    item = InsightService.get_item(db, item_id, current_user["user_id"])
    if not item:
        raise HTTPException(status_code=404, detail="内容不存在")

    ai_service = AIService(db=db)
    result = await InsightService.analyze_with_ai(
        db, item, ai_service, user_id=current_user["user_id"]
    )
    return result


@router.post("/analyze/batch")
async def analyze_batch(
    item_ids: List[int],
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """批量AI分析（异步后台）– 最多50条"""
    await insight_batch_limiter.check(f"insight_batch:{current_user['user_id']}")

    if len(item_ids) > 50:
        raise HTTPException(status_code=400, detail="单次最多批量分析50条")

    # 验证所有权
    items = (
        db.query(InsightContentItem)
        .filter(
            InsightContentItem.id.in_(item_ids),
            InsightContentItem.owner_id == current_user["user_id"],
        )
        .all()
    )
    found_ids = [i.id for i in items]
    not_found = [x for x in item_ids if x not in found_ids]

    task = InsightCollectTask(
        owner_id=current_user["user_id"],
        platform="mixed",
        collect_mode="analyze_batch",
        target_value=",".join(str(i) for i in found_ids[:100]),
        status="running",
        result_count=0,
        notes=f"queued={len(found_ids)}, not_found={len(not_found)}",
        run_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    async def _run_batch():
        ai_service = AIService(db=db)
        ok_count = 0
        fail_count = 0
        for item in items:
            try:
                await InsightService.analyze_with_ai(
                    db, item, ai_service, user_id=current_user["user_id"]
                )
                ok_count += 1
            except Exception:
                fail_count += 1  # 单条失败不中断批量

        task.status = "done" if fail_count == 0 else "failed"
        task.result_count = ok_count
        task.notes = f"ok={ok_count}, failed={fail_count}, queued={len(found_ids)}"
        db.commit()
        return {"ok": ok_count, "failed": fail_count, "task_id": task.id}

    background_tasks.add_task(_run_batch)
    return {
        "task_id": task.id,
        "queued": len(found_ids),
        "not_found": not_found,
        "rate_limit": {
            "limit": settings.INSIGHT_BATCH_ANALYZE_RATE_LIMIT_PER_MINUTE,
            "window_seconds": settings.INSIGHT_BATCH_ANALYZE_RATE_LIMIT_WINDOW_SECONDS,
        },
        "message": f"已将 {len(found_ids)} 条加入后台分析队列",
    }


@router.get("/analyze/tasks", response_model=List[InsightAnalyzeBatchTaskResponse])
def list_analyze_batch_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return (
        db.query(InsightCollectTask)
        .filter(
            InsightCollectTask.owner_id == current_user["user_id"],
            InsightCollectTask.collect_mode == "analyze_batch",
        )
        .order_by(InsightCollectTask.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/analyze/tasks/{task_id}", response_model=InsightAnalyzeBatchTaskResponse)
def get_analyze_batch_task(
    task_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    task = (
        db.query(InsightCollectTask)
        .filter(
            InsightCollectTask.id == task_id,
            InsightCollectTask.owner_id == current_user["user_id"],
            InsightCollectTask.collect_mode == "analyze_batch",
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Analyze batch task not found")
    return task


# ─────────────────────────────────────────────
# 账号档案
# ─────────────────────────────────────────────

@router.get("/authors", response_model=List[InsightAuthorResponse])
def list_authors(
    platform: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    _: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    q = db.query(InsightAuthorProfile)
    if platform:
        q = q.filter(InsightAuthorProfile.platform == platform)
    return q.order_by(InsightAuthorProfile.viral_rate.desc()).offset(skip).limit(limit).all()


@router.get("/authors/{author_id}", response_model=InsightAuthorResponse)
def get_author(
    author_id: int,
    _: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    author = db.query(InsightAuthorProfile).filter(InsightAuthorProfile.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="账号档案不存在")
    return author


# ─────────────────────────────────────────────
# 检索召回
# ─────────────────────────────────────────────

@router.post("/retrieve", response_model=InsightRetrieveResponse)
def retrieve_for_generation(
    req: InsightRetrieveRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    给文案生成模块提供结构化参考特征。
    只返回分析结论（标题公式/痛点/结构/风格），不返回原文。
    """
    result = InsightService.retrieve_for_generation(
        db,
        owner_id=current_user["user_id"],
        platform=req.platform,
        topic_name=req.topic_name,
        audience_tags=req.audience_tags,
        limit=req.limit,
    )
    return result


# ─────────────────────────────────────────────
# 统计
# ─────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return InsightService.get_stats(db, current_user["user_id"])
