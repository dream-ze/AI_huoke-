"""MVP素材库路由模块"""

from app.core.database import get_db
from app.schemas.mvp_schemas import (
    BatchBuildKnowledgeRequest,
    BatchBuildKnowledgeResponse,
    MaterialCreateRequest,
    UpdateTagsRequest,
)
from app.services.mvp_knowledge_service import MvpKnowledgeService
from app.services.mvp_material_service import MvpMaterialService
from app.services.mvp_rewrite_service import MvpRewriteService
from app.services.mvp_tag_service import MvpTagService
from app.services.pipeline_service import PipelineService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter()


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
    db: Session = Depends(get_db),
):
    """列出素材列表，支持筛选和分页"""
    svc = MvpMaterialService(db)
    return svc.list_materials(
        page=page,
        size=size,
        platform=platform,
        tag_id=tag_id,
        audience=audience,
        style=style,
        is_hot=is_hot,
        keyword=keyword,
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
            "error": d["error"],
        }
        for d in result["details"]
    ]

    return BatchBuildKnowledgeResponse(
        total=result["total"],
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        details=details,
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
