"""MVP API路由 - 收件箱/素材库/知识库/AI工作台/合规审核"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.mvp_schemas import (
    MaterialCreateRequest,
    UpdateTagsRequest,
    KnowledgeBuildRequest,
    KnowledgeSearchRequest,
    GenerateRequest,
    ComplianceCheckRequest,
    TagCreateRequest,
    DashboardStatsResponse,
    AutoPipelineRequest,
    AutoPipelineResponse,
    AutoPipelineBatchRequest,
    AutoPipelineBatchResponse,
    BatchIdsRequest,
    IngestRequest,
    ComplianceRuleRequest,
    ComplianceTestRequest,
    FeedbackSubmitRequest,
    FeedbackResponse,
    FeedbackStatsResponse,
    KnowledgeQualityRankingResponse,
    LearningSuggestionsResponse,
    WeightAdjustmentResult,
    # 知识图谱相关 Schema
    KnowledgeGraphResponse,
    GraphStatsResponse,
    TopicClusterResponse,
    EnhancedSearchResult,
    BuildRelationsResponse,
    BatchBuildRelationsResponse,
    # 批量入知识库 Schema
    BatchBuildKnowledgeRequest,
    BatchBuildKnowledgeResponse,
)
from app.core.config import settings
from app.services.pipeline_service import PipelineService
from app.schemas.generate_schema import FullPipelineRequest
from app.services.mvp_inbox_service import MvpInboxService
from app.services.mvp_material_service import MvpMaterialService
from app.services.mvp_tag_service import MvpTagService
from app.services.mvp_knowledge_service import MvpKnowledgeService
from app.services.mvp_generate_service import MvpGenerateService
from app.services.mvp_rewrite_service import MvpRewriteService
from app.services.mvp_compliance_service import MvpComplianceService
from app.services.cleaning_service import CleaningService
from app.services.extraction_service import ExtractionService
from app.services.quality_screening_service import QualityScreeningService
from app.services.feedback_service import FeedbackService
from app.services.embedding_service import get_embedding_service
from app.services.model_manager_service import get_model_manager_service

router = APIRouter(prefix="/api/mvp", tags=["MVP"])


# ── 收件箱 ──
@router.get("/inbox")
def list_inbox(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    platform: str = Query(None),
    source_type: str = Query(None),
    risk_level: str = Query(None),
    duplicate_status: str = Query(None),
    keyword: str = Query(None),
    clean_status: str = Query(None),
    quality_status: str = Query(None),
    risk_status: str = Query(None),
    material_status: str = Query(None),
    db: Session = Depends(get_db)
):
    """列出收件箱条目，支持筛选和分页"""
    svc = MvpInboxService(db)
    result = svc.list_inbox(
        page=page, size=size, status=status, platform=platform,
        source_type=source_type, risk_level=risk_level,
        duplicate_status=duplicate_status, keyword=keyword,
        clean_status=clean_status, quality_status=quality_status,
        risk_status=risk_status, material_status=material_status
    )
    # 序列化items - 包含所有新字段
    items_out = []
    for item in result.get("items", []):
        items_out.append({
            "id": item.id,
            "platform": item.platform,
            "source_id": item.source_id,
            "title": item.title,
            "content": item.content,
            "content_preview": item.content_preview,
            "author": item.author,
            "author_name": item.author_name,
            "source_url": item.source_url,
            "source_type": item.source_type,
            "keyword": item.keyword,
            "risk_level": item.risk_level,
            "duplicate_status": item.duplicate_status,
            "score": item.score,
            "quality_score": item.quality_score,
            "risk_score": item.risk_score,
            "tech_status": item.tech_status,
            "biz_status": item.biz_status,
            "clean_status": item.clean_status,
            "quality_status": item.quality_status,
            "risk_status": item.risk_status,
            "material_status": item.material_status,
            "like_count": item.like_count,
            "comment_count": item.comment_count,
            "favorite_count": item.favorite_count,
            "publish_time": str(item.publish_time) if item.publish_time else None,
            "cleaned_at": str(item.cleaned_at) if item.cleaned_at else None,
            "screened_at": str(item.screened_at) if item.screened_at else None,
            "created_at": str(item.created_at) if item.created_at else None,
            "updated_at": str(item.updated_at) if item.updated_at else None
        })
    return {
        "items": items_out,
        "total": result.get("total", 0),
        "page": result.get("page", page),
        "size": result.get("size", size)
    }


@router.get("/inbox/{item_id}")
def get_inbox_item(item_id: int, db: Session = Depends(get_db)):
    """获取单条收件箱条目"""
    svc = MvpInboxService(db)
    item = svc.get_item(item_id)
    if not item:
        raise HTTPException(404, "收件箱条目不存在")
    return {
        "id": item.id,
        "platform": item.platform,
        "title": item.title,
        "content": item.content,
        "author": item.author,
        "source_url": item.source_url,
        "source_type": item.source_type,
        "keyword": item.keyword,
        "risk_level": item.risk_level,
        "duplicate_status": item.duplicate_status,
        "score": item.score,
        "tech_status": item.tech_status,
        "biz_status": item.biz_status,
        "created_at": str(item.created_at) if item.created_at else None
    }


@router.post("/inbox/{item_id}/to-material")
async def inbox_to_material(item_id: int, db: Session = Depends(get_db)):
    """将收件箱条目入素材库（使用 PipelineService）"""
    service = PipelineService(db)
    result = await service.promote_to_material(item_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/inbox/{item_id}/mark-hot")
def inbox_mark_hot(item_id: int, db: Session = Depends(get_db)):
    """标记收件箱条目为爆款"""
    try:
        svc = MvpInboxService(db)
        item = svc.mark_hot(item_id)
        return {"message": "已标记爆款", "score": item.score}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/inbox/{item_id}/discard")
def inbox_discard(item_id: int, db: Session = Depends(get_db)):
    """丢弃收件箱条目"""
    try:
        svc = MvpInboxService(db)
        svc.discard(item_id)
        return {"message": "已废弃"}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/inbox/{item_id}/ignore")
async def ignore_inbox_item(item_id: int, db: Session = Depends(get_db)):
    """单条忽略 - 更新 material_status='ignored'"""
    from app.models.models import MvpInboxItem
    item = db.query(MvpInboxItem).filter(MvpInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.material_status = 'ignored'
    db.commit()
    return {"success": True, "item_id": item_id}


@router.post("/inbox/{item_id}/clean")
def clean_inbox_item(item_id: int, db: Session = Depends(get_db)):
    """单条收件箱条目清洗"""
    service = CleaningService(db)
    result = service.clean_item(item_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Clean failed"))
    return result


@router.post("/inbox/batch-clean")
def batch_clean_inbox(request: BatchIdsRequest, db: Session = Depends(get_db)):
    """批量清洗收件箱条目"""
    service = CleaningService(db)
    stats = service.batch_clean(request.ids)
    # 重命名 success -> success_count 避免与布尔 success 冲突
    return {
        "success": True,
        "total": stats["total"],
        "success_count": stats["success"],
        "failed_count": stats["failed"],
        "details": stats.get("details", [])
    }


@router.post("/inbox/{item_id}/screen")
async def screen_inbox_item(item_id: int, db: Session = Depends(get_db)):
    """单条质量筛选"""
    from app.core.config import settings
    extraction_svc = ExtractionService(
        ollama_base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL
    )
    service = QualityScreeningService(db, extraction_service=extraction_svc)
    result = await service.screen_item(item_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/inbox/batch-screen")
async def batch_screen_inbox(request: BatchIdsRequest, db: Session = Depends(get_db)):
    """批量质量筛选"""
    from app.core.config import settings
    extraction_svc = ExtractionService(
        ollama_base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL
    )
    service = QualityScreeningService(db, extraction_service=extraction_svc)
    stats = await service.batch_screen(request.ids)
    # 重命名 success -> success_count 避免与布尔 success 冲突
    return {
        "success": True,
        "total": stats["total"],
        "success_count": stats["success"],
        "failed_count": stats["failed"],
        "details": stats.get("details", [])
    }


@router.post("/inbox/ingest")
async def ingest_to_inbox(request: IngestRequest, db: Session = Depends(get_db)):
    """采集数据入收件箱（自动触发清洗）"""
    service = PipelineService(db)
    return await service.ingest_from_collector(request.model_dump())


@router.post("/inbox/batch-to-material")
async def batch_to_material(request: BatchIdsRequest, db: Session = Depends(get_db)):
    """批量入素材库"""
    service = PipelineService(db)
    stats = await service.batch_promote_to_material(request.ids)
    # 重命名 success -> success_count 避免与布尔 success 冲突
    return {
        "success": True,
        "total": stats["total"],
        "success_count": stats["success"],
        "failed_count": stats["failed"],
        "details": stats.get("details", [])
    }


@router.post("/inbox/batch-ignore")
async def batch_ignore_inbox(request: BatchIdsRequest, db: Session = Depends(get_db)):
    """批量忽略"""
    service = PipelineService(db)
    stats = await service.batch_ignore(request.ids)
    # 重命名 success -> success_count 避免与布尔 success 冲突
    return {
        "success": True,
        "total": stats["total"],
        "success_count": stats["success"],
        "failed_count": stats["failed"],
        "details": stats.get("details", [])
    }


# ── 素材库 ──
@router.get("/materials")
def list_materials(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    platform: str = Query(None),
    tag_id: int = Query(None),
    audience: str = Query(None),
    style: str = Query(None),
    is_hot: bool = Query(None),
    keyword: str = Query(None),
    db: Session = Depends(get_db)
):
    """列出素材列表，支持筛选和分页"""
    svc = MvpMaterialService(db)
    return svc.list_materials(
        page=page, size=size, platform=platform, tag_id=tag_id,
        audience=audience, style=style, is_hot=is_hot, keyword=keyword
    )


@router.get("/materials/{material_id}")
def get_material(material_id: int, db: Session = Depends(get_db)):
    """获取素材详情"""
    svc = MvpMaterialService(db)
    detail = svc.get_material(material_id)
    if not detail:
        raise HTTPException(404, "素材不存在")
    return detail


@router.post("/materials")
def create_material(req: MaterialCreateRequest, db: Session = Depends(get_db)):
    """创建素材"""
    svc = MvpMaterialService(db)
    material = svc.create_material(req.model_dump())
    return {"message": "创建成功", "id": material.id}


@router.post("/materials/{material_id}/build-knowledge")
def build_knowledge(material_id: int, db: Session = Depends(get_db)):
    """从素材构建知识"""
    try:
        svc = MvpKnowledgeService(db)
        knowledge = svc.build_from_material(material_id)
        return {"message": "知识构建成功", "knowledge_id": knowledge.id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/materials/batch-build-knowledge", response_model=BatchBuildKnowledgeResponse)
def batch_build_knowledge(req: BatchBuildKnowledgeRequest, db: Session = Depends(get_db)):
    """批量从素材构建知识
    
    复用单条 build_from_material 逻辑，单条失败不影响整批处理。
    返回每条素材的处理结果详情。
    """
    svc = MvpKnowledgeService(db)
    result = svc.batch_build_from_materials(req.material_ids)
    
    # 转换为 Pydantic 模型格式
    details = [
        {
            "material_id": d["material_id"],
            "success": d["success"],
            "knowledge_id": d["knowledge_id"],
            "error": d["error"]
        }
        for d in result["details"]
    ]
    
    return BatchBuildKnowledgeResponse(
        total=result["total"],
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        details=details
    )


@router.post("/materials/{material_id}/to-knowledge")
async def material_to_knowledge(material_id: int, db: Session = Depends(get_db)):
    """素材入知识库（使用 PipelineService，支持向量切分）"""
    service = PipelineService(db)
    result = await service.build_knowledge(material_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/materials/{material_id}/rewrite")
def rewrite_material(material_id: int, db: Session = Depends(get_db)):
    """爆款仿写"""
    try:
        svc = MvpRewriteService(db)
        result = svc.rewrite_hot(material_id)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/materials/{material_id}/toggle-hot")
def toggle_material_hot(material_id: int, db: Session = Depends(get_db)):
    """切换素材爆款状态"""
    try:
        svc = MvpMaterialService(db)
        item = svc.toggle_hot(material_id)
        return {"message": "爆款状态更新成功", "id": item.id, "is_hot": item.is_hot}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/materials/{material_id}/tags")
def update_material_tags(material_id: int, req: UpdateTagsRequest, db: Session = Depends(get_db)):
    """更新素材标签"""
    svc = MvpTagService(db)
    svc.update_material_tags(material_id, req.tag_ids)
    return {"message": "标签更新成功"}


# ── 知识库 ──

# 分库统计 - 必须在 /knowledge/{id} 之前注册
@router.get("/knowledge/library-stats")
def get_library_stats(db: Session = Depends(get_db)):
    """获取各分库统计（带最近更新时间）"""
    svc = MvpKnowledgeService(db)
    return svc.get_library_stats()


# 按分库列出 - 必须在 /knowledge/{id} 之前注册
@router.get("/knowledge/library/{library_type}")
def list_by_library(
    library_type: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = Query(""),
    db: Session = Depends(get_db)
):
    """按分库类型列出知识条目"""
    svc = MvpKnowledgeService(db)
    result = svc.list_by_library(library_type, page, size, keyword)
    # 序列化
    items_out = []
    for item in result["items"]:
        items_out.append({
            "id": item.id,
            "title": item.title,
            "content": item.content[:200] if item.content else "",
            "platform": item.platform,
            "audience": item.audience,
            "topic": item.topic,
            "content_type": item.content_type,
            "library_type": item.library_type,
            "like_count": item.like_count or 0,
            "comment_count": item.comment_count or 0,
            "created_at": str(item.created_at) if item.created_at else None,
        })
    return {"items": items_out, "total": result["total"], "page": page, "size": size}


@router.get("/knowledge")
def list_knowledge(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    platform: str = Query(None),
    audience: str = Query(None),
    style: str = Query(None),
    category: str = Query(None),
    topic: str = Query(None),
    content_type: str = Query(None),
    keyword: str = Query(None),
    library_type: str = Query(None),
    db: Session = Depends(get_db)
):
    """列出知识库条目"""
    svc = MvpKnowledgeService(db)
    result = svc.list_knowledge(
        page=page, size=size, platform=platform,
        audience=audience, style=style, category=category, 
        keyword=keyword, topic=topic, content_type=content_type,
        library_type=library_type
    )
    # 序列化items
    items_out = []
    for item in result.get("items", []):
        items_out.append({
            "id": item.id,
            "title": item.title,
            "content": item.content,
            "category": item.category,
            "platform": item.platform,
            "audience": item.audience,
            "style": item.style,
            "source_material_id": item.source_material_id,
            "use_count": item.use_count,
            "created_at": str(item.created_at) if item.created_at else None,
            "library_type": getattr(item, 'library_type', None),
            "layer": getattr(item, 'layer', None),
            "risk_level": getattr(item, 'risk_level', None),
            "summary": getattr(item, 'summary', None),
            "topic": getattr(item, 'topic', None),
            "content_type": getattr(item, 'content_type', None),
            "opening_type": getattr(item, 'opening_type', None),
            "hook_sentence": getattr(item, 'hook_sentence', None),
            "cta_style": getattr(item, 'cta_style', None),
            "is_hot": getattr(item, 'is_hot', False),
            "author": getattr(item, 'author', None),
        })
    return {
        "items": items_out,
        "total": result.get("total", 0),
        "page": result.get("page", page),
        "size": result.get("size", size)
    }



@router.get("/knowledge/libraries")
def get_knowledge_libraries(db: Session = Depends(get_db)):
    """获取各分库统计"""
    from sqlalchemy import func as sa_func
    from app.models.models import MvpKnowledgeItem
    
    LIBRARY_LABELS = {
        "hot_content": "爆款内容库",
        "industry_phrases": "行业话术库",
        "platform_rules": "平台规则库",
        "audience_profile": "人群画像库",
        "account_positioning": "账号定位库",
        "prompt_templates": "提示词库",
        "compliance_rules": "审核规则库",
    }
    
    results = (
        db.query(
            MvpKnowledgeItem.library_type,
            sa_func.count(MvpKnowledgeItem.id)
        )
        .group_by(MvpKnowledgeItem.library_type)
        .all()
    )
    
    libraries = []
    total = 0
    for lib_type, count in results:
        libraries.append({
            "library_type": lib_type or "industry_phrases",
            "label": LIBRARY_LABELS.get(lib_type, lib_type or "其他"),
            "count": count,
        })
        total += count
    
    # 补充空库
    seen = {l["library_type"] for l in libraries}
    for lt, label in LIBRARY_LABELS.items():
        if lt not in seen:
            libraries.append({"library_type": lt, "label": label, "count": 0})
    
    return {"libraries": libraries, "total": total}


@router.get("/knowledge/chunks/{knowledge_id}")
def get_knowledge_chunks(knowledge_id: int, db: Session = Depends(get_db)):
    """获取某条知识的切块列表"""
    from app.models.models import MvpKnowledgeChunk
    
    chunks = (
        db.query(MvpKnowledgeChunk)
        .filter(MvpKnowledgeChunk.knowledge_id == knowledge_id)
        .order_by(MvpKnowledgeChunk.chunk_index)
        .all()
    )
    
    result = []
    for c in chunks:
        result.append({
            "id": c.id,
            "knowledge_id": c.knowledge_id,
            "chunk_type": c.chunk_type,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "metadata_json": c.metadata_json,
            "has_embedding": bool(c.embedding),
            "token_count": c.token_count or 0,
            "created_at": str(c.created_at) if c.created_at else None,
        })
    
    return {"chunks": result, "total": len(result)}


@router.post("/knowledge/reindex")
async def reindex_knowledge(
    request: dict = None,
    db: Session = Depends(get_db)
):
    """重建知识切块和向量索引"""
    from app.models.models import MvpKnowledgeItem
    from app.services.chunking_service import get_chunking_service
    
    body = request or {}
    knowledge_ids = body.get("knowledge_ids", None)
    embedding_model = body.get("embedding_model", "volcano")
    
    chunking = get_chunking_service(db)
    
    if knowledge_ids:
        items = db.query(MvpKnowledgeItem).filter(
            MvpKnowledgeItem.id.in_(knowledge_ids)
        ).all()
    else:
        items = db.query(MvpKnowledgeItem).limit(500).all()
    
    total = len(items)
    success = 0
    failed = 0
    
    for item in items:
        try:
            result = await chunking.process_and_store_chunks(
                item.id, embedding_model=embedding_model
            )
            if result.get("success"):
                success += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
    
    return {
        "total_processed": total,
        "success_count": success,
        "failed_count": failed,
        "message": f"处理完成: {success}成功, {failed}失败"
    }


@router.get("/knowledge/{knowledge_id}")
def get_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    """获取知识条目详情"""
    svc = MvpKnowledgeService(db)
    item = svc.get_knowledge(knowledge_id)
    if not item:
        raise HTTPException(404, "知识条目不存在")
    return {
        "id": item.id,
        "title": item.title,
        "content": item.content,
        "category": item.category,
        "platform": item.platform,
        "audience": item.audience,
        "style": item.style,
        "source_material_id": item.source_material_id,
        "use_count": item.use_count,
        "created_at": str(item.created_at) if item.created_at else None
    }


@router.post("/knowledge/build")
def build_knowledge_from_material(req: KnowledgeBuildRequest, db: Session = Depends(get_db)):
    """从素材构建知识"""
    try:
        svc = MvpKnowledgeService(db)
        knowledge = svc.build_from_material(req.material_id)
        return {"message": "知识构建成功", "knowledge_id": knowledge.id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/knowledge/search")
def search_knowledge(req: KnowledgeSearchRequest, db: Session = Depends(get_db)):
    """搜索知识库"""
    svc = MvpKnowledgeService(db)
    results = svc.search_knowledge(req.query, platform=req.platform, audience=req.audience)
    return [
        {
            "id": r.id,
            "title": r.title,
            "content": r.content[:300] if r.content else "",
            "category": r.category,
            "platform": r.platform,
            "use_count": r.use_count
        }
        for r in results
    ]


# ── 自动入库Pipeline ──
@router.post("/raw-contents/auto-pipeline", response_model=AutoPipelineResponse)
def auto_pipeline(
    req: AutoPipelineRequest,
    db: Session = Depends(get_db)
):
    """
    自动入库Pipeline：接收原始内容，自动执行清洗→抽取→入知识库
    
    - 内容去重（基于标题+内容匹配）
    - 结构化字段抽取（topic, audience, content_type, opening_type, hook_sentence, cta_style, risk_level, summary）
    - 直接入库，跳过收件箱审批环节
    """
    svc = MvpKnowledgeService(db)
    result = svc.auto_ingest_from_raw(
        title=req.title,
        content=req.content,
        platform=req.platform,
        source_url=req.source_url,
        author=req.author
    )
    return AutoPipelineResponse(**result)


@router.post("/raw-contents/auto-pipeline/batch", response_model=AutoPipelineBatchResponse)
def auto_pipeline_batch(
    req: AutoPipelineBatchRequest,
    db: Session = Depends(get_db)
):
    """
    批量自动入库Pipeline：批量接收原始内容，自动执行清洗→抽取→入知识库
    """
    svc = MvpKnowledgeService(db)
    items = [item.model_dump() for item in req.items]
    result = svc.auto_ingest_batch(items)
    return AutoPipelineBatchResponse(
        total=result["total"],
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        results=[AutoPipelineResponse(**r) for r in result["results"]]
    )


# ── AI工作台 ──
@router.post("/generate")
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    """多版本内容生成"""
    try:
        svc = MvpGenerateService(db)
        result = svc.generate_multi_version(
            source_type=req.source_type,
            source_id=req.source_id,
            manual_text=req.manual_text,
            target_platform=req.target_platform,
            audience=req.audience,
            style=req.style,
            enable_knowledge=req.enable_knowledge,
            enable_rewrite=req.enable_rewrite,
            version_count=req.version_count,
            extra_requirements=req.extra_requirements
        )
        if result.get("error"):
            raise HTTPException(500, result["error"])
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/generate/final")
def generate_final(req: GenerateRequest, db: Session = Depends(get_db)):
    """完整主链路生成（标签识别→知识检索→多版本生成→合规审核）"""
    try:
        svc = MvpGenerateService(db)
        result = svc.generate_final(
            source_type=req.source_type,
            source_id=req.source_id,
            manual_text=req.manual_text,
            target_platform=req.target_platform,
            audience=req.audience,
            style=req.style,
            enable_knowledge=req.enable_knowledge,
            enable_rewrite=req.enable_rewrite,
            version_count=req.version_count,
            extra_requirements=req.extra_requirements
        )
        if result.get("error"):
            raise HTTPException(500, result["error"])
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/generate/full-pipeline")
async def generate_pipeline(req: FullPipelineRequest, db: Session = Depends(get_db)):
    """
    全流程内容生成接口（知识库检索 -> 上下文编排 -> 多版本生成 -> 合规审核 -> 最终输出）
    
    请求参数：
    - platform: 目标平台 (xiaohongshu / douyin / zhihu)
    - account_type: 账号类型 (loan_advisor / agent / knowledge_account)
    - audience: 目标人群 (bad_credit / high_debt / office_worker / self_employed)
    - topic: 内容主题 (loan / credit / online_loan / housing_fund)
    - goal: 内容目标 (private_message / consultation / conversion)
    
    响应：
    - versions: 3个版本的生成结果 (professional/casual/seeding)
    - compliance: 合规审核结果
    - final_text: 最终推荐文本
    - knowledge_context_used: 是否使用了知识库上下文
    """
    try:
        svc = MvpGenerateService(db)
        result = await svc.generate_full_pipeline(req)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"内容生成失败: {str(e)}")


# ── 合规审核 ──
@router.post("/compliance/check")
def compliance_check(req: ComplianceCheckRequest, db: Session = Depends(get_db)):
    """合规检查"""
    svc = MvpComplianceService(db)
    return svc.check(req.text)


# ── 合规规则管理 ──
@router.get("/compliance/rules")
def list_compliance_rules(
    rule_type: str = "",
    risk_level: str = "",
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db)
):
    """规则列表"""
    from app.models.models import MvpComplianceRule
    query = db.query(MvpComplianceRule)
    if rule_type:
        query = query.filter(MvpComplianceRule.rule_type == rule_type)
    if risk_level:
        query = query.filter(MvpComplianceRule.risk_level == risk_level)
    total = query.count()
    items = query.offset((page-1)*size).limit(size).all()
    return {
        "items": [{"id": r.id, "rule_type": r.rule_type, "keyword": r.keyword,
                   "pattern": getattr(r, 'pattern', None),
                   "risk_level": r.risk_level, "description": getattr(r, 'description', None),
                   "suggestion": getattr(r, 'suggestion', None),
                   "is_active": getattr(r, 'is_active', True),
                   "created_at": str(r.created_at) if r.created_at else None} for r in items],
        "total": total, "page": page, "size": size
    }


@router.post("/compliance/rules")
def create_compliance_rule(req: ComplianceRuleRequest, db: Session = Depends(get_db)):
    """创建规则"""
    from app.models.models import MvpComplianceRule
    rule = MvpComplianceRule(
        rule_type=req.rule_type,
        keyword=req.keyword,
        risk_level=req.risk_level,
    )
    # 如果模型有额外字段则设置
    if hasattr(rule, 'pattern') and req.pattern:
        rule.pattern = req.pattern
    if hasattr(rule, 'description') and req.description:
        rule.description = req.description
    if hasattr(rule, 'suggestion') and req.suggestion:
        rule.suggestion = req.suggestion
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"success": True, "id": rule.id}


@router.put("/compliance/rules/{rule_id}")
def update_compliance_rule(rule_id: int, req: ComplianceRuleRequest, db: Session = Depends(get_db)):
    """更新规则"""
    from app.models.models import MvpComplianceRule
    rule = db.query(MvpComplianceRule).filter(MvpComplianceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    rule.rule_type = req.rule_type
    rule.keyword = req.keyword
    rule.risk_level = req.risk_level
    if hasattr(rule, 'pattern'):
        rule.pattern = req.pattern
    if hasattr(rule, 'description'):
        rule.description = req.description
    if hasattr(rule, 'suggestion'):
        rule.suggestion = req.suggestion
    db.commit()
    return {"success": True, "id": rule.id}


@router.delete("/compliance/rules/{rule_id}")
def delete_compliance_rule(rule_id: int, db: Session = Depends(get_db)):
    """删除规则"""
    from app.models.models import MvpComplianceRule
    rule = db.query(MvpComplianceRule).filter(MvpComplianceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    db.delete(rule)
    db.commit()
    return {"success": True}


@router.post("/compliance/test")
def test_compliance_rule(req: ComplianceTestRequest, db: Session = Depends(get_db)):
    """输入文本，用所有规则检测风险"""
    svc = MvpComplianceService(db)
    result = svc.check(req.text)
    return result


# ── 标签 ──
@router.get("/tags")
def list_tags(type: str = Query(None), db: Session = Depends(get_db)):
    """列出标签"""
    svc = MvpTagService(db)
    tags = svc.list_tags(tag_type=type)
    return [
        {
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "created_at": str(t.created_at) if t.created_at else None
        }
        for t in tags
    ]


@router.post("/tags")
def create_tag(req: TagCreateRequest, db: Session = Depends(get_db)):
    """创建标签"""
    svc = MvpTagService(db)
    tag = svc.create_tag(req.name, req.type)
    return {"id": tag.id, "name": tag.name, "type": tag.type}


# ── 统计（AI中枢用）──
@router.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)):
    """获取统计概览"""
    from app.models.models import MvpInboxItem, MvpMaterialItem, MvpKnowledgeItem, MvpGenerationResult
    from sqlalchemy import func
    from datetime import datetime, timedelta

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    inbox_pending = db.query(func.count(MvpInboxItem.id)).filter(
        MvpInboxItem.biz_status == "pending"
    ).scalar() or 0

    material_count = db.query(func.count(MvpMaterialItem.id)).scalar() or 0

    knowledge_count = db.query(func.count(MvpKnowledgeItem.id)).scalar() or 0

    today_gen = db.query(func.count(MvpGenerationResult.id)).filter(
        MvpGenerationResult.created_at >= today_start
    ).scalar() or 0

    risk_count = db.query(func.count(MvpGenerationResult.id)).filter(
        MvpGenerationResult.compliance_status == "blocked"
    ).scalar() or 0

    recent_gens = db.query(MvpGenerationResult).order_by(
        MvpGenerationResult.created_at.desc()
    ).limit(5).all()

    recent_mats = db.query(MvpMaterialItem).order_by(
        MvpMaterialItem.created_at.desc()
    ).limit(5).all()

    return {
        "inbox_pending": inbox_pending,
        "material_count": material_count,
        "knowledge_count": knowledge_count,
        "today_generation_count": today_gen,
        "risk_content_count": risk_count,
        "recent_generations": [
            {
                "id": g.id,
                "title": g.output_title or "",
                "version": g.version,
                "created_at": str(g.created_at) if g.created_at else None
            }
            for g in recent_gens
        ],
        "recent_materials": [
            {
                "id": m.id,
                "title": m.title,
                "platform": m.platform,
                "created_at": str(m.created_at) if m.created_at else None
            }
            for m in recent_mats
        ]
    }


# ── Dashboard统计（AI中枢用）──
@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def dashboard_stats(db: Session = Depends(get_db)):
    """获取Dashboard统计数据（AI中枢用）"""
    from app.models.models import MvpInboxItem, MvpMaterialItem, MvpKnowledgeItem, MvpGenerationResult
    from sqlalchemy import func, or_
    from datetime import date

    today = date.today()
    today_str = today.isoformat()

    # 今日采集量（mvp_inbox_items 今日创建的数量）
    today_collected = db.query(func.count(MvpInboxItem.id)).filter(
        func.date(MvpInboxItem.created_at) == today
    ).scalar() or 0

    # 今日入知识库量（mvp_knowledge_items 今日创建的数量）
    today_knowledge_ingested = db.query(func.count(MvpKnowledgeItem.id)).filter(
        func.date(MvpKnowledgeItem.created_at) == today
    ).scalar() or 0

    # 今日生成量（mvp_generation_results 今日创建的数量）
    today_generated = db.query(func.count(MvpGenerationResult.id)).filter(
        func.date(MvpGenerationResult.created_at) == today
    ).scalar() or 0

    # 风险文案数（risk_level 为 medium 或 high 的素材数量）
    risk_content_count = db.query(func.count(MvpMaterialItem.id)).filter(
        or_(MvpMaterialItem.risk_level == "medium", MvpMaterialItem.risk_level == "high")
    ).scalar() or 0

    # 知识库总量
    total_knowledge = db.query(func.count(MvpKnowledgeItem.id)).scalar() or 0

    # 素材库总量
    total_materials = db.query(func.count(MvpMaterialItem.id)).scalar() or 0

    return DashboardStatsResponse(
        today_collected=today_collected,
        today_knowledge_ingested=today_knowledge_ingested,
        today_generated=today_generated,
        risk_content_count=risk_content_count,
        total_knowledge=total_knowledge,
        total_materials=total_materials,
        date=today_str
    )


# ── 反馈闭环 ──
@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    提交生成结果反馈
    
    - 记录反馈类型（采纳/修改后采纳/拒绝）
    - 更新关联知识条目的质量评分
    - 支持评分和标签
    """
    service = FeedbackService(db)
    result = await service.submit_feedback(
        generation_id=req.generation_id,
        query=req.query,
        generated_text=req.generated_text,
        feedback_type=req.feedback_type,
        modified_text=req.modified_text,
        rating=req.rating,
        feedback_tags=req.feedback_tags,
        knowledge_ids_used=req.knowledge_ids_used
    )
    return FeedbackResponse(**result)


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    获取反馈统计
    
    - 采纳率、修改率、拒绝率
    - 平均评分
    """
    service = FeedbackService(db)
    stats = await service.get_feedback_stats(days)
    return FeedbackStatsResponse(**stats)


@router.get("/knowledge/quality/rankings")
async def get_quality_rankings(
    limit: int = Query(20, ge=1, le=100),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    获取知识库质量排行榜
    
    - 按质量评分排序
    - 显示引用次数、正负面反馈等
    """
    service = FeedbackService(db)
    items = await service.get_quality_rankings(limit, order)
    return {"items": items, "total": len(items)}


