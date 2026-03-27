#!/usr/bin/env python3
"""
将 legacy content_assets 历史数据回填到新的 first-principles material pipeline。

默认行为：
  - 从 content_assets 读取历史素材
  - 写入 source_contents / normalized_contents / material_items / knowledge_documents / knowledge_chunks
  - 使用 legacy-content-asset-{id} 作为 source_id，支持幂等重跑

示例：
  python scripts/backfill_material_pipeline.py --limit 100
  python scripts/backfill_material_pipeline.py --owner-id 1 --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DEBUG", "false")

from sqlalchemy.orm import joinedload

from app.core.database import SessionLocal
from app.models import ContentAsset, MaterialItem
from app.services.collector import AcquisitionIntakeService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="回填旧 content_assets 到新素材管道")
    parser.add_argument("--owner-id", type=int, default=None, help="仅回填指定 owner_id")
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少条，0 表示不限制")
    parser.add_argument("--after-id", type=int, default=0, help="仅处理大于该 ID 的旧素材")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入数据库")
    return parser.parse_args()


def build_raw_item(asset: ContentAsset) -> dict:
    metrics = dict(asset.metrics or {})
    screenshots = asset.screenshots or []
    legacy_source_id = f"legacy-content-asset-{asset.id}"
    return {
        "id": legacy_source_id,
        "platform": asset.platform,
        "source_url": asset.source_url,
        "title": asset.title,
        "content_text": asset.content,
        "author_name": asset.author,
        "publish_time": asset.publish_time.isoformat() if asset.publish_time else None,
        "cover_url": screenshots[0] if screenshots else None,
        "like_count": metrics.get("like_count") or metrics.get("likes") or 0,
        "comment_count": metrics.get("comment_count") or metrics.get("comments") or 0,
        "favorite_count": metrics.get("favorite_count") or metrics.get("favorites") or 0,
        "share_count": metrics.get("share_count") or metrics.get("shares") or 0,
        "parse_status": "success",
        "risk_status": "safe",
        "raw_payload": {
            "legacy_content_asset_id": asset.id,
            "legacy_source_type": asset.source_type,
            "legacy_category": asset.category,
            "legacy_tags": asset.tags or [],
            "legacy_comments_keywords": asset.comments_keywords or [],
            "legacy_top_comments": asset.top_comments or [],
            "legacy_manual_note": asset.manual_note,
            "legacy_metrics": metrics,
            "legacy_screenshots": screenshots,
        },
    }


def apply_legacy_timestamps(material: MaterialItem, asset: ContentAsset) -> None:
    source = material.source_content
    normalized = material.normalized_content
    if asset.created_at:
        if source is not None:
            source.created_at = asset.created_at
        if normalized is not None:
            normalized.created_at = asset.created_at
        material.created_at = asset.created_at
        for document in material.knowledge_documents or []:
            document.created_at = asset.created_at
            for chunk in document.knowledge_chunks or []:
                chunk.created_at = asset.created_at
    if asset.updated_at:
        material.updated_at = asset.updated_at


def main() -> int:
    args = parse_args()
    db = SessionLocal()

    created_count = 0
    skipped_count = 0
    failed_count = 0

    try:
        query = (
            db.query(ContentAsset)
            .options(
                joinedload(ContentAsset.blocks),
                joinedload(ContentAsset.comments),
                joinedload(ContentAsset.snapshots),
                joinedload(ContentAsset.insights),
            )
            .filter(ContentAsset.id > args.after_id)
            .order_by(ContentAsset.id.asc())
        )
        if args.owner_id is not None:
            query = query.filter(ContentAsset.owner_id == args.owner_id)
        if args.limit > 0:
            query = query.limit(args.limit)

        assets = query.all()
        print(f"[INFO] 准备处理 {len(assets)} 条历史素材")

        for asset in assets:
            legacy_source_id = f"legacy-content-asset-{asset.id}"
            existing = (
                db.query(MaterialItem)
                .filter(
                    MaterialItem.owner_id == asset.owner_id,
                    MaterialItem.platform == asset.platform,
                    MaterialItem.source_id == legacy_source_id,
                )
                .first()
            )
            if existing is not None:
                skipped_count += 1
                print(f"[SKIP] content_asset={asset.id} -> material_item={existing.id}")
                continue

            if args.dry_run:
                skipped_count += 1
                print(f"[DRY ] content_asset={asset.id} title={asset.title[:40]}")
                continue

            try:
                result = AcquisitionIntakeService._process_item(
                    db=db,
                    owner_id=asset.owner_id,
                    source_channel="legacy_migration",
                    raw_item=build_raw_item(asset),
                    platform=asset.platform,
                    keyword=asset.category or "",
                    remark=f"历史回填自 content_assets#{asset.id}",
                )
                material = result["material"]
                apply_legacy_timestamps(material, asset)
                db.commit()
                created_count += 1
                print(f"[OK  ] content_asset={asset.id} -> material_item={material.id} status={material.status}")
            except Exception as exc:
                db.rollback()
                failed_count += 1
                print(f"[FAIL] content_asset={asset.id} error={exc}")

        print(
            "[DONE] "
            f"created={created_count} skipped={skipped_count} failed={failed_count} dry_run={args.dry_run}"
        )
        return 0 if failed_count == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())