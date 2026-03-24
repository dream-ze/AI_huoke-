"""
素材中台 - CollectService
功能：链接解析（平台识别 + 元数据抓取）、自动分类/打标签、AI 爆款分析、素材库 CRUD。
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.models import ContentAsset

logger = logging.getLogger(__name__)

# 平台识别规则
PLATFORM_PATTERNS: Dict[str, List[str]] = {
    "xiaohongshu": [r"xiaohongshu\.com", r"xhslink\.com", r"xhs\.link"],
    "douyin": [r"douyin\.com", r"v\.douyin\.com", r"iesdouyin\.com"],
    "zhihu": [r"zhihu\.com"],
    "gongzhonghao": [r"mp\.weixin\.qq\.com"],
    "xianyu": [r"goofish\.com", r"xianyu\.taobao\.com"],
    "weibo": [r"weibo\.com", r"weibo\.cn"],
    "bilibili": [r"bilibili\.com", r"b23\.tv"],
    "kuaishou": [r"kuaishou\.com", r"gifshow\.com"],
    "toutiao": [r"toutiao\.com", r"toutiaoimg\.com"],
}

PLATFORM_LABELS: Dict[str, str] = {
    "xiaohongshu": "小红书",
    "douyin": "抖音",
    "zhihu": "知乎",
    "gongzhonghao": "公众号",
    "xianyu": "咸鱼",
    "weibo": "微博",
    "bilibili": "B站",
    "kuaishou": "快手",
    "toutiao": "头条",
    "wechat": "微信",
    "other": "其他",
}

# 浏览器请求头，降低被反爬拦截概率
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

# 行业分类关键词（贷款/金融获客场景）
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "额度提升": ["额度", "提额", "信用卡", "额度低", "提高额度", "白户"],
    "征信修复": ["征信", "花了", "修复征信", "查询次数", "逾期记录"],
    "负债优化": ["负债", "债务", "月供", "还款压力", "减轻负担", "一笔还清"],
    "职业认证": ["公务员", "教师", "职业", "单位证明", "在职", "央企", "国企"],
    "房贷公积金": ["房贷", "住房贷款", "公积金", "房产抵押", "按揭"],
    "车贷": ["车贷", "汽车贷款", "车抵押", "购车", "加油车"],
    "企业贷款": ["企业贷", "营业执照", "法人", "对公账户", "小微企业", "流水贷"],
    "引流获客": ["加微信", "私信我", "下方评论", "点击主页", "获客", "咨询"],
    "客户话术": ["话术", "聊天记录", "客户问", "问答", "怎么回复", "沟通技巧"],
    "爆款参考": ["爆款", "10w+", "10万+", "热搜", "涨粉", "爆了", "流量密码"],
}

ALL_CATEGORIES = list(CATEGORY_KEYWORDS.keys()) + ["其他"]


class CollectService:
    """素材中台核心服务。"""

    @staticmethod
    def detect_platform(url: str) -> str:
        url_lower = url.lower()
        for platform, patterns in PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return platform
        return "other"

    @staticmethod
    def _extract_meta(html: str, prop: str) -> str:
        patterns = [
            rf'<meta[^>]+property=["\']?{re.escape(prop)}["\']?[^>]+content=["\']([^"\'<>]*)["\']',
            rf'<meta[^>]+content=["\']([^"\'<>]*)["\'][^>]+property=["\']?{re.escape(prop)}["\']?',
            rf'<meta[^>]+name=["\']?{re.escape(prop)}["\']?[^>]+content=["\']([^"\'<>]*)["\']',
            rf'<meta[^>]+content=["\']([^"\'<>]*)["\'][^>]+name=["\']?{re.escape(prop)}["\']?',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_title(html: str) -> str:
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _clean_html_text(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = (
            text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&nbsp;", " ")
            .replace("&#xa0;", " ")
            .replace("&quot;", '"')
        )
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    async def fetch_url_meta(url: str) -> Tuple[bool, Dict[str, str]]:
        try:
            async with httpx.AsyncClient(
                timeout=12,
                follow_redirects=True,
                headers=_BROWSER_HEADERS,
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return False, {}
                html = resp.text

            title = (
                CollectService._extract_meta(html, "og:title")
                or CollectService._extract_meta(html, "twitter:title")
                or CollectService._extract_title(html)
            )
            description = (
                CollectService._extract_meta(html, "og:description")
                or CollectService._extract_meta(html, "description")
                or CollectService._extract_meta(html, "twitter:description")
            )
            author = (
                CollectService._extract_meta(html, "article:author")
                or CollectService._extract_meta(html, "og:author")
                or CollectService._extract_meta(html, "author")
            )
            site_name = CollectService._extract_meta(html, "og:site_name")

            return True, {
                "title": CollectService._clean_html_text(title)[:200],
                "description": CollectService._clean_html_text(description)[:2000],
                "author": CollectService._clean_html_text(author)[:100],
                "site_name": CollectService._clean_html_text(site_name)[:100],
            }

        except Exception as exc:
            logger.warning("fetch_url_meta failed for %r: %s", url, exc)
            return False, {}

    @staticmethod
    def auto_category(title: str, content: str) -> str:
        text = (title + " " + (content or "")).lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return cat
        return "其他"

    @staticmethod
    def get_list(
        db: Session,
        user_id: int,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        is_viral: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ContentAsset]:
        query = db.query(ContentAsset).filter(ContentAsset.owner_id == user_id)
        if platform and platform != "all":
            query = query.filter(ContentAsset.platform == platform)
        if category and category != "all":
            query = query.filter(ContentAsset.category == category)
        if is_viral is not None:
            query = query.filter(ContentAsset.is_viral == is_viral)
        if search:
            query = query.filter(
                or_(
                    ContentAsset.title.ilike(f"%{search}%"),
                    ContentAsset.content.ilike(f"%{search}%"),
                )
            )
        return query.order_by(desc(ContentAsset.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_stats(db: Session, user_id: int) -> Dict[str, Any]:
        total = db.query(ContentAsset).filter(ContentAsset.owner_id == user_id).count()
        viral = db.query(ContentAsset).filter(
            ContentAsset.owner_id == user_id,
            ContentAsset.is_viral.is_(True),
        ).count()

        by_platform = (
            db.query(ContentAsset.platform, func.count(ContentAsset.id).label("cnt"))
            .filter(ContentAsset.owner_id == user_id)
            .group_by(ContentAsset.platform)
            .all()
        )
        by_category = (
            db.query(ContentAsset.category, func.count(ContentAsset.id).label("cnt"))
            .filter(ContentAsset.owner_id == user_id)
            .group_by(ContentAsset.category)
            .all()
        )

        return {
            "total": total,
            "viral_count": viral,
            "by_platform": {platform: count for platform, count in by_platform if platform},
            "by_category": {cat: count for cat, count in by_category if cat},
        }

    @staticmethod
    async def analyze_with_ai(
        content: ContentAsset,
        ai_service,
        force_cloud: bool = False,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        platform_label = PLATFORM_LABELS.get(content.platform, content.platform)
        body = (content.content or "")[:2000]

        prompt = f"""你是内容运营专家，专注贷款/金融产品推广。
