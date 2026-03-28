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
)
from app.schemas.generate_schema import FullPipelineRequest
from app.services.mvp_inbox_service import MvpInboxService
from app.services.mvp_material_service import MvpMaterialService
from app.services.mvp_tag_service import MvpTagService
from app.services.mvp_knowledge_service import MvpKnowledgeService
from app.services.mvp_generate_service import MvpGenerateService
from app.services.mvp_rewrite_service import MvpRewriteService
from app.services.mvp_compliance_service import MvpComplianceService

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
    db: Session = Depends(get_db)
):
    """列出收件箱条目，支持筛选和分页"""
    svc = MvpInboxService(db)
    result = svc.list_inbox(
        page=page, size=size, status=status, platform=platform,
        source_type=source_type, risk_level=risk_level,
        duplicate_status=duplicate_status, keyword=keyword
    )
    # 序列化items
    items_out = []
    for item in result.get("items", []):
        items_out.append({
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
def inbox_to_material(item_id: int, db: Session = Depends(get_db)):
    """将收件箱条目入素材库"""
    try:
        svc = MvpInboxService(db)
        material = svc.to_material(item_id)
        return {"message": "已入素材库", "material_id": material.id}
    except ValueError as e:
        raise HTTPException(400, str(e))


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


@router.post("/materials/{material_id}/rewrite")
def rewrite_material(material_id: int, db: Session = Depends(get_db)):
    """爆款仿写"""
    try:
        svc = MvpRewriteService(db)
        result = svc.rewrite_hot(material_id)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/materials/{material_id}/tags")
def update_material_tags(material_id: int, req: UpdateTagsRequest, db: Session = Depends(get_db)):
    """更新素材标签"""
    svc = MvpTagService(db)
    svc.update_material_tags(material_id, req.tag_ids)
    return {"message": "标签更新成功"}


# ── 知识库 ──
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
        return svc.generate_multi_version(
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
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/generate/final")
def generate_final(req: GenerateRequest, db: Session = Depends(get_db)):
    """完整主链路生成（标签识别→知识检索→多版本生成→合规审核）"""
    try:
        svc = MvpGenerateService(db)
        return svc.generate_final(
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
