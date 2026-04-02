import logging
import math
import re
from datetime import datetime
from typing import List, Optional

from app.models.models import MvpInboxItem
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QualityScreeningService:
    def __init__(self, db: Session, extraction_service=None):
        self.db = db
        self.extraction_service = extraction_service

    async def screen_item(self, inbox_item_id: int) -> dict:
        """单条质量筛选"""
        item = self.db.query(MvpInboxItem).filter(MvpInboxItem.id == inbox_item_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}

        if item.clean_status != "cleaned":
            return {"success": False, "error": "Item not cleaned yet"}

        try:
            # 1. Ollama 结构化抽取（可选）
            extraction = {}
            if self.extraction_service:
                extraction = await self.extraction_service.extract_structured(item.content or "", item.platform or "")

            # 2. 热度评分（0-25分）
            heat_score = self._calc_heat_score(item.like_count or 0, item.comment_count or 0, item.favorite_count or 0)

            # 3. 完整度评分（0-25分）
            completeness_score = self._calc_completeness_score(item)

            # 4. 可读性评分（0-25分）
            readability_score = self._calc_readability_score(item.content or "")

            # 5. 可仿写性评分（0-25分）
            rewritability_score = self._calc_rewritability_score(item, extraction)

            # 6. 综合质量分（0-100）
            quality_score = heat_score + completeness_score + readability_score + rewritability_score

            # 7. 风险评分（0-100，越高越危险）
            risk_score = self._calc_risk_score(item, extraction)

            # 8. 确定质量状态
            if quality_score >= 70:
                quality_status = "good"
            elif quality_score >= 40:
                quality_status = "normal"
            else:
                quality_status = "low"

            # 9. 确定风险状态
            if risk_score >= 60:
                risk_status = "high_risk"
            elif risk_score >= 30:
                risk_status = "low_risk"
            else:
                risk_status = "normal"

            # 10. 更新数据库
            item.quality_score = round(quality_score, 1)
            item.risk_score = round(risk_score, 1)
            item.quality_status = quality_status
            item.risk_status = risk_status
            item.screened_at = datetime.utcnow()

            # 11. 质量达标 + 风险可控 → 自动标记为可仿写
            if quality_score >= 70 and risk_score < 50:
                item.rewrite_ready = True

            self.db.commit()

            return {
                "success": True,
                "item_id": item.id,
                "quality_score": item.quality_score,
                "risk_score": item.risk_score,
                "quality_status": quality_status,
                "risk_status": risk_status,
                "extraction": extraction,
            }
        except Exception as e:
            logger.error(f"Screen failed for item {inbox_item_id}: {e}")
            return {"success": False, "error": str(e)}

    async def batch_screen(self, item_ids: List[int]) -> dict:
        """批量筛选"""
        results = {"total": len(item_ids), "success": 0, "failed": 0, "details": []}
        for item_id in item_ids:
            result = await self.screen_item(item_id)
            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1
            results["details"].append(result)
        return results

    def _calc_heat_score(self, likes: int, comments: int, favorites: int) -> float:
        """热度评分 0-25"""
        # 点赞权重0.4，评论权重0.4，收藏权重0.2
        raw = likes * 0.4 + comments * 0.4 + favorites * 0.2
        # 对数归一化，1000以上满分
        if raw <= 0:
            return 0
        normalized = min(math.log10(raw + 1) / 3, 1.0)  # log10(1001)≈3
        return round(normalized * 25, 1)

    def _calc_completeness_score(self, item) -> float:
        """完整度评分 0-25"""
        score = 0
        fields = [
            (item.title, 5),
            (item.content, 5),
            (item.author_name, 3),
            (item.platform, 3),
            (item.publish_time, 2),
            (item.url, 2),
            (item.like_count is not None and item.like_count > 0, 2),
            (item.comment_count is not None and item.comment_count > 0, 2),
            (item.source_id, 1),
        ]
        for field_val, weight in fields:
            if field_val:
                score += weight
        return min(score, 25)

    def _calc_readability_score(self, content: str) -> float:
        """可读性评分 0-25"""
        if not content:
            return 0
        score = 0
        # 长度适中（100-3000字最佳）
        length = len(content)
        if 100 <= length <= 3000:
            score += 10
        elif 50 <= length <= 5000:
            score += 5

        # 有段落分隔
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        if 2 <= len(paragraphs) <= 20:
            score += 8
        elif len(paragraphs) >= 1:
            score += 4

        # 有标点结构
        punctuation_count = len(re.findall(r"[。！？；，、.!?;,]", content))
        if punctuation_count >= 5:
            score += 7
        elif punctuation_count >= 2:
            score += 3

        return min(score, 25)

    def _calc_rewritability_score(self, item, extraction: dict) -> float:
        """可仿写性评分 0-25"""
        score = 0
        # 有明确主题
        if extraction.get("topic") and extraction["topic"] != "other":
            score += 8
        elif item.title:
            score += 4

        # 有钩子句
        if extraction.get("hook_sentence"):
            score += 6

        # 有痛点或解决方案
        if extraction.get("pain_point"):
            score += 4
        if extraction.get("solution"):
            score += 4

        # 有明确受众
        if extraction.get("audience"):
            score += 3

        return min(score, 25)

    def _calc_risk_score(self, item, extraction: dict) -> float:
        """风险评分 0-100，越高越危险"""
        score = 0
        # 基于 Ollama 抽取的风险点
        risk_points = extraction.get("risk_points", [])
        score += min(len(risk_points) * 15, 45)

        # 基于现有 risk_level
        if item.risk_level == "high":
            score += 30
        elif item.risk_level == "medium":
            score += 15

        # 简单关键词检测
        content = (item.content or "") + " " + (item.title or "")
        risk_keywords = [
            r"保证.*收益",
            r"稳赚",
            r"零风险",
            r"必赚",
            r"内部.*消息",
            r"绝密",
            r"百分百",
            r"日赚\d+",
            r"月入\d+万",
        ]
        for kw in risk_keywords:
            if re.search(kw, content):
                score += 10

        return min(score, 100)
