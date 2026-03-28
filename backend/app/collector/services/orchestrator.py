from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.ai_service import AIService
from app.collector.services.pipeline import AcquisitionIntakeService


class MaterialPipelineOrchestrator:
    """Single entrypoint for ingest -> clean -> knowledge -> retrieve -> generate."""

    def __init__(
        self,
        db: Session,
        owner_id: int,
        ai_service: Optional[AIService] = None,
    ) -> None:
        self.db = db
        self.owner_id = owner_id
        self.ai_service = ai_service or AIService(db=db)

    def ingest_manual_content(
        self,
        platform: str,
        title: Optional[str],
        content_text: str,
        note: Optional[str] = None,
        tags: Optional[list[str]] = None,
        source_url: Optional[str] = None,
        author_name: Optional[str] = None,
        raw_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        ingest_result = AcquisitionIntakeService.ingest_item(
            db=self.db,
            owner_id=self.owner_id,
            source_channel="manual_input",
            raw_item={
                "platform": platform,
                "title": title,
                "content_text": content_text,
                "source_url": source_url,
                "author_name": author_name,
                "parse_status": "success",
                "risk_status": "review",
                "raw_payload": {
                    "tags": tags or [],
                    **(raw_payload or {}),
                },
            },
            platform=platform,
            keyword="",
            remark=note,
            auto_commit=True,
        )
        material = ingest_result["material"]
        return {
            "material_id": int(material.id),
            "status": str(material.status),
            "duplicate": bool(ingest_result.get("duplicate")),
            "reason": ingest_result.get("reason"),
            "material": material,
        }

    def ensure_material_knowledge(self, material_id: int):
        item = AcquisitionIntakeService.get_material_item(
            db=self.db,
            owner_id=self.owner_id,
            material_id=material_id,
            include_knowledge=True,
            include_chunks=True,
        )
        if item is None:
            raise ValueError("素材不存在")

        primary_doc = AcquisitionIntakeService.get_primary_knowledge_document(item)
        doc_mismatch = (
            primary_doc is None
            or (primary_doc.title or "") != (item.title or "")
            or (primary_doc.content_text or "") != (item.content_text or "")
        )
        if doc_mismatch:
            AcquisitionIntakeService.reindex_material(self.db, self.owner_id, material_id)
            item = AcquisitionIntakeService.get_material_item(
                db=self.db,
                owner_id=self.owner_id,
                material_id=material_id,
                include_knowledge=True,
                include_chunks=True,
            )
            if item is None:
                raise ValueError("素材不存在")

        return item

    async def generate_from_material(
        self,
        material_id: int,
        platform: str,
        account_type: Optional[str] = None,
        target_audience: Optional[str] = None,
        task_type: str = "rewrite",
    ) -> dict[str, Any]:
        material = self.ensure_material_knowledge(material_id)
        primary_doc = AcquisitionIntakeService.get_primary_knowledge_document(material)
        resolved_account_type = account_type or (primary_doc.account_type if primary_doc else "科普号")
        resolved_target_audience = target_audience or (primary_doc.target_audience if primary_doc else "泛人群")

        result = await AcquisitionIntakeService.generate(
            db=self.db,
            owner_id=self.owner_id,
            material_id=material.id,
            platform=platform,
            account_type=resolved_account_type,
            target_audience=resolved_target_audience,
            task_type=task_type,
            ai_service=self.ai_service,
        )
        return {
            **result,
            "material": material,
            "resolved_account_type": resolved_account_type,
            "resolved_target_audience": resolved_target_audience,
        }

    async def ingest_and_generate(
        self,
        source_platform: str,
        title: Optional[str],
        content_text: str,
        target_platform: str,
        account_type: Optional[str] = None,
        target_audience: Optional[str] = None,
        task_type: str = "rewrite",
        note: Optional[str] = None,
        tags: Optional[list[str]] = None,
        source_url: Optional[str] = None,
        author_name: Optional[str] = None,
        raw_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        ingest_result = self.ingest_manual_content(
            platform=source_platform,
            title=title,
            content_text=content_text,
            note=note,
            tags=tags,
            source_url=source_url,
            author_name=author_name,
            raw_payload=raw_payload,
        )
        generation_result = await self.generate_from_material(
            material_id=ingest_result["material_id"],
            platform=target_platform,
            account_type=account_type,
            target_audience=target_audience,
            task_type=task_type,
        )
        material = generation_result["material"]
        primary_doc = AcquisitionIntakeService.get_primary_knowledge_document(material)
        return {
            "material_id": int(material.id),
            "material_status": str(material.status),
            "cleaned_title": material.title,
            "cleaned_content_text": material.content_text,
            "knowledge_document_id": primary_doc.id if primary_doc else None,
            "generation_task_id": generation_result["generation_task_id"],
            "output_text": generation_result["output_text"],
            "references": generation_result.get("references") or [],
            "selected_variant": generation_result.get("selected_variant"),
            "resolved_account_type": generation_result["resolved_account_type"],
            "resolved_target_audience": generation_result["resolved_target_audience"],
        }
