"""
爆款内容采集分析中心 – InsightService
五层闭环：采集入库 → 内容清洗 → AI分析 → 主题/账号聚类 → 检索召回
"""
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.models.models import (
    InsightAuthorProfile,
    InsightCollectTask,
    InsightContentItem,
    InsightTopic,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 互动分计算权重
# ──────────────────────────────────────────────
_ENGAGEMENT_WEIGHTS = {
    "collect_count": 3.0,
    "comment_count": 2.5,
    "share_count": 2.0,
    "like_count": 1.0,
    "view_count": 0.05,
}

# 热度分层阈值（互动分）
_HEAT_TIERS = [
    ("viral", 500),
    ("hot", 200),
    ("warm", 80),
    ("normal", 0),
]


def _calc_engagement(item: InsightContentItem) -> float:
    score = 0.0
    for field, weight in _ENGAGEMENT_WEIGHTS.items():
        score += (getattr(item, field, 0) or 0) * weight
    return round(score, 2)


def _calc_heat_tier(score: float) -> Tuple[str, bool]:
    for tier, threshold in _HEAT_TIERS:
        if score >= threshold:
            return tier, tier in ("hot", "viral")
    return "normal", False


class InsightService:

    # ─────────────────────────────────────────
    # 主题管理
    # ─────────────────────────────────────────

    @staticmethod
    def create_topic(db: Session, name: str, **kwargs) -> InsightTopic:
        existing = db.query(InsightTopic).filter(InsightTopic.name == name).first()
        if existing:
            return existing
        topic = InsightTopic(name=name, **kwargs)
        db.add(topic)
        db.commit()
        db.refresh(topic)
        return topic

    @staticmethod
    def list_topics(db: Session) -> List[InsightTopic]:
        return db.query(InsightTopic).order_by(desc(InsightTopic.content_count)).all()

    @staticmethod
    def get_topic(db: Session, topic_id: int) -> Optional[InsightTopic]:
        return db.query(InsightTopic).filter(InsightTopic.id == topic_id).first()

    @staticmethod
    def get_or_create_topic_by_name(db: Session, name: str) -> Optional[InsightTopic]:
        if not name:
            return None
        t = db.query(InsightTopic).filter(InsightTopic.name == name).first()
        if not t:
            t = InsightTopic(name=name)
            db.add(t)
            db.commit()
            db.refresh(t)
        return t

    # ─────────────────────────────────────────
    # 账号档案管理
    # ─────────────────────────────────────────

    @staticmethod
    def upsert_author(
        db: Session,
        platform: str,
        author_name: str,
        author_profile_url: Optional[str] = None,
        fans_count: Optional[int] = None,
        account_positioning: Optional[str] = None,
    ) -> InsightAuthorProfile:
        author = (
            db.query(InsightAuthorProfile)
            .filter(
                InsightAuthorProfile.platform == platform,
                InsightAuthorProfile.author_name == author_name,
            )
            .first()
        )
        if not author:
            author = InsightAuthorProfile(
                platform=platform,
                author_name=author_name,
                author_profile_url=author_profile_url,
                fans_count=fans_count,
                account_type=account_positioning,
            )
            db.add(author)
            db.commit()
            db.refresh(author)
        else:
            if fans_count is not None:
                author.fans_count = fans_count
            if author_profile_url:
                author.author_profile_url = author_profile_url
            if account_positioning:
                author.account_type = account_positioning
            db.commit()
        return author

    @staticmethod
    def refresh_author_stats(db: Session, author_id: int) -> None:
        """重新统计账号的爆款率、平均互动分、主题覆盖、风格分布"""
        items = (
            db.query(InsightContentItem)
            .filter(InsightContentItem.author_id == author_id)
            .all()
        )
        if not items:
            return

        author = db.query(InsightAuthorProfile).filter(InsightAuthorProfile.id == author_id).first()
        if not author:
            return

        hot_count = sum(1 for i in items if i.is_hot)
        avg_eng = sum(i.engagement_score for i in items) / len(items)

        # 主题覆盖
        topic_coverage: Dict[str, int] = {}
        for item in items:
            if item.topic:
                topic_coverage[item.topic.name] = topic_coverage.get(item.topic.name, 0) + 1

        # 风格分布
        style_summary: Dict[str, int] = {}
        for item in items:
            if item.tone_style:
                style_summary[item.tone_style] = style_summary.get(item.tone_style, 0) + 1

        # 主要主题
        if topic_coverage:
            primary_topic_name = max(topic_coverage, key=lambda k: topic_coverage[k])
            primary_topic = db.query(InsightTopic).filter(InsightTopic.name == primary_topic_name).first()
            if primary_topic:
                author.primary_topic_id = primary_topic.id

        author.viral_rate = round(hot_count / len(items), 4)
        author.avg_engagement = round(avg_eng, 2)
        author.topic_coverage = topic_coverage
        author.style_summary = style_summary
        db.commit()

    # ─────────────────────────────────────────
    # 内容入库
    # ─────────────────────────────────────────

    @staticmethod
    def ingest_item(
        db: Session,
        owner_id: int,
        platform: str,
        title: str,
        body_text: str,
        source_url: Optional[str] = None,
        content_type: str = "post",
        author_name: Optional[str] = None,
        author_profile_url: Optional[str] = None,
        fans_count: Optional[int] = None,
        account_positioning: Optional[str] = None,
        publish_time: Optional[datetime] = None,
        like_count: int = 0,
        comment_count: int = 0,
        share_count: int = 0,
        collect_count: int = 0,
        view_count: int = 0,
        topic_name: Optional[str] = None,
        audience_tags: Optional[List[str]] = None,
        manual_note: Optional[str] = None,
        source_type: str = "manual",
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> InsightContentItem:
        # 去重检查（同平台+同URL）
        if source_url:
            existing = (
                db.query(InsightContentItem)
                .filter(
                    InsightContentItem.owner_id == owner_id,
                    InsightContentItem.source_url == source_url,
                )
                .first()
            )
            if existing:
                return existing

        # 关联主题
        topic = None
        if topic_name:
            topic = InsightService.get_or_create_topic_by_name(db, topic_name)

        # 账号档案
        author_profile = None
        if author_name:
            author_profile = InsightService.upsert_author(
                db, platform, author_name,
                author_profile_url=author_profile_url,
                fans_count=fans_count,
                account_positioning=account_positioning,
            )

        item = InsightContentItem(
            owner_id=owner_id,
            platform=platform,
            source_url=source_url,
            content_type=content_type,
            title=title,
            body_text=body_text,
            author_name=author_name,
            author_profile_url=author_profile_url,
            author_platform_id=author_profile_url,
            fans_count=fans_count,
            account_positioning=account_positioning,
            publish_time=publish_time,
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            collect_count=collect_count,
            view_count=view_count,
            audience_tags=audience_tags or [],
            manual_note=manual_note,
            source_type=source_type,
            raw_payload=raw_payload,
            topic_id=topic.id if topic else None,
            author_id=author_profile.id if author_profile else None,
        )

        # 计算互动分及热度分层
        item.engagement_score = _calc_engagement(item)
        item.heat_tier, item.is_hot = _calc_heat_tier(item.engagement_score)

        db.add(item)
        db.commit()
        db.refresh(item)

        # 更新主题内容计数
        if topic:
            topic.content_count = (
                db.query(InsightContentItem)
                .filter(InsightContentItem.topic_id == topic.id)
                .count()
            )
            db.commit()

        return item

    @staticmethod
    def batch_ingest(
        db: Session,
        owner_id: int,
        items_data: List[Dict[str, Any]],
    ) -> Tuple[int, int]:
        """批量入库，返回 (成功数, 跳过数)"""
        ok, skipped = 0, 0
        for data in items_data:
            try:
                InsightService.ingest_item(db, owner_id, **data)
                ok += 1
            except Exception as e:
                logger.warning(f"batch ingest skip: {e}")
                skipped += 1
        return ok, skipped

    # ─────────────────────────────────────────
    # 查询
    # ─────────────────────────────────────────

    @staticmethod
    def list_items(
        db: Session,
        owner_id: int,
        platform: Optional[str] = None,
        topic_id: Optional[int] = None,
        is_hot: Optional[bool] = None,
        heat_tier: Optional[str] = None,
        ai_analyzed: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[InsightContentItem]:
        q = db.query(InsightContentItem).filter(InsightContentItem.owner_id == owner_id)
        if platform and platform != "all":
            q = q.filter(InsightContentItem.platform == platform)
        if topic_id:
            q = q.filter(InsightContentItem.topic_id == topic_id)
        if is_hot is not None:
            q = q.filter(InsightContentItem.is_hot == is_hot)
        if heat_tier:
            q = q.filter(InsightContentItem.heat_tier == heat_tier)
        if ai_analyzed is not None:
            q = q.filter(InsightContentItem.ai_analyzed == ai_analyzed)
        if search:
            q = q.filter(
                or_(
                    InsightContentItem.title.ilike(f"%{search}%"),
                    InsightContentItem.body_text.ilike(f"%{search}%"),
                )
            )
        return q.order_by(desc(InsightContentItem.engagement_score)).offset(skip).limit(limit).all()

    @staticmethod
    def get_item(db: Session, item_id: int, owner_id: int) -> Optional[InsightContentItem]:
        return (
            db.query(InsightContentItem)
            .filter(InsightContentItem.id == item_id, InsightContentItem.owner_id == owner_id)
            .first()
        )

    @staticmethod
    def get_stats(db: Session, owner_id: int) -> Dict[str, Any]:
        total = db.query(InsightContentItem).filter(InsightContentItem.owner_id == owner_id).count()
        hot = db.query(InsightContentItem).filter(
            InsightContentItem.owner_id == owner_id,
            InsightContentItem.is_hot == True,
        ).count()
        analyzed = db.query(InsightContentItem).filter(
            InsightContentItem.owner_id == owner_id,
            InsightContentItem.ai_analyzed == True,
        ).count()

        by_platform = (
            db.query(InsightContentItem.platform, func.count(InsightContentItem.id))
            .filter(InsightContentItem.owner_id == owner_id)
            .group_by(InsightContentItem.platform)
            .all()
        )
        by_heat = (
            db.query(InsightContentItem.heat_tier, func.count(InsightContentItem.id))
            .filter(InsightContentItem.owner_id == owner_id)
            .group_by(InsightContentItem.heat_tier)
            .all()
        )
        topics = InsightService.list_topics(db)

        return {
            "total": total,
            "hot_count": hot,
            "analyzed_count": analyzed,
            "by_platform": {p: c for p, c in by_platform if p},
            "by_heat_tier": {t: c for t, c in by_heat if t},
            "topic_count": len(topics),
        }

    # ─────────────────────────────────────────
    # AI 分析层
    # ─────────────────────────────────────────

    @staticmethod
    async def analyze_with_ai(
        db: Session,
        item: InsightContentItem,
        ai_service,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        调用 LLM 深度拆解内容结构 → 存回数据库
        返回分析字段字典
        """
        body_excerpt = (item.body_text or "")[:2500]
        prompt = f"""你是内容运营专家，专注金融/贷款产品社媒内容分析。
分析以下内容，只返回 JSON，不输出任何解释。

平台: {item.platform}
标题: {item.title}
正文: {body_excerpt}
互动数据: 点赞={item.like_count} 评论={item.comment_count} 收藏={item.collect_count} 分享={item.share_count}

返回格式（严格JSON）:
{{
  "topic_name": "最匹配主题（征信查询多/负债高/个体户经营贷/上班族信贷/企业主融资/资料准备/面签问题/申请被拒/债务优化/引流获客/其他）",
  "audience_tags": ["上班族","查询多"],
  "content_type": "避坑提醒型",
  "structure_type": "问题-原因-建议",
  "hook_type": "问题开头",
  "tone_style": "自然口语风",
  "cta_type": "评论引导",
  "emotion_level": 4,
  "info_density": 3,
  "title_formula": "X个坑 | 你以为XX但其实XX",
  "pain_points": ["征信查多被拒贷","不知道查多会影响审批"],
  "highlights": ["标题直击误区","结构清晰适合收藏","信息密度高"],
  "is_hot": true,
  "risk_level": "low",
  "risk_flags": [],
  "content_summary": "一句话摘要（50字内）"
}}"""

        try:
            result_text = await ai_service.call_llm(
                prompt=prompt,
                system_prompt="你是专业内容运营分析师，只输出JSON，不输出任何解释。",
                use_cloud=ai_service.use_cloud,
                user_id=user_id,
                scene="insight_analyze",
            )
            m = re.search(r'\{.*\}', result_text, re.DOTALL)
            if not m:
                raise ValueError("AI 未返回有效 JSON")
            data = json.loads(m.group(0))
        except Exception as e:
            logger.error(f"insight AI analyze failed id={item.id}: {e}")
            data = {}

        # 关联主题
        topic_name = data.get("topic_name") or ""
        topic = None
        if topic_name:
            topic = InsightService.get_or_create_topic_by_name(db, topic_name)

        # 重新计算热度（AI 可能修正判断）
        is_hot_ai = bool(data.get("is_hot", item.is_hot))

        # 写回数据库
        item.topic_id = topic.id if topic else item.topic_id
        item.audience_tags = [str(t) for t in data.get("audience_tags", item.audience_tags)][:10]
        item.content_type = str(data.get("content_type", item.content_type))[:32]
        item.structure_type = str(data.get("structure_type", ""))[:64]
        item.hook_type = str(data.get("hook_type", ""))[:64]
        item.tone_style = str(data.get("tone_style", ""))[:64]
        item.cta_type = str(data.get("cta_type", ""))[:64]
        item.emotion_level = int(data.get("emotion_level", 3))
        item.info_density = int(data.get("info_density", 3))
        item.title_formula = str(data.get("title_formula", ""))[:200]
        item.pain_points = [str(p) for p in data.get("pain_points", [])][:8]
        item.highlights = [str(h) for h in data.get("highlights", [])][:6]
        item.is_hot = is_hot_ai
        if is_hot_ai and item.heat_tier == "normal":
            item.heat_tier = "hot"
        item.risk_level = str(data.get("risk_level", "low"))
        item.risk_flags = [str(f) for f in data.get("risk_flags", [])][:6]
        item.content_summary = str(data.get("content_summary", ""))[:200]
        item.ai_analysis = data
        item.ai_analyzed = True
        db.commit()

        # 更新主题知识库（聚合常见标题模板/痛点/结构）
        if topic:
            InsightService._update_topic_knowledge(db, topic)

        # 更新账号档案
        if item.author_id:
            InsightService.refresh_author_stats(db, item.author_id)

        return {
            "content_id": item.id,
            "topic_name": topic_name,
            "audience_tags": item.audience_tags,
            "structure_type": item.structure_type or "",
            "hook_type": item.hook_type or "",
            "tone_style": item.tone_style or "",
            "cta_type": item.cta_type or "",
            "emotion_level": item.emotion_level,
            "info_density": item.info_density,
            "title_formula": item.title_formula or "",
            "pain_points": item.pain_points,
            "highlights": item.highlights,
            "is_hot": item.is_hot,
            "heat_tier": item.heat_tier,
            "risk_level": item.risk_level,
            "risk_flags": item.risk_flags,
            "content_summary": item.content_summary or "",
        }

    @staticmethod
    def _update_topic_knowledge(db: Session, topic: InsightTopic) -> None:
        """从已分析内容中提取并聚合主题知识库字段"""
        items = (
            db.query(InsightContentItem)
            .filter(
                InsightContentItem.topic_id == topic.id,
                InsightContentItem.ai_analyzed == True,
            )
            .order_by(desc(InsightContentItem.engagement_score))
            .limit(50)
            .all()
        )
        if not items:
            return

        # 取互动分最高 Top-10 的标题
        top_titles = [i.title for i in items[:10] if i.title]

        # 聚合痛点（去重保留频次最高）
        pain_counter: Dict[str, int] = {}
        for i in items:
            for p in (i.pain_points or []):
                pain_counter[p] = pain_counter.get(p, 0) + 1
        top_pains = sorted(pain_counter, key=lambda k: -pain_counter[k])[:10]

        # 聚合结构模板
        struct_counter: Dict[str, int] = {}
        for i in items:
            if i.structure_type:
                struct_counter[i.structure_type] = struct_counter.get(i.structure_type, 0) + 1
        top_structs = sorted(struct_counter, key=lambda k: -struct_counter[k])[:5]

        # 聚合 CTA
        cta_counter: Dict[str, int] = {}
        for i in items:
            if i.cta_type:
                cta_counter[i.cta_type] = cta_counter.get(i.cta_type, 0) + 1
        top_ctas = sorted(cta_counter, key=lambda k: -cta_counter[k])[:5]

        topic.common_titles = top_titles
        topic.common_pain_points = top_pains
        topic.common_structures = top_structs
        topic.common_ctas = top_ctas
        topic.content_count = (
            db.query(InsightContentItem)
            .filter(InsightContentItem.topic_id == topic.id)
            .count()
        )
        db.commit()

    # ─────────────────────────────────────────
    # 检索召回层
    # ─────────────────────────────────────────

    @staticmethod
    def retrieve_for_generation(
        db: Session,
        owner_id: int,
        platform: str,
        topic_name: Optional[str] = None,
        audience_tags: Optional[List[str]] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        给文案生成模块提供结构化参考特征。
        只返回分析结论，不返回原文，防止直接抄写。
        增强版：引入时效性权重和质量评分综合排序。
        """
        q = (
            db.query(InsightContentItem)
            .filter(
                InsightContentItem.owner_id == owner_id,
                InsightContentItem.platform == platform,
                InsightContentItem.ai_analyzed == True,
            )
        )
        if topic_name:
            topic = db.query(InsightTopic).filter(InsightTopic.name == topic_name).first()
            if topic:
                q = q.filter(InsightContentItem.topic_id == topic.id)

        if audience_tags:
            # JSON 数组字段模糊匹配（SQLite 和 PostgreSQL 均支持 CAST+like）
            for tag in audience_tags[:3]:
                q = q.filter(InsightContentItem.audience_tags.cast(str).ilike(f"%{tag}%"))

        # 拉取更多候选（3x），然后在 Python 层做综合排序
        candidates = q.order_by(desc(InsightContentItem.engagement_score)).limit(limit * 6).all()

        if not candidates:
            # 降级：不限平台
            candidates = (
                db.query(InsightContentItem)
                .filter(
                    InsightContentItem.owner_id == owner_id,
                    InsightContentItem.ai_analyzed == True,
                )
                .order_by(desc(InsightContentItem.engagement_score))
                .limit(limit * 2)
                .all()
            )

        # ── 综合评分排序：互动分 × 时效权重 ──────────────
        now = datetime.utcnow()

        def _composite_score(item: InsightContentItem) -> float:
            eng = float(item.engagement_score or 0)
            # 时效权重：30天内满分，之后线性衰减至90天归零
            age_days = 0
            collect_time = item.collect_time
            if collect_time is not None:
                if collect_time.tzinfo is not None:
                    collect_time = collect_time.replace(tzinfo=None)
                age_days = max((now - collect_time).days, 0)
            recency_weight = max(1.0 - age_days / 90.0, 0.1)
            quality_weight = 1.2 if item.is_hot else 1.0
            return eng * recency_weight * quality_weight

        items = sorted(candidates, key=_composite_score, reverse=True)[:limit * 3]

        title_examples = list({i.title for i in items if i.title})[:limit]
        structure_examples = list({i.structure_type for i in items if i.structure_type})[:5]
        hook_examples = list({i.hook_type for i in items if i.hook_type})[:5]
        cta_examples = list({i.cta_type for i in items if i.cta_type})[:5]
        pain_examples: List[str] = []
        for i in items:
            for p in (i.pain_points or []):
                if p not in pain_examples:
                    pain_examples.append(p)
            if len(pain_examples) >= 10:
                break

        # 风格汇总（按频次排序）
        style_counts: Dict[str, int] = {}
        for i in items:
            if i.tone_style:
                style_counts[i.tone_style] = style_counts.get(i.tone_style, 0) + 1
        style_summary = "、".join(
            f"{k}({v}篇)" for k, v in sorted(style_counts.items(), key=lambda x: -x[1])
        ) if style_counts else "暂无风格数据"

        # 质量摘要：爆款率
        hot_count = sum(1 for i in items if i.is_hot)
        quality_note = (
            f"参考素材中有 {hot_count}/{len(items)} 篇爆款，互动质量{'较高' if hot_count >= 2 else '一般'}"
            if items else "暂无质量数据"
        )

        # 风险提醒
        topic_obj = None
        if topic_name:
            topic_obj = db.query(InsightTopic).filter(InsightTopic.name == topic_name).first()
        risk_reminder = (topic_obj.risk_notes if topic_obj and topic_obj.risk_notes else
                         "请避免夸大收益、宣传高额贷款、使用'一定批/100%下款'等违规表达")

        return {
            "topic_name": topic_name,
            "platform": platform,
            "title_examples": title_examples,
            "structure_examples": structure_examples,
            "hook_examples": hook_examples,
            "cta_examples": cta_examples,
            "pain_point_examples": pain_examples[:10],
            "style_summary": style_summary,
            "quality_note": quality_note,
            "risk_reminder": risk_reminder,
            "reference_count": len(items),
        }

    # ─────────────────────────────────────────
    # 删除
    # ─────────────────────────────────────────

    @staticmethod
    def delete_item(db: Session, item_id: int, owner_id: int) -> bool:
        item = InsightService.get_item(db, item_id, owner_id)
        if not item:
            return False
        # 更新主题计数
        topic_id = item.topic_id
        db.delete(item)
        db.commit()
        if topic_id:
            topic = db.query(InsightTopic).filter(InsightTopic.id == topic_id).first()
            if topic:
                topic.content_count = max(0, topic.content_count - 1)
                db.commit()
        return True
