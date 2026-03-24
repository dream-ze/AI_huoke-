"""
素材中台 API 端点
  POST  /api/collect/parse-link      链接解析（检测平台 + 抓取元信息）
  POST  /api/collect/save            保存素材
  POST  /api/collect/analyze/{id}    AI 爆款分析
  GET   /api/collect/list            素材列表（含过滤）
  GET   /api/collect/stats           统计数据
  PUT   /api/collect/{id}            更新标签/备注/分类
  DELETE /api/collect/{id}           删除素材
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models import ContentAsset
from app.schemas import (
    CollectSaveRequest,
    CollectUpdateRequest,
    DuplicateCheckRequest,
    ParseLinkRequest,
    ContentAssetDetailResponse,
)
from app.services.ai_service import AIService
from app.services.collect_service import CollectService, PLATFORM_LABELS, ALL_CATEGORIES

router = APIRouter(prefix="/api/collect", tags=["collect"])


# ──────────────────────────────────────────
# 链接解析
# ──────────────────────────────────────────
@router.post("/parse-link")
async def parse_link(
    req: ParseLinkRequest,
    current_user: dict = Depends(verify_token),
):
    """解析链接，返回平台识别 + 页面元信息（标题/摘要）"""
    # 基础 URL 校验
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请输入完整 URL（以 http/https 开头）")

    platform = CollectService.detect_platform(url)
    success, meta = await CollectService.fetch_url_meta(url)

    label = PLATFORM_LABELS.get(platform, "未知平台")
    if success and (meta.get("title") or meta.get("description")):
        message = f"✅ 已从 {label} 提取到标题和摘要，请核对内容后保存入库"
    else:
        message = f"⚠️ 已识别为 {label}，但该平台有访问限制，无法自动提取正文——请手动填写内容后保存"

    return {
        "platform":         platform,
        "platform_label":   label,
        "source_url":       url,
        "detected_title":   meta.get("title", ""),
        "detected_content": meta.get("description", ""),
        "detected_author":  meta.get("author", ""),
        "fetch_success":    success,
        "message":          message,
    }


# ──────────────────────────────────────────
# 保存素材
# ──────────────────────────────────────────
@router.post("/save", response_model=ContentAssetDetailResponse)
def save_collect(
    req: CollectSaveRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """保存采集到的素材（来自链接解析 or 手动录入 or 批量导入）"""
    from app.models import User

    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 自动分类（未传则规则判断）
    category = req.category or CollectService.auto_category(req.title, req.content)

    data = req.model_dump(exclude={"source_type", "category"})
    item = ContentAsset(
        owner_id=current_user["user_id"],
        source_type=req.source_type,
        category=category,
        **data,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ──────────────────────────────────────────
# AI 爆款分析
# ──────────────────────────────────────────
@router.post("/analyze/{content_id}")
async def analyze_content(
    content_id: int,
    force_cloud: bool = Query(False, description="强制使用云端模型"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """用 AI 分析该素材：自动打标签、分类、给出爆款评分与改写建议"""
    item = db.query(ContentAsset).filter(
        ContentAsset.id == content_id,
        ContentAsset.owner_id == current_user["user_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    ai_service = AIService(db=db)
    result = await CollectService.analyze_with_ai(
        item, ai_service, force_cloud, current_user["user_id"]
    )

    # 将分析结果写回数据库
    if result.get("tags"):
        item.tags = result["tags"]
    if result.get("category"):
        item.category = result["category"]
    if result.get("heat_score") is not None:
        item.heat_score = float(result["heat_score"])
    if result.get("is_viral") is not None:
        item.is_viral = bool(result["is_viral"])
    db.commit()

    return {"content_id": content_id, **result}


# ──────────────────────────────────────────
# 素材列表
# ──────────────────────────────────────────
@router.get("/list")
def list_collect(
    platform: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_viral: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获取素材列表，支持平台/分类/爆款/关键字筛选"""
    items = CollectService.get_list(
        db, current_user["user_id"],
        platform=platform, category=category,
        is_viral=is_viral, search=search,
        skip=skip, limit=limit,
    )
    # 手动序列化，确保返回 content 字段
    result = []
    for item in items:
        result.append({
            "id":           item.id,
            "platform":     item.platform,
            "source_url":   item.source_url,
            "content_type": item.content_type,
            "title":        item.title,
            "content":      item.content or "",
            "author":       item.author,
            "tags":         item.tags or [],
            "heat_score":   item.heat_score or 0.0,
            "is_viral":     item.is_viral or False,
            "source_type":  getattr(item, "source_type", "paste"),
            "category":     getattr(item, "category", None),
            "manual_note":  item.manual_note,
            "metrics":      item.metrics or {},
            "created_at":   item.created_at.isoformat() if item.created_at else None,
        })
    return result


# ──────────────────────────────────────────
# 统计
# ──────────────────────────────────────────
@router.get("/stats")
def collect_stats(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """素材库统计：总量、爆款数、按平台/分类分布"""
    return CollectService.get_stats(db, current_user["user_id"])


@router.get("/meta/options")
def collect_options(_: dict = Depends(verify_token)):
    """返回可用的平台和分类选项"""
    return {
        "platforms": list(PLATFORM_LABELS.items()),   # [(key, label), ...]
        "categories": ALL_CATEGORIES,
    }


# ──────────────────────────────────────────
# 更新素材
# ──────────────────────────────────────────
@router.put("/{content_id}", response_model=ContentAssetDetailResponse)
def update_collect(
    content_id: int,
    req: CollectUpdateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """更新素材的标签 / 备注 / 分类 / 标题 / 正文"""
    item = db.query(ContentAsset).filter(
        ContentAsset.id == content_id,
        ContentAsset.owner_id == current_user["user_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


# ──────────────────────────────────────────
# 删除素材
# ──────────────────────────────────────────
@router.delete("/{content_id}")
def delete_collect(
    content_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """删除指定素材"""
    item = db.query(ContentAsset).filter(
        ContentAsset.id == content_id,
        ContentAsset.owner_id == current_user["user_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    db.delete(item)
    db.commit()
    return {"message": "已删除"}


# ──────────────────────────────────────────
# 内容去重检查
# ──────────────────────────────────────────
@router.post("/check-duplicate")
def check_duplicate(
    req: DuplicateCheckRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    检查内容是否与素材库中已有内容重复。
    依次通过 URL 精确匹配、标题精确匹配、文本相似度三层检查。
    """
    result = CollectService.check_duplicate(
        db=db,
        user_id=current_user["user_id"],
        title=req.title,
        content=req.content,
        source_url=req.source_url,
        similarity_threshold=req.similarity_threshold,
    )
    return result
