from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.domains.acquisition.collect_service import (
    ALL_CATEGORIES,
    PLATFORM_LABELS,
    CollectService,
)
from app.domains.acquisition.inbox_service import InboxService
from app.domains.ai_workbench.ai_service import AIService
from app.integrations.ocr import extract_text_from_image_bytes
from app.models import ContentAsset, InboxItem
from app.schemas.schemas import (
    CollectIntakeRequest,
    CollectIntakeResponse,
    CollectOcrResponse,
    CollectSaveRequest,
    CollectUpdateRequest,
    ContentAssetDetailResponse,
    ParseLinkRequest,
)

collect_routes = APIRouter(tags=["collect"])


def _find_existing_request_item(db: Session, user_id: int, client_request_id: str | None) -> InboxItem | None:
    if not client_request_id:
        return None
    marker = f"[REQ_ID]{client_request_id}"
    return (
        db.query(InboxItem)
        .filter(
            InboxItem.owner_id == user_id,
            InboxItem.manual_note.ilike(f"%{marker}%"),
        )
        .order_by(InboxItem.created_at.desc())
        .first()
    )


@collect_routes.post("/intake", response_model=CollectIntakeResponse)
def intake_collect(
    req: CollectIntakeRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """统一采集入口：mobile_share / screenshot_ocr / wechat_forward 等统一先入 inbox。"""
    existing_item = _find_existing_request_item(db, current_user["user_id"], req.client_request_id)
    if existing_item:
        return {
            "inbox_id": existing_item.id,
            "status": existing_item.status,
            "source_type": existing_item.source_type or req.source_type,
            "dedupe_hit": True,
            "duplicate_ids": [existing_item.id],
            "message": "检测到重复提交，已复用已有收件箱条目",
        }

    normalized_url = InboxService._normalize_url(req.source_url)
    duplicate_rows = []
    if normalized_url:
        duplicate_rows = (
            db.query(InboxItem)
            .filter(
                InboxItem.owner_id == current_user["user_id"],
                InboxItem.source_url == normalized_url,
                InboxItem.status.in_(["pending", "analyzed", "imported"]),
            )
            .order_by(InboxItem.created_at.desc())
            .limit(10)
            .all()
        )

    payload = req.model_dump(exclude={"raw_payload", "client_request_id"})
    payload["source_url"] = normalized_url
    request_marker = f"[REQ_ID]{req.client_request_id}" if req.client_request_id else ""

    if duplicate_rows:
        marker = f"[DUPLICATE_HINT] url_exists={len(duplicate_rows)}"
        existing_note = payload.get("manual_note") or ""
        payload["manual_note"] = f"{existing_note}\n{marker}\n{request_marker}".strip()
    elif request_marker:
        existing_note = payload.get("manual_note") or ""
        payload["manual_note"] = f"{existing_note}\n{request_marker}".strip()

    item = InboxService.create_item(db, current_user["user_id"], payload)
    return {
        "inbox_id": item.id,
        "status": item.status,
        "source_type": item.source_type or req.source_type,
        "dedupe_hit": len(duplicate_rows) > 0,
        "duplicate_ids": [row.id for row in duplicate_rows],
        "message": "已进入收件箱，待分拣入素材库",
    }


@collect_routes.post("/ocr", response_model=CollectOcrResponse)
async def collect_ocr(
    image: UploadFile = File(...),
    platform: str = Form("other"),
    source_url: str | None = Form(None),
    title: str | None = Form(None),
    author: str | None = Form(None),
    save_to_inbox: bool = Form(True),
    client_request_id: str | None = Form(None),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """截图 OCR：识别后可直接进入收件箱（source_type=screenshot_ocr）。"""
    if save_to_inbox:
        existing_item = _find_existing_request_item(db, current_user["user_id"], client_request_id)
        if existing_item:
            return {
                "extracted_text": existing_item.content,
                "engine": "dedupe-cache",
                "warnings": ["检测到重复上传，已复用已有收件箱结果"],
                "inbox_id": existing_item.id,
                "dedupe_hit": True,
                "message": "OCR 请求重复提交，已返回已有收件箱条目",
            }

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片文件")

    binary = await image.read()
    if not binary:
        raise HTTPException(status_code=400, detail="空文件")

    text, engine, warnings = extract_text_from_image_bytes(binary)

    inbox_id = None
    if save_to_inbox:
        safe_title = (title or image.filename or "截图OCR内容").strip()[:255]
        request_marker = f"[REQ_ID]{client_request_id}" if client_request_id else ""
        payload = {
            "platform": platform,
            "source_url": InboxService._normalize_url(source_url),
            "content_type": "post",
            "title": safe_title if safe_title else "截图OCR内容",
            "content": text or "",
            "author": author,
            "tags": ["ocr", "screenshot"],
            "metrics": {},
            "manual_note": f"来自 mobile-h5 截图 OCR 入口\n{request_marker}".strip(),
            "source_type": "screenshot_ocr",
        }
        item = InboxService.create_item(db, current_user["user_id"], payload)
        inbox_id = item.id

    return {
        "extracted_text": text,
        "engine": engine,
        "warnings": warnings,
        "inbox_id": inbox_id,
        "dedupe_hit": False,
        "message": "OCR 完成，已进入收件箱" if inbox_id else "OCR 完成",
    }


@collect_routes.post("/parse-link")
async def parse_link(
    req: ParseLinkRequest,
    current_user: dict = Depends(verify_token),
):
    """解析链接，返回平台识别 + 页面元信息（标题/摘要）。"""
    _ = current_user
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
        "platform": platform,
        "platform_label": label,
        "source_url": url,
        "detected_title": meta.get("title", ""),
        "detected_content": meta.get("description", ""),
        "detected_author": meta.get("author", ""),
        "fetch_success": success,
        "message": message,
    }


@collect_routes.post("/save", response_model=ContentAssetDetailResponse)
def save_collect(
    req: CollectSaveRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """保存采集到的素材（来自链接解析 or 手动录入 or 批量导入）。"""
    from app.models import User

    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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


@collect_routes.post("/analyze/{content_id}")
async def analyze_content(
    content_id: int,
    force_cloud: bool = Query(False, description="强制使用云端模型"),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """用 AI 分析该素材：自动打标签、分类、给出爆款评分与改写建议。"""
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


@collect_routes.get("/list")
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
    """获取素材列表，支持平台/分类/爆款/关键字筛选。"""
    items = CollectService.get_list(
        db,
        current_user["user_id"],
        platform=platform,
        category=category,
        is_viral=is_viral,
        search=search,
        skip=skip,
        limit=limit,
    )
    result = []
    for item in items:
        result.append(
            {
                "id": item.id,
                "platform": item.platform,
                "source_url": item.source_url,
                "content_type": item.content_type,
                "title": item.title,
                "content": item.content or "",
                "author": item.author,
                "tags": item.tags or [],
                "heat_score": item.heat_score or 0.0,
                "is_viral": item.is_viral or False,
                "source_type": getattr(item, "source_type", "paste"),
                "category": getattr(item, "category", None),
                "manual_note": item.manual_note,
                "metrics": item.metrics or {},
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )
    return result


@collect_routes.get("/stats")
def collect_stats(
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """素材库统计：总量、爆款数、按平台/分类分布。"""
    return CollectService.get_stats(db, current_user["user_id"])


@collect_routes.get("/meta/options")
def collect_options(_: dict = Depends(verify_token)):
    """返回可用的平台和分类选项。"""
    return {
        "platforms": list(PLATFORM_LABELS.items()),
        "categories": ALL_CATEGORIES,
    }


@collect_routes.put("/{content_id}", response_model=ContentAssetDetailResponse)
def update_collect(
    content_id: int,
    req: CollectUpdateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """更新素材的标签 / 备注 / 分类 / 标题 / 正文。"""
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


@collect_routes.delete("/{content_id}")
def delete_collect(
    content_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """删除指定素材。"""
    item = db.query(ContentAsset).filter(
        ContentAsset.id == content_id,
        ContentAsset.owner_id == current_user["user_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="素材不存在")

    db.delete(item)
    db.commit()
    return {"message": "已删除"}


v1_collect_router = APIRouter(prefix="/collect")
v1_collect_router.include_router(collect_routes)