@router.get("/knowledge/quality/suggestions")
async def get_learning_suggestions(db: Session = Depends(get_db)):
    """
    获取持续学习建议
    
    - 高评价知识条目 → 建议权重提升
    - 低评价知识条目 → 建议降权或移除
    - 用户修改模式分析 → 建议内容调整方向
    """
    service = FeedbackService(db)
    suggestions = await service.get_learning_suggestions()
    return suggestions


@router.post("/knowledge/quality/adjust")
async def apply_weight_adjustment(db: Session = Depends(get_db)):
    """
    应用权重调整
    
    - quality_score > 0.8: 检索时权重 boost 1.5x
    - quality_score < 0.3: 检索时降权 0.5x
    - reference_count == 0 且 创建超30天: 标记为冷数据
    """
    service = FeedbackService(db)
    result = await service.apply_weight_adjustment()
    return result


@router.get("/feedback/tags")
async def get_feedback_tags():
    """获取可用的反馈标签选项"""
    from app.services.feedback_service import FeedbackService
    return {"tags": FeedbackService.FEEDBACK_TAGS_OPTIONS}


# ── 模型管理 ──
@router.get("/models/embedding")
async def list_embedding_models():
    """列出可用 embedding 模型"""
    model_service = get_model_manager_service()
    embedding_service = get_embedding_service()
    
    # 获取配置中的模型列表
    config_models = model_service.get_available_embedding_models()
    
    # 获取当前选中的模型
    current_model = embedding_service.get_current_model()
    
    return {
        "models": config_models,
        "current_model": current_model,
        "default_model": getattr(settings, 'DEFAULT_EMBEDDING_MODEL', 'nomic-embed-text')
    }