请分析以下内容，只返回 JSON，不要输出任何解释文字。

平台: {platform_label}
标题: {content.title}
正文: {body}

返回格式（严格 JSON）:
{{
  "tags": ["标签1","标签2","标签3"],
  "category": "分类名（从以下选一个最合适的：额度提升/征信修复/负债优化/职业认证/房贷公积金/车贷/企业贷款/引流获客/客户话术/爆款参考/其他）",
  "heat_score": 75,
  "is_viral": false,
  "viral_reasons": ["理由1（如：标题情绪强烈）"],
  "key_selling_points": ["卖点1","卖点2"],
  "rewrite_hints": "简述：该如何改写才能提升转化或降低风险",
  "viral_potential_score": 68,
  "spread_potential": "高/中/低",
  "user_profile": "目标用户画像，如：25-35岁上班族，有贷款需求",
  "emotion_tone": "情绪调性，如：焦虑共鸣/积极励志/理性分析",
  "content_structure": ["结构元素1（如：痛点开头）","结构元素2","结构元素3"],
  "reusable_elements": ["可复用元素1（如：具体数字举例）","可复用元素2"],
  "risk_warnings": ["风险点1（如：含绝对化承诺）","风险点2"]
}}"""

        try:
            use_cloud = force_cloud or ai_service.use_cloud
            result_text = await ai_service.call_llm(
                prompt=prompt,
                system_prompt="你是专业内容运营分析师，只输出 JSON，不输出任何解释。",
                use_cloud=use_cloud,
                user_id=user_id,
                scene="collect_analyze",
            )
            matched = re.search(r"\{.*\}", result_text, re.DOTALL)
            if matched:
                data = json.loads(matched.group(0))
                return {
                    "tags": [str(tag) for tag in data.get("tags", [])][:10],
                    "category": str(data.get("category", "其他"))[:64],
                    "heat_score": float(data.get("heat_score", 0)),
                    "is_viral": bool(data.get("is_viral", False)),
                    "viral_reasons": [str(reason) for reason in data.get("viral_reasons", [])][:5],
                    "key_selling_points": [str(point) for point in data.get("key_selling_points", [])][:5],
                    "rewrite_hints": str(data.get("rewrite_hints", ""))[:500],
                    "viral_potential_score": float(data.get("viral_potential_score", 0)),
                    "spread_potential": str(data.get("spread_potential", ""))[:16],
                    "user_profile": str(data.get("user_profile", ""))[:200],
                    "emotion_tone": str(data.get("emotion_tone", ""))[:64],
                    "content_structure": [str(e) for e in data.get("content_structure", [])][:8],
                    "reusable_elements": [str(e) for e in data.get("reusable_elements", [])][:8],
                    "risk_warnings": [str(w) for w in data.get("risk_warnings", [])][:5],
                }
        except Exception as exc:
            logger.error("AI analyze failed for content_id=%s: %s", content.id, exc)

        auto_cat = CollectService.auto_category(content.title, content.content or "")
        return {
            "tags": [],
            "category": auto_cat,
            "heat_score": 0.0,
            "is_viral": False,
            "viral_reasons": [],
            "key_selling_points": [],
            "rewrite_hints": "",
            "viral_potential_score": 0.0,
            "spread_potential": "",
            "user_profile": "",
            "emotion_tone": "",
            "content_structure": [],
            "reusable_elements": [],
            "risk_warnings": [],
        }

    # ── 内容去重 ──────────────────────────────
    @staticmethod
    def check_duplicate(
        db: Session,
        user_id: int,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        similarity_threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """
        基于 URL 精确匹配和文本相似度检查内容是否重复。
        返回 {is_duplicate, duplicate_id, similarity_score, method}。
        """
        # 1. URL 精确匹配
        if source_url:
            existing = db.query(ContentAsset).filter(
                ContentAsset.owner_id == user_id,
                ContentAsset.source_url == source_url,
            ).first()
            if existing:
                return {
                    "is_duplicate": True,
                    "duplicate_id": existing.id,
                    "similarity_score": 1.0,
                    "method": "url_exact",
                }

        # 2. 标题完全匹配
        if title:
            existing = db.query(ContentAsset).filter(
                ContentAsset.owner_id == user_id,
                ContentAsset.title == title,
            ).first()
            if existing:
                return {
                    "is_duplicate": True,
                    "duplicate_id": existing.id,
                    "similarity_score": 1.0,
                    "method": "title_exact",
                }

        # 3. 文本相似度（简易 n-gram 特征比对，无需外部库）
        def _ngram_set(t: str, c: str, n: int = 3) -> set:
            # 分别限长，确保标题和正文都有代表性
            combined = t[:200] + " " + c[:300]
            combined = re.sub(r"\s+", " ", combined).strip()
            return {combined[i:i + n] for i in range(len(combined) - n + 1)} if len(combined) >= n else set()

        query_ngrams = _ngram_set(title, content)
        if not query_ngrams:
            return {"is_duplicate": False, "duplicate_id": None, "similarity_score": 0.0, "method": "none"}

        # 只检查最近 200 条记录，避免全表扫描
        recent_items = (
            db.query(ContentAsset)
            .filter(ContentAsset.owner_id == user_id)
            .order_by(desc(ContentAsset.created_at))
            .limit(200)
            .all()
        )

        best_match_id = None
        best_score = 0.0
        for item in recent_items:
            item_ngrams = _ngram_set(item.title or "", item.content or "")
            if not item_ngrams:
                continue
            intersection = len(query_ngrams & item_ngrams)
            union = len(query_ngrams | item_ngrams)
            score = intersection / union if union > 0 else 0.0
            if score > best_score:
                best_score = score
                best_match_id = item.id

        is_dup = best_score >= similarity_threshold
        return {
            "is_duplicate": is_dup,
            "duplicate_id": best_match_id if is_dup else None,
            "similarity_score": round(best_score, 4),
            "method": "text_similarity",
        }
