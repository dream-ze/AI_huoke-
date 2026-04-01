"""MVP知识库路由模块"""

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.mvp_schemas import (  # 知识图谱相关 Schema
    AutoPipelineBatchRequest,
    AutoPipelineBatchResponse,
    AutoPipelineRequest,
    AutoPipelineResponse,
    BatchBuildRelationsResponse,
    BuildRelationsResponse,
    GraphStatsResponse,
    KnowledgeBuildRequest,
    KnowledgeGraphResponse,
    KnowledgeSearchRequest,
)
from app.services.mvp_knowledge_service import MvpKnowledgeService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter()


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
    db: Session = Depends(get_db),
):
    """按分库类型列出知识条目"""
    svc = MvpKnowledgeService(db)
    result = svc.list_by_library(library_type, page, size, keyword)
    # 序列化
    items_out = []
    for item in result["items"]:
        items_out.append(
            {
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
            }
        )
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
    db: Session = Depends(get_db),
):
    """列出知识库条目"""
    svc = MvpKnowledgeService(db)
    result = svc.list_knowledge(
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
    # 序列化items
    items_out = []
    for item in result.get("items", []):
        items_out.append(
            {
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
                "library_type": getattr(item, "library_type", None),
                "layer": getattr(item, "layer", None),
                "risk_level": getattr(item, "risk_level", None),
                "summary": getattr(item, "summary", None),
                "topic": getattr(item, "topic", None),
                "content_type": getattr(item, "content_type", None),
                "opening_type": getattr(item, "opening_type", None),
                "hook_sentence": getattr(item, "hook_sentence", None),
                "cta_style": getattr(item, "cta_style", None),
                "is_hot": getattr(item, "is_hot", False),
                "author": getattr(item, "author", None),
            }
        )
    return {
        "items": items_out,
        "total": result.get("total", 0),
        "page": result.get("page", page),
        "size": result.get("size", size),
    }


@router.get("/knowledge/libraries")
def get_knowledge_libraries(db: Session = Depends(get_db)):
    """获取各分库统计"""
    from app.models.models import MvpKnowledgeItem
    from sqlalchemy import func as sa_func

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
        db.query(MvpKnowledgeItem.library_type, sa_func.count(MvpKnowledgeItem.id))
        .group_by(MvpKnowledgeItem.library_type)
        .all()
    )

    libraries = []
    total = 0
    for lib_type, count in results:
        libraries.append(
            {
                "library_type": lib_type or "industry_phrases",
                "label": LIBRARY_LABELS.get(lib_type, lib_type or "其他"),
                "count": count,
            }
        )
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
        result.append(
            {
                "id": c.id,
                "knowledge_id": c.knowledge_id,
                "chunk_type": c.chunk_type,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "metadata_json": c.metadata_json,
                "has_embedding": bool(c.embedding),
                "token_count": c.token_count or 0,
                "created_at": str(c.created_at) if c.created_at else None,
            }
        )

    return {"chunks": result, "total": len(result)}


@router.post("/knowledge/reindex")
async def reindex_knowledge(
    request: dict = None, db: Session = Depends(get_db), _user=Depends(require_permission("knowledge", "write"))
):
    """重建知识切块和向量索引 - 需要 knowledge:write 权限"""
    from app.models.models import MvpKnowledgeItem
    from app.services.chunking_service import get_chunking_service

    body = request or {}
    knowledge_ids = body.get("knowledge_ids", None)
    embedding_model = body.get("embedding_model", "volcano")

    chunking = get_chunking_service(db)

    if knowledge_ids:
        items = db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id.in_(knowledge_ids)).all()
    else:
        items = db.query(MvpKnowledgeItem).limit(500).all()

    total = len(items)
    success = 0
    failed = 0

    for item in items:
        try:
            result = await chunking.process_and_store_chunks(item.id, embedding_model=embedding_model)
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
        "message": f"处理完成: {success}成功, {failed}失败",
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
        "created_at": str(item.created_at) if item.created_at else None,
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
            "use_count": r.use_count,
        }
        for r in results
    ]


# ── 自动入库Pipeline ──
@router.post("/raw-contents/auto-pipeline", response_model=AutoPipelineResponse)
def auto_pipeline(req: AutoPipelineRequest, db: Session = Depends(get_db)):
    """
    自动入库Pipeline：接收原始内容，自动执行清洗→抽取→入知识库

    - 内容去重（基于标题+内容匹配）
    - 结构化字段抽取（topic, audience, content_type, opening_type, hook_sentence, cta_style, risk_level, summary）
    - 直接入库，跳过收件箱审批环节
    """
    svc = MvpKnowledgeService(db)
    result = svc.auto_ingest_from_raw(
        title=req.title, content=req.content, platform=req.platform, source_url=req.source_url, author=req.author
    )
    return AutoPipelineResponse(**result)


@router.post("/raw-contents/auto-pipeline/batch", response_model=AutoPipelineBatchResponse)
def auto_pipeline_batch(req: AutoPipelineBatchRequest, db: Session = Depends(get_db)):
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
        results=[AutoPipelineResponse(**r) for r in result["results"]],
    )


# ═══════════════════════════════════════════════════════════════
# 知识图谱
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
        message=f"构建完成: 处理 {result['processed']} 条, 创建 {result['relations_created']} 条关系",
    )


@router.post("/knowledge/{knowledge_id}/relations/build")
async def build_single_knowledge_relations(knowledge_id: int, db: Session = Depends(get_db)):
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
            message=f"成功创建 {len(relations)} 条关系",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/knowledge/{knowledge_id}/related")
async def get_related_knowledge_items(
    knowledge_id: int,
    relation_type: str = Query(None, description="关系类型过滤"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    db: Session = Depends(get_db),
):
    """获取关联知识条目（图遍历1跳）

    返回与指定知识条目直接相关的其他条目。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service

    service = get_knowledge_graph_service(db)
    results = await service.get_related_items(knowledge_id=knowledge_id, relation_type=relation_type, limit=limit)
    return {"items": results, "total": len(results)}


@router.get("/knowledge/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph_data(
    library_type: str = Query(None, description="分库类型过滤"),
    limit: int = Query(50, ge=1, le=200, description="节点数量限制"),
    db: Session = Depends(get_db),
):
    """获取知识图谱数据（nodes + edges 格式）

    返回节点和边的数据，用于前端可视化。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service

    service = get_knowledge_graph_service(db)
    result = await service.get_knowledge_graph(library_type=library_type, limit=limit)
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
    min_size: int = Query(2, ge=2, le=10, description="最小簇大小"), db: Session = Depends(get_db)
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
    db: Session = Depends(get_db),
):
    """图增强检索

    先向量检索，再沿关系图扩展相关条目。
    返回增强后的检索结果。
    """
    from app.services.knowledge_graph_service import get_knowledge_graph_service

    service = get_knowledge_graph_service(db)
    results = await service.enhanced_search(query=query, top_k=top_k, expand_limit=expand_limit)
    return {"results": results, "total": len(results)}