@router.get("/models/llm")
async def list_llm_models():
    """列出可用 LLM 模型"""
    model_service = get_model_manager_service()
    
    # 获取配置中的模型列表
    config_models = model_service.get_available_llm_models()
    
    return {
        "models": config_models,
        "default_model": getattr(settings, 'DEFAULT_LLM_MODEL', 'qwen2.5')
    }


@router.post("/models/embedding/select")
async def select_embedding_model(request: dict):
    """切换当前 embedding 模型
    
    请求体：
    - model_name: 模型名称（如 "nomic-embed-text", "qwen3-embedding"）
    """
    model_name = request.get("model_name")
    if not model_name:
        raise HTTPException(status_code=400, detail="缺少 model_name 参数")
    
    embedding_service = get_embedding_service()
    result = embedding_service.select_model(model_name)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/models/ollama/status")
async def get_ollama_status():
    """获取 Ollama 服务状态及已安装模型"""
    model_service = get_model_manager_service()
    
    models = await model_service.list_ollama_models()
    
    return {
        "status": "running" if models else "unavailable",
        "models": models,
        "count": len(models)
    }


@router.post("/models/ollama/pull")
async def pull_ollama_model(request: dict):
    """拉取 Ollama 模型
    
    请求体：
    - model_name: 模型名称（如 "qwen2.5", "nomic-embed-text:latest"）
    """
    model_name = request.get("model_name")
    if not model_name:
        raise HTTPException(status_code=400, detail="缺少 model_name 参数")
    
    model_service = get_model_manager_service()
    result = await model_service.pull_ollama_model(model_name)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.get("/models/ollama/{model_name}/info")
async def get_ollama_model_info(model_name: str):
    """获取 Ollama 模型详细信息"""
    model_service = get_model_manager_service()
    result = await model_service.get_model_info(model_name)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result


@router.get("/models/ollama/{model_name}/check")
async def check_ollama_model(model_name: str):
    """检查 Ollama 模型是否可用"""
    model_service = get_model_manager_service()
    result = await model_service.check_model_status(model_name)
    
    return result


@router.post("/models/benchmark")
async def benchmark_model(request: dict):
    """模型性能对标
    
    请求体：
    - model_name: 模型名称（必需）
    - test_text: 测试文本（可选，默认使用内置测试文本）
    """
    model_name = request.get("model_name")
    test_text = request.get("test_text")
    
    if not model_name:
        raise HTTPException(status_code=400, detail="缺少 model_name 参数")
    
    model_service = get_model_manager_service()
    result = await model_service.benchmark_model(model_name, test_text)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


# ═══════════════════════════════════════════════════════════════
# 知识图谱 - Task #18
# ═══════════════════════════════════════════════════════════════

@router.post("/knowledge/graph/build")
async def build_knowledge_relations(db: Session = Depends(get_db)):
    """触发全量关系构建
    
    扫描所有知识条目，基于向量相似度和元数据匹配构建关系图。
    大量数据时分批处理，每批100条。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service
    
    service = get_knowledge_graph_service(db)
    result = await service.batch_build_relations(batch_size=100)
    
    return BatchBuildRelationsResponse(
        total_items=result["total_items"],
        processed=result["processed"],
        relations_created=result["relations_created"],
        errors=result["errors"],
        message=f"构建完成: 处理 {result['processed']} 条, 创建 {result['relations_created']} 条关系"
    )


@router.post("/knowledge/{knowledge_id}/relations/build")
async def build_single_knowledge_relations(
    knowledge_id: int,
    db: Session = Depends(get_db)
):
    """为单条知识条目构建关系
    
    基于向量相似度和元数据匹配发现并建立关系。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service
    
    service = get_knowledge_graph_service(db)
    try:
        relations = await service.build_relations(knowledge_id)
        return BuildRelationsResponse(
            success=True,
            knowledge_id=knowledge_id,
            relations_created=len(relations),
            message=f"成功创建 {len(relations)} 条关系"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/knowledge/{knowledge_id}/related")
async def get_related_knowledge_items(
    knowledge_id: int,
    relation_type: str = Query(None, description="关系类型过滤"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """获取关联知识条目（图遍历1跳）
    
    返回与指定知识条目直接相关的其他条目。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service
    
    service = get_knowledge_graph_service(db)
    results = await service.get_related_items(
        knowledge_id=knowledge_id,
        relation_type=relation_type,
        limit=limit
    )
    return {"items": results, "total": len(results)}


@router.get("/knowledge/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph_data(
    library_type: str = Query(None, description="分库类型过滤"),
    limit: int = Query(50, ge=1, le=200, description="节点数量限制"),
    db: Session = Depends(get_db)
):
    """获取知识图谱数据（nodes + edges 格式）
    
    返回节点和边的数据，用于前端可视化。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service
    
    service = get_knowledge_graph_service(db)
    result = await service.get_knowledge_graph(
        library_type=library_type,
        limit=limit
    )
    return KnowledgeGraphResponse(**result)


@router.get("/knowledge/graph/stats", response_model=GraphStatsResponse)
async def get_knowledge_graph_stats(db: Session = Depends(get_db)):
    """获取图谱统计信息
    
    返回节点数、边数、平均度、最大连通分量等统计数据。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service
    
    service = get_knowledge_graph_service(db)
    result = await service.get_graph_stats()
    return GraphStatsResponse(**result)


@router.get("/knowledge/graph/clusters")
async def get_knowledge_topic_clusters(
    min_size: int = Query(2, ge=2, le=10, description="最小簇大小"),
    db: Session = Depends(get_db)
):
    """获取主题聚类
    
    基于关系图发现主题簇，返回 [{topic, items, count}]。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service
    
    service = get_knowledge_graph_service(db)
    result = await service.cluster_topics(min_cluster_size=min_size)
    return {"clusters": result, "total": len(result)}


@router.get("/knowledge/graph/enhanced-search")
async def enhanced_knowledge_search(
    query: str = Query(..., description="查询文本"),
    top_k: int = Query(5, ge=1, le=20, description="初始检索数量"),
    expand_limit: int = Query(3, ge=0, le=10, description="每条结果扩展数量"),
    db: Session = Depends(get_db)
):
    """图增强检索
    
    先向量检索，再沿关系图扩展相关条目。
    返回增强后的检索结果。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service
    
    service = get_knowledge_graph_service(db)
    results = await service.enhanced_search(
        query=query,
        top_k=top_k,
        expand_limit=expand_limit
    )
    return {"results": results, "total": len(results)}
