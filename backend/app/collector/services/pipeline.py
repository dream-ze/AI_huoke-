from __future__ import annotations

from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
import html
import hashlib
import re
from typing import Any, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CollectTask,
    EmployeeLinkSubmission,
    GenerationTask,
    KnowledgeChunk,
    KnowledgeDocument,
    MaterialItem,
    NormalizedContent,
    PromptTemplate,
    Rule,
    SourceContent,
)
from app.services.compliance_service import ComplianceService
from app.collector.services.browser_client import BrowserCollectorClient


class AcquisitionIntakeService:
    """First-principles acquisition pipeline: source -> normalized -> material -> knowledge -> generation."""

    _TARGET_TERMS = ["贷款", "资金", "征信", "负债", "网贷", "融资", "周转"]
    _INTENT_TERMS = ["怎么办", "求助", "急需", "有没有", "推荐", "私信", "加微", "联系"]
    _STATUS_TRANSITIONS: dict[str, set[str]] = {
        "pending": {"review", "discard"},
        "review": {"pending", "discard"},
        "discard": {"pending", "review"},
    }
    _ACCOUNT_TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("顾问号", ("方案", "怎么做", "怎么办", "顾问", "办理", "测额")),
        ("法务号", ("法务", "协商", "律师", "诉讼", "法条")),
        ("引流号", ("私信", "加微信", "主页", "评论区", "咨询我")),
        ("科普号", ("科普", "知识", "解析", "注意", "避坑")),
    ]
    _AUDIENCE_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("负债逾期", ("逾期", "负债", "催收", "协商", "延期")),
        ("征信问题", ("征信", "查询多", "花户", "黑户", "征信花")),
        ("创业周转", ("创业", "周转", "流水", "企业贷", "营业执照")),
        ("宝妈", ("宝妈", "带娃", "全职妈妈", "母婴")),
    ]
    _CONTENT_TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("案例", ("案例", "真实经历", "成功", "上岸")),
        ("评论洞察", ("评论区", "网友", "留言", "评论")),
        ("规则说明", ("规则", "要求", "条件", "门槛")),
    ]
    _TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("车贷", ("车贷", "按揭车", "绿本", "解押", "提前还款")),
        ("房贷", ("房贷", "公积金", "首付", "月供", "商贷")),
        ("网贷", ("网贷", "借呗", "花呗", "360借条", "微粒贷")),
        ("信用卡", ("信用卡", "账单", "分期", "停息挂账", "逾期")),
        ("征信", ("征信", "查询次数", "风控", "黑户", "白户")),
    ]
    _INTENT_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("求助", ("怎么办", "咋办", "怎么解决", "求助", "能不能")),
        ("被拒", ("被拒", "拒贷", "下不来", "审核不过")),
        ("避坑", ("避坑", "套路", "被骗", "千万别", "后悔")),
        ("经验分享", ("攻略", "经验", "分享", "终于懂了", "提前还款")),
        ("转化引导", ("推荐", "中介", "私信", "咨询我", "联系我")),
    ]
    _CROWD_RULES: list[tuple[str, tuple[str, ...]]] = [
        ("负债人群", ("负债", "欠款", "还不上", "逾期")),
        ("征信问题人群", ("征信花", "大数据花", "查询多", "白户", "黑户")),
        ("购车人群", ("买车", "提车", "按揭车", "车贷")),
        ("购房人群", ("买房", "首付", "上车", "房贷")),
    ]
    _HIGH_RISK_TERMS: tuple[str, ...] = (
        "套现",
        "洗白",
        "黑户秒过",
        "包装资料",
        "刷流水",
        "百分百下款",
        "无视风控",
        "无视征信",
        "内部渠道",
    )
    _MEDIUM_RISK_TERMS: tuple[str, ...] = (
        "私信",
        "加v",
        "加微",
        "VX",
        "微信",
        "联系我",
        "中介",
    )
    _DEFAULT_COMPLIANCE_BLOCK_SCORE: int = 60
    _NOISE_LINE_PATTERNS: tuple[str, ...] = (
        r"^(展开|收起|全文|阅读全文|查看全文|原文|复制链接|网页链接)$",
        r"^(点赞|收藏|分享|评论|转发|关注|私信|举报|置顶)$",
        r"^(作者|发布时间|来源|标签|话题|IP属地|地址)[:：].{0,30}$",
        r"^(https?://\S+)$",
        r"^(#\S+\s*){1,8}$",
    )

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            text = value.strip().replace("Z", "+00:00")
            if not text:
                return None
            try:
                return datetime.fromisoformat(text)
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _strip_html(value: str) -> str:
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", value, flags=re.IGNORECASE | re.DOTALL)
        return re.sub(r"<[^>]+>", " ", text)

    @staticmethod
    def _clean_inline_text(value: Any) -> str:
        text = html.unescape(AcquisitionIntakeService._normalize_text(value))
        text = (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\u3000", " ")
            .replace("\xa0", " ")
            .replace("\u200b", " ")
        )
        text = AcquisitionIntakeService._strip_html(text)
        return text

    @staticmethod
    def _clean_title_text(value: Any) -> str:
        text = AcquisitionIntakeService._clean_inline_text(value)
        text = re.sub(r"\s+", " ", text).strip(" \n\t-_|")
        text = re.sub(r"([!?！？。])\1{2,}", r"\1\1", text)
        return text[:255]

    @staticmethod
    def _is_noise_line(value: str) -> bool:
        text = value.strip()
        if not text:
            return True
        for pattern in AcquisitionIntakeService._NOISE_LINE_PATTERNS:
            if re.fullmatch(pattern, text, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _clean_content_text(value: Any) -> str:
        text = AcquisitionIntakeService._clean_inline_text(value)
        if not text:
            return ""

        normalized_lines: list[str] = []
        previous_line = ""
        for raw_line in text.split("\n"):
            line = re.sub(r"\s+", " ", raw_line).strip()
            if AcquisitionIntakeService._is_noise_line(line):
                continue
            if line == previous_line:
                continue
            normalized_lines.append(line)
            previous_line = line

        body = "\n".join(normalized_lines).strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = re.sub(r"([!?！？。])\1{2,}", r"\1\1", body)
        return body

    @staticmethod
    def _split_keywords(keyword: str) -> list[str]:
        text = keyword.strip()
        if not text:
            return []
        return [seg.strip() for seg in re.split(r"[\s,，;；|/]+", text) if seg.strip()]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        cleaned = AcquisitionIntakeService._normalize_text(text).lower()
        if not cleaned:
            return []

        tokens: list[str] = []
        for token in re.findall(r"[a-z0-9]{2,}|[\u4e00-\u9fff]{2,}", cleaned):
            tokens.append(token)
            if re.fullmatch(r"[\u4e00-\u9fff]{2,}", token):
                for size in (2, 3):
                    for idx in range(0, max(len(token) - size + 1, 0)):
                        tokens.append(token[idx: idx + size])
        return tokens

    @staticmethod
    def _extract_keywords(text: str, limit: int = 12) -> list[str]:
        counter = Counter(AcquisitionIntakeService._tokenize(text))
        return [token for token, _ in counter.most_common(limit)]

    @staticmethod
    def _build_content_hash(title: str, content: str, source_url: Optional[str]) -> str:
        payload = "\n".join([
            AcquisitionIntakeService._normalize_text(title),
            AcquisitionIntakeService._normalize_text(content),
            AcquisitionIntakeService._normalize_text(source_url),
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_collected_item(platform: str, keyword: str, item: dict[str, Any]) -> dict[str, Any]:
        source_id = item.get("source_id") or item.get("sourceId") or item.get("external_id") or item.get("id")
        url = item.get("url") or item.get("source_url")
        raw_title = item.get("title") or item.get("raw_title")
        raw_content_text = item.get("content_text") or item.get("content") or item.get("snippet") or item.get("desc")
        title = AcquisitionIntakeService._clean_title_text(raw_title)
        content_text = AcquisitionIntakeService._clean_content_text(raw_content_text)
        if not title and content_text:
            title = AcquisitionIntakeService._clean_title_text(content_text[:40])
        normalized_platform = AcquisitionIntakeService._normalize_text(item.get("platform") or platform or "other") or "other"

        return {
            "platform": normalized_platform,
            "keyword": AcquisitionIntakeService._normalize_text(keyword) or None,
            "source_id": AcquisitionIntakeService._normalize_text(source_id) or None,
            "source_url": AcquisitionIntakeService._normalize_text(url) or None,
            "raw_title": AcquisitionIntakeService._normalize_text(raw_title) or None,
            "raw_content_text": AcquisitionIntakeService._normalize_text(raw_content_text) or None,
            "title": title or None,
            "author_name": AcquisitionIntakeService._normalize_text(item.get("author_name") or item.get("author") or item.get("nickname")) or None,
            "content_text": content_text or None,
            "cover_url": AcquisitionIntakeService._normalize_text(item.get("cover_url")) or None,
            "publish_time": AcquisitionIntakeService._to_datetime(item.get("publish_time") or item.get("upload_time")),
            "like_count": AcquisitionIntakeService._to_int(item.get("like_count") or item.get("liked_count")),
            "comment_count": AcquisitionIntakeService._to_int(item.get("comment_count")),
            "favorite_count": AcquisitionIntakeService._to_int(item.get("collect_count") or item.get("favorite_count") or item.get("collected_count")),
            "share_count": AcquisitionIntakeService._to_int(item.get("share_count")),
            "parse_status": AcquisitionIntakeService._normalize_text(item.get("parse_status") or "success").lower() or "success",
            "risk_status": AcquisitionIntakeService._normalize_text(item.get("risk_status") or "safe").lower() or "safe",
            "raw_payload": item,
        }

    @staticmethod
    def _validate_required_fields(normalized: dict[str, Any], source_channel: str) -> Optional[str]:
        if not normalized.get("platform"):
            return "missing_platform"
        if not normalized.get("title") and not normalized.get("content_text"):
            return "missing_title_and_content"
        if source_channel in {"collect_task", "employee_submission", "wechat_robot"}:
            if not normalized.get("source_url"):
                return "missing_url"
        return None

    @staticmethod
    def _calculate_quality(normalized: dict[str, Any]) -> int:
        score = 0
        if normalized.get("title"):
            score += 20
        if normalized.get("content_text"):
            score += 30
            content_length = len(str(normalized["content_text"]))
            if content_length >= 80:
                score += 15
            if content_length >= 200:
                score += 15
        if normalized.get("author_name"):
            score += 10
        if normalized.get("publish_time"):
            score += 5
        if normalized.get("cover_url"):
            score += 5
        return min(score, 100)

    @staticmethod
    def _calculate_relevance(normalized: dict[str, Any], keyword: str) -> int:
        text = f"{normalized.get('title') or ''} {normalized.get('content_text') or ''}"
        score = 0
        for token in AcquisitionIntakeService._split_keywords(keyword):
            if token and token in text:
                score += 30
        for term in AcquisitionIntakeService._TARGET_TERMS:
            if term in text:
                score += 12
        return min(score, 100)

    @staticmethod
    def _calculate_lead_score(normalized: dict[str, Any]) -> tuple[int, str, str]:
        text = f"{normalized.get('title') or ''} {normalized.get('content_text') or ''}"
        score = 0
        matched_terms: list[str] = []
        for word in AcquisitionIntakeService._INTENT_TERMS:
            if word in text:
                matched_terms.append(word)
                score += 20
        if any(term in text for term in ("电话", "微信", "私信", "联系")):
            matched_terms.append("联系方式线索")
            score += 20

        score = min(score, 100)
        if score >= 70:
            level = "high"
        elif score >= 35:
            level = "medium"
        else:
            level = "low"
        reason = "、".join(matched_terms[:3]) if matched_terms else "未识别显著转化信号"
        return score, level, reason

    @staticmethod
    def _calculate_hot_level(normalized: dict[str, Any]) -> str:
        score = (
            AcquisitionIntakeService._to_int(normalized.get("favorite_count")) * 3
            + AcquisitionIntakeService._to_int(normalized.get("comment_count")) * 2
            + AcquisitionIntakeService._to_int(normalized.get("share_count")) * 2
            + AcquisitionIntakeService._to_int(normalized.get("like_count"))
        )
        if score >= 200:
            return "high"
        if score >= 60:
            return "medium"
        return "low"

    @staticmethod
    def _classify_account_type(text: str) -> str:
        for label, words in AcquisitionIntakeService._ACCOUNT_TYPE_RULES:
            if any(word in text for word in words):
                return label
        return "科普号"

    @staticmethod
    def _classify_target_audience(text: str) -> str:
        for label, words in AcquisitionIntakeService._AUDIENCE_RULES:
            if any(word in text for word in words):
                return label
        return "泛人群"

    @staticmethod
    def _classify_content_type(title: str, content: str) -> str:
        text = f"{title} {content}"
        for label, words in AcquisitionIntakeService._CONTENT_TYPE_RULES:
            if any(word in text for word in words):
                return label
        if not content:
            return "标题"
        return "正文"

    @staticmethod
    def _extract_topic(title: str, content: str) -> str:
        keywords = AcquisitionIntakeService._extract_keywords(f"{title} {content}", limit=5)
        return " / ".join(keywords[:3]) if keywords else "未分类主题"

    @staticmethod
    def _split_chunks(text: str, chunk_size: int = 300) -> list[str]:
        body = AcquisitionIntakeService._normalize_text(text)
        if not body:
            return []
        paragraphs = [seg.strip() for seg in re.split(r"\n+", body) if seg.strip()]
        if not paragraphs:
            paragraphs = [body]

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if not current:
                current = paragraph
                continue
            if len(current) + len(paragraph) + 1 <= chunk_size:
                current = f"{current}\n{paragraph}"
            else:
                chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)
        return chunks[:20]

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...] | list[str]) -> bool:
        return any(keyword and keyword in text for keyword in keywords)

    @staticmethod
    def _count_any(text: str, keywords: tuple[str, ...] | list[str]) -> int:
        return sum(text.count(keyword) for keyword in keywords if keyword)

    @staticmethod
    def _detect_tag_by_rules(
        text: str,
        rules: list[tuple[str, tuple[str, ...]]],
        default_label: str,
    ) -> str:
        for label, words in rules:
            if AcquisitionIntakeService._contains_any(text, words):
                return label
        return default_label

    @staticmethod
    def build_material_tags(title: str, content_text: str) -> dict[str, Any]:
        merged = f"{title}\n{content_text}".strip()
        merged = re.sub(r"\s+", " ", merged)

        topic_tag = AcquisitionIntakeService._detect_tag_by_rules(
            merged,
            AcquisitionIntakeService._TOPIC_RULES,
            "贷款泛话题",
        )
        intent_tag = AcquisitionIntakeService._detect_tag_by_rules(
            merged,
            AcquisitionIntakeService._INTENT_RULES,
            "普通讨论",
        )
        crowd_tag = AcquisitionIntakeService._detect_tag_by_rules(
            merged,
            AcquisitionIntakeService._CROWD_RULES,
            "泛需求人群",
        )

        risk_tag = "low"
        if AcquisitionIntakeService._contains_any(merged, AcquisitionIntakeService._HIGH_RISK_TERMS):
            risk_tag = "high"
        elif AcquisitionIntakeService._contains_any(merged, AcquisitionIntakeService._MEDIUM_RISK_TERMS):
            risk_tag = "medium"

        heat_score = 30
        heat_score += min(
            AcquisitionIntakeService._count_any(merged, ("贷款", "车贷", "房贷", "网贷", "征信")) * 5,
            20,
        )
        heat_score += min(
            AcquisitionIntakeService._count_any(merged, ("怎么办", "被拒", "逾期", "套路", "提前还款")) * 8,
            30,
        )
        if len(merged) > 200:
            heat_score += 10
        if len(merged) > 500:
            heat_score += 10
        heat_score = min(heat_score, 100)

        reason = (
            f"识别为【{topic_tag}】话题，"
            f"用户意图偏【{intent_tag}】，"
            f"目标人群属于【{crowd_tag}】，"
            f"风险等级为【{risk_tag}】。"
        )

        return {
            "topic_tag": topic_tag,
            "intent_tag": intent_tag,
            "crowd_tag": crowd_tag,
            "risk_tag": risk_tag,
            "heat_score": heat_score,
            "reason": reason,
        }

    @staticmethod
    def _normalize_hashtags(tags: list[str], limit: int = 6) -> list[str]:
        result: list[str] = []
        for tag in tags:
            text = AcquisitionIntakeService._normalize_text(tag).replace("#", "")
            if not text:
                continue
            final_tag = f"#{text}"
            if final_tag not in result:
                result.append(final_tag)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _shorten_text(text: str, max_len: int = 180) -> str:
        body = AcquisitionIntakeService._normalize_text(text).replace("\n", " ")
        return body[:max_len]

    @staticmethod
    def generate_copy_variants(
        platform: str,
        title: str,
        content_text: str,
        tags: dict[str, Any],
        keyword: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        topic = str(tags.get("topic_tag") or "贷款泛话题")
        crowd = str(tags.get("crowd_tag") or "泛需求人群")
        source = AcquisitionIntakeService._shorten_text(content_text, 180 if platform == "xiaohongshu" else 120)
        normalized_title = AcquisitionIntakeService._normalize_text(title) or topic

        if platform == "douyin":
            variants = [
                {
                    "variant_name": "口播版1",
                    "title": f"{topic}别瞎弄",
                    "content": (
                        f"{normalized_title}，很多人一上来就做错了。"
                        f"尤其是{crowd}，最怕的不是没办法，而是顺序搞错。"
                        f"这条素材里最关键的一点其实是：{source}。"
                        f"先把自己的情况看明白，再决定下一步。"
                    ),
                    "hashtags": AcquisitionIntakeService._normalize_hashtags([topic, crowd, platform]),
                },
                {
                    "variant_name": "口播版2",
                    "title": f"{topic}一定要先看这个",
                    "content": (
                        f"很多人问{topic}怎么处理，"
                        f"其实不是不会做，是不知道先做哪一步。"
                        f"这篇内容里讲到：{source}。"
                        f"真遇到这种情况，先别急。"
                    ),
                    "hashtags": AcquisitionIntakeService._normalize_hashtags([topic, "避坑", platform]),
                },
                {
                    "variant_name": "口播版3",
                    "title": f"{topic}经验分享",
                    "content": (
                        f"今天聊一下{topic}。"
                        f"很多人容易忽略真实成本和后续影响。"
                        f"素材核心内容是：{source}。"
                        f"这种事一定先判断，再行动。"
                    ),
                    "hashtags": AcquisitionIntakeService._normalize_hashtags([topic, "经验", platform]),
                },
            ]
            return variants

        variants = [
            {
                "variant_name": "爆款版",
                "title": f"{topic}真的别乱做，我是怎么一步步避坑的",
                "content": (
                    f"最近看到很多人在聊“{normalized_title}”，其实这种事我之前也踩过坑。\n\n"
                    f"尤其是像【{crowd}】这种情况，很多人第一反应就是急着做决定，"
                    f"但越着急越容易被带偏。\n\n"
                    f"我后来才发现，先把自己的情况拆清楚，比到处乱问更重要。\n"
                    f"比如这类问题里，最容易忽略的就是还款方式、实际成本、征信影响这几个点。\n\n"
                    f"素材里提到的点是：{source}...\n\n"
                    f"如果你也在碰到类似问题，真的建议先把自己的情况理一遍，"
                    f"别一上来就被别人节奏带走。"
                ),
                "hashtags": AcquisitionIntakeService._normalize_hashtags([keyword or "", topic, crowd, platform]),
            },
            {
                "variant_name": "引流版",
                "title": f"{topic}这件事，我劝你先别急着做决定",
                "content": (
                    f"很多人表面看是在问“{normalized_title}”，"
                    f"其实真正卡住的是：不知道自己适合哪种方案。\n\n"
                    f"像【{crowd}】这类情况，处理顺序很关键，顺序错了，后面会更麻烦。\n\n"
                    "我把这类内容反复看了很多，发现大家最容易踩的就是：\n"
                    "1. 只看表面利率\n"
                    "2. 忽略隐藏成本\n"
                    "3. 没提前判断自己条件\n\n"
                    f"原素材核心是：{source}...\n\n"
                    "有同样情况的，先别乱操作，先把自己的问题点搞清楚。"
                ),
                "hashtags": AcquisitionIntakeService._normalize_hashtags([keyword or "", topic, "避坑", platform]),
            },
            {
                "variant_name": "安全版",
                "title": f"关于{topic}，分享几个容易被忽略的点",
                "content": (
                    f"今天整理了一下关于“{normalized_title}”这类内容。\n\n"
                    "发现很多讨论其实都集中在几个问题上：\n"
                    "- 真实成本怎么看\n"
                    "- 还款节奏怎么判断\n"
                    "- 不同人群适不适合当前方案\n\n"
                    f"像这篇素材里提到：{source}...\n\n"
                    f"如果你最近也在关注【{topic}】相关内容，建议多对比、多判断，"
                    "先把信息看完整，再做决定。"
                ),
                "hashtags": AcquisitionIntakeService._normalize_hashtags([topic, crowd, "经验分享", platform]),
            },
        ]
        return variants

    @staticmethod
    def compliance_review_and_rewrite(content: str, policy: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        policy = policy or {}
        threshold = int(policy.get("block_score_threshold") or AcquisitionIntakeService._DEFAULT_COMPLIANCE_BLOCK_SCORE)
        custom_risk_words = [str(word).strip() for word in (policy.get("custom_risk_words") or []) if str(word).strip()]

        reviewed_input = content
        for risk_word in custom_risk_words:
            if risk_word in reviewed_input:
                reviewed_input = reviewed_input.replace(risk_word, "合规表达")

        first_pass = ComplianceService.check_compliance(reviewed_input)
        reviewed_content = reviewed_input
        corrected = False

        if not bool(first_pass.get("is_compliant")):
            for risk_point in first_pass.get("risk_points") or []:
                reviewed_content = ComplianceService.suggest_correction(reviewed_content, risk_point)
            corrected = reviewed_content != reviewed_input

        second_pass = ComplianceService.check_compliance(reviewed_content)
        risk_score = second_pass.get("risk_score") if second_pass.get("risk_score") is not None else first_pass.get("risk_score")
        risk_level = second_pass.get("risk_level") or first_pass.get("risk_level") or "low"
        publish_blocked = bool(risk_level == "high" or (risk_score is not None and float(risk_score) >= float(threshold)))
        return {
            "content": reviewed_content,
            "corrected": corrected,
            "before": first_pass,
            "after": second_pass,
            "is_compliant": bool(second_pass.get("is_compliant")),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_points": second_pass.get("risk_points") or [],
            "suggestions": second_pass.get("suggestions") or [],
            "publish_blocked": publish_blocked,
            "block_threshold": threshold,
        }

    @staticmethod
    def _decide_status(
        source_channel: str,
        normalized: dict[str, Any],
        quality_score: int,
        relevance_score: int,
        lead_score: int,
        validation_reason: Optional[str],
    ) -> tuple[str, str]:
        if validation_reason:
            return "discard", validation_reason

        risk_status = normalized.get("risk_status") or "safe"
        parse_status = normalized.get("parse_status") or "success"

        if risk_status in {"blocked", "high", "reject"}:
            return "discard", "risk_blocked"
        if quality_score < 30:
            return "discard", "low_quality"
        if source_channel == "manual_input":
            return "review", "manual_input"
        if parse_status in {"list_only", "detail_failed", "partial"}:
            return "review", "detail_not_complete"
        if risk_status in {"review", "medium"}:
            return "review", "risk_need_review"
        if relevance_score == 0 and source_channel == "collect_task":
            return "discard", "irrelevant"
        if lead_score < 20:
            return "review", "lead_need_review"
        return "pending", "passed"

    @staticmethod
    def _find_duplicate_material(
        db: Session,
        owner_id: int,
        platform: str,
        source_id: Optional[str],
        content_hash: str,
    ) -> Optional[MaterialItem]:
        if source_id:
            existing_by_source = (
                db.query(MaterialItem)
                .filter(
                    MaterialItem.owner_id == owner_id,
                    MaterialItem.platform == platform,
                    MaterialItem.source_id == source_id,
                )
                .order_by(MaterialItem.id.desc())
                .first()
            )
            if existing_by_source is not None:
                return existing_by_source

        existing_by_hash = (
            db.query(MaterialItem)
            .join(NormalizedContent, MaterialItem.normalized_content_id == NormalizedContent.id)
            .filter(
                MaterialItem.owner_id == owner_id,
                MaterialItem.platform == platform,
                NormalizedContent.content_hash == content_hash,
            )
            .order_by(MaterialItem.id.desc())
            .first()
        )
        return existing_by_hash

    @staticmethod
    def _create_source_content(
        db: Session,
        owner_id: int,
        source_channel: str,
        normalized: dict[str, Any],
        source_task_id: Optional[int],
        source_submission_id: Optional[int],
        submitted_by_employee_id: Optional[int],
        remark: Optional[str],
    ) -> SourceContent:
        source = SourceContent(
            owner_id=owner_id,
            source_channel=source_channel,
            source_task_id=source_task_id,
            source_submission_id=source_submission_id,
            submitted_by_employee_id=submitted_by_employee_id,
            source_type="crawler" if source_channel in {"collect_task", "employee_submission", "wechat_robot"} else "manual",
            source_platform=normalized["platform"],
            source_id=normalized.get("source_id"),
            source_url=normalized.get("source_url"),
            keyword=normalized.get("keyword"),
            raw_title=normalized.get("raw_title") or normalized.get("title"),
            raw_content=normalized.get("raw_content_text") or normalized.get("content_text"),
            raw_payload=normalized.get("raw_payload") or {},
            author_name=normalized.get("author_name"),
            cover_url=normalized.get("cover_url"),
            publish_time=normalized.get("publish_time"),
            like_count=normalized.get("like_count", 0),
            comment_count=normalized.get("comment_count", 0),
            favorite_count=normalized.get("favorite_count", 0),
            share_count=normalized.get("share_count", 0),
            parse_status=normalized.get("parse_status") or "success",
            risk_status=normalized.get("risk_status") or "safe",
            remark=remark,
        )
        db.add(source)
        db.flush()
        return source

    @staticmethod
    def _create_normalized_content(
        db: Session,
        owner_id: int,
        source: SourceContent,
        normalized: dict[str, Any],
        content_hash: str,
    ) -> NormalizedContent:
        title = normalized.get("title") or (normalized.get("content_text") or "")[:20] or "无标题"
        content_text = normalized.get("content_text") or normalized.get("title") or ""
        normalized_content = NormalizedContent(
            owner_id=owner_id,
            source_content_id=source.id,
            title=title,
            content_text=content_text,
            content_preview=content_text[:100],
            content_hash=content_hash,
            platform=normalized["platform"],
            source_id=normalized.get("source_id"),
            source_url=normalized.get("source_url"),
            author_name=normalized.get("author_name"),
            cover_url=normalized.get("cover_url"),
            publish_time=normalized.get("publish_time"),
            like_count=normalized.get("like_count", 0),
            comment_count=normalized.get("comment_count", 0),
            favorite_count=normalized.get("favorite_count", 0),
            share_count=normalized.get("share_count", 0),
            parse_status=normalized.get("parse_status") or "success",
            risk_status=normalized.get("risk_status") or "safe",
            keyword=normalized.get("keyword"),
        )
        db.add(normalized_content)
        db.flush()
        return normalized_content

    @staticmethod
    def _replace_knowledge(
        db: Session,
        owner_id: int,
        material: MaterialItem,
    ) -> KnowledgeDocument:
        for existing in list(material.knowledge_documents or []):
            db.delete(existing)
        db.flush()

        text = f"{material.title or ''}\n{material.content_text or ''}"
        document = KnowledgeDocument(
            owner_id=owner_id,
            material_item_id=material.id,
            platform=material.platform,
            account_type=AcquisitionIntakeService._classify_account_type(text),
            target_audience=AcquisitionIntakeService._classify_target_audience(text),
            content_type=AcquisitionIntakeService._classify_content_type(material.title or "", material.content_text or ""),
            topic=AcquisitionIntakeService._extract_topic(material.title or "", material.content_text or ""),
            title=material.title,
            summary=(material.content_text or material.content_preview or "")[:120],
            content_text=material.content_text,
        )
        db.add(document)
        db.flush()

        for idx, chunk_text in enumerate(AcquisitionIntakeService._split_chunks(material.content_text or ""), start=1):
            db.add(
                KnowledgeChunk(
                    owner_id=owner_id,
                    knowledge_document_id=document.id,
                    chunk_type="body",
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    keywords=AcquisitionIntakeService._extract_keywords(chunk_text, limit=8),
                )
            )

        return document

    @staticmethod
    def _process_item(
        db: Session,
        owner_id: int,
        source_channel: str,
        raw_item: dict[str, Any],
        platform: str,
        keyword: str,
        source_task_id: Optional[int] = None,
        source_submission_id: Optional[int] = None,
        submitted_by_employee_id: Optional[int] = None,
        remark: Optional[str] = None,
    ) -> dict[str, Any]:
        normalized = AcquisitionIntakeService._normalize_collected_item(platform, keyword, raw_item)
        validation_reason = AcquisitionIntakeService._validate_required_fields(normalized, source_channel)
        content_hash = AcquisitionIntakeService._build_content_hash(
            normalized.get("title") or "",
            normalized.get("content_text") or "",
            normalized.get("source_url"),
        )

        duplicate = AcquisitionIntakeService._find_duplicate_material(
            db=db,
            owner_id=owner_id,
            platform=normalized["platform"],
            source_id=normalized.get("source_id"),
            content_hash=content_hash,
        )
        if duplicate is not None:
            return {
                "created": False,
                "duplicate": True,
                "material": duplicate,
                "status": "discard",
                "reason": "duplicate",
            }

        source = AcquisitionIntakeService._create_source_content(
            db=db,
            owner_id=owner_id,
            source_channel=source_channel,
            normalized=normalized,
            source_task_id=source_task_id,
            source_submission_id=source_submission_id,
            submitted_by_employee_id=submitted_by_employee_id,
            remark=remark,
        )
        normalized_content = AcquisitionIntakeService._create_normalized_content(db, owner_id, source, normalized, content_hash)

        quality_score = AcquisitionIntakeService._calculate_quality(normalized)
        relevance_score = AcquisitionIntakeService._calculate_relevance(normalized, keyword)
        lead_score, lead_level, lead_reason = AcquisitionIntakeService._calculate_lead_score(normalized)
        status, reason = AcquisitionIntakeService._decide_status(
            source_channel=source_channel,
            normalized=normalized,
            quality_score=quality_score,
            relevance_score=relevance_score,
            lead_score=lead_score,
            validation_reason=validation_reason,
        )
        title = normalized.get("title") or (normalized.get("content_text") or "")[:20] or "无标题"
        content_text = normalized.get("content_text") or title

        material = MaterialItem(
            owner_id=owner_id,
            source_channel=source_channel,
            source_task_id=source_task_id,
            source_submission_id=source_submission_id,
            submitted_by_employee_id=submitted_by_employee_id,
            source_content_id=source.id,
            normalized_content_id=normalized_content.id,
            platform=normalized["platform"],
            source_id=normalized.get("source_id"),
            source_url=normalized.get("source_url"),
            keyword=normalized.get("keyword"),
            title=title,
            content_text=content_text,
            content_preview=content_text[:100],
            author_name=normalized.get("author_name"),
            cover_url=normalized.get("cover_url"),
            publish_time=normalized.get("publish_time"),
            like_count=normalized.get("like_count", 0),
            comment_count=normalized.get("comment_count", 0),
            favorite_count=normalized.get("favorite_count", 0),
            share_count=normalized.get("share_count", 0),
            hot_level=AcquisitionIntakeService._calculate_hot_level(normalized),
            lead_level=lead_level,
            lead_reason=lead_reason,
            quality_score=quality_score,
            relevance_score=relevance_score,
            lead_score=lead_score,
            parse_status=normalized.get("parse_status") or "success",
            risk_status=normalized.get("risk_status") or "safe",
            is_duplicate=False,
            filter_reason=reason,
            status=status,
            remark=remark,
        )
        db.add(material)
        db.flush()
        AcquisitionIntakeService._replace_knowledge(db, owner_id, material)

        return {
            "created": True,
            "duplicate": False,
            "material": material,
            "status": status,
            "reason": reason,
        }

    @staticmethod
    def serialize_material_item(item: MaterialItem, include_raw_data: bool = True) -> dict[str, Any]:
        created_at = getattr(item, "created_at", None)
        updated_at = getattr(item, "updated_at", None)
        publish_time = getattr(item, "publish_time", None)
        raw_data: dict[str, Any] = {}
        if include_raw_data:
            source = getattr(item, "source_content", None)
            raw_data = getattr(source, "raw_payload", None) or {}

        return {
            "id": item.id,
            "source_channel": item.source_channel,
            "source_task_id": item.source_task_id,
            "source_submission_id": item.source_submission_id,
            "platform": item.platform,
            "source_id": item.source_id,
            "keyword": item.keyword,
            "title": item.title,
            "author": item.author_name,
            "content": item.content_text,
            "url": item.source_url,
            "cover_url": item.cover_url,
            "like_count": item.like_count,
            "comment_count": item.comment_count,
            "collect_count": item.favorite_count,
            "share_count": item.share_count,
            "publish_time": publish_time.isoformat() if publish_time else None,
            "parse_status": item.parse_status,
            "risk_status": item.risk_status,
            "quality_score": item.quality_score,
            "relevance_score": item.relevance_score,
            "lead_score": item.lead_score,
            "lead_level": item.lead_level,
            "lead_reason": item.lead_reason,
            "hot_level": item.hot_level,
            "is_duplicate": bool(item.is_duplicate),
            "filter_reason": item.filter_reason,
            "raw_data": raw_data,
            "status": item.status,
            "submitted_by_employee_id": item.submitted_by_employee_id,
            "remark": item.remark,
            "review_note": item.review_note,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }

    @staticmethod
    def ingest_item(
        db: Session,
        owner_id: int,
        source_channel: str,
        raw_item: dict[str, Any],
        platform: str,
        keyword: str,
        source_task_id: Optional[int] = None,
        source_submission_id: Optional[int] = None,
        submitted_by_employee_id: Optional[int] = None,
        remark: Optional[str] = None,
        auto_commit: bool = False,
    ) -> dict[str, Any]:
        result = AcquisitionIntakeService._process_item(
            db=db,
            owner_id=owner_id,
            source_channel=source_channel,
            raw_item=raw_item,
            platform=platform,
            keyword=keyword,
            source_task_id=source_task_id,
            source_submission_id=source_submission_id,
            submitted_by_employee_id=submitted_by_employee_id,
            remark=remark,
        )
        if auto_commit:
            db.commit()
            material = result.get("material")
            if material is not None:
                db.refresh(material)
        return result

    @staticmethod
    def _ingest_items(
        db: Session,
        owner_id: int,
        source_channel: str,
        items: list[dict[str, Any]],
        platform: str,
        keyword: str,
        source_task_id: Optional[int] = None,
        source_submission_id: Optional[int] = None,
        submitted_by_employee_id: Optional[int] = None,
        remark: Optional[str] = None,
    ) -> dict[str, int]:
        stats = {
            "inserted_count": 0,
            "review_count": 0,
            "discard_count": 0,
            "duplicate_count": 0,
            "failed_count": 0,
        }

        for raw in items:
            try:
                result = AcquisitionIntakeService.ingest_item(
                    db=db,
                    owner_id=owner_id,
                    source_channel=source_channel,
                    raw_item=raw,
                    platform=platform,
                    keyword=keyword,
                    source_task_id=source_task_id,
                    source_submission_id=source_submission_id,
                    submitted_by_employee_id=submitted_by_employee_id,
                    remark=remark,
                    auto_commit=False,
                )
                if result["duplicate"]:
                    stats["duplicate_count"] += 1
                    continue
                if result["status"] == "pending":
                    stats["inserted_count"] += 1
                elif result["status"] == "review":
                    stats["review_count"] += 1
                else:
                    stats["discard_count"] += 1
            except Exception:
                stats["failed_count"] += 1

        db.commit()
        return stats

    @staticmethod
    def create_keyword_task(
        db: Session,
        owner_id: int,
        platform: str,
        keyword: str,
        max_items: int,
        client: Optional[BrowserCollectorClient] = None,
    ) -> dict[str, Any]:
        collector_client = client or BrowserCollectorClient()
        task = CollectTask(
            owner_id=owner_id,
            task_type="keyword",
            platform=platform,
            keyword=keyword,
            max_items=max_items,
            status="pending",
        )
        db.add(task)
        db.flush()
        task_id = int(task.id)

        try:
            result = collector_client.collect_keyword(platform=platform, keyword=keyword, max_items=max_items)
            rows = result.get("items") or []
            stats = AcquisitionIntakeService._ingest_items(
                db=db,
                owner_id=owner_id,
                source_channel="collect_task",
                items=rows,
                platform=platform,
                keyword=keyword,
                source_task_id=task_id,
            )
            task.result_count = int(result.get("count") or result.get("total") or len(rows))
            task.inserted_count = stats["inserted_count"]
            task.review_count = stats["review_count"]
            task.discard_count = stats["discard_count"]
            task.duplicate_count = stats["duplicate_count"]
            task.failed_count = stats["failed_count"]
            task.status = "success"
            db.commit()
            db.refresh(task)
            return {
                "task_id": task_id,
                "status": task.status,
                "result_count": task.result_count,
                "inserted": task.inserted_count,
                "review": task.review_count,
                "discard": task.discard_count,
                "duplicate": task.duplicate_count,
                "failed": task.failed_count,
            }
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
            db.commit()
            raise

    @staticmethod
    def submit_link(
        db: Session,
        owner_id: int,
        employee_id: Optional[int],
        url: str,
        note: Optional[str],
        source_type: str = "manual_link",
        client: Optional[BrowserCollectorClient] = None,
    ) -> dict[str, Any]:
        collector_client = client or BrowserCollectorClient()
        submission = EmployeeLinkSubmission(
            owner_id=owner_id,
            employee_id=employee_id,
            source_type=source_type,
            url=url,
            note=note,
            status="pending",
        )
        db.add(submission)
        db.flush()
        submission_id = int(submission.id)

        try:
            result = collector_client.collect_single_link(url=url)
            rows = result.get("items") or []
            if not rows:
                raise ValueError("采集服务未返回可入库内容")

            row = rows[0]
            platform = AcquisitionIntakeService._normalize_text(row.get("platform") or "other") or "other"
            submission.platform = platform
            channel = "wechat_robot" if source_type == "wechat_robot" else "employee_submission"
            stats = AcquisitionIntakeService._ingest_items(
                db=db,
                owner_id=owner_id,
                source_channel=channel,
                items=[row],
                platform=platform,
                keyword=url,
                source_submission_id=submission_id,
                submitted_by_employee_id=employee_id,
                remark=note,
            )
            submission.status = "success"
            db.commit()
            return {
                "submission_id": submission_id,
                "status": submission.status,
                "platform": submission.platform,
                "inserted": stats["inserted_count"],
                "review": stats["review_count"],
                "discard": stats["discard_count"],
                "duplicate": stats["duplicate_count"],
            }
        except Exception as exc:
            submission.status = "failed"
            submission.error_message = str(exc)
            db.commit()
            raise

    @staticmethod
    def submit_manual(
        db: Session,
        owner_id: int,
        platform: str,
        title: str,
        content: str,
        tags: Optional[list] = None,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        raw_item = {
            "platform": platform,
            "title": title,
            "content_text": content,
            "parse_status": "success",
            "risk_status": "review",
            "raw_payload": {"tags": tags or []},
        }
        result = AcquisitionIntakeService.ingest_item(
            db=db,
            owner_id=owner_id,
            source_channel="manual_input",
            raw_item=raw_item,
            platform=platform,
            keyword="",
            remark=note,
            auto_commit=True,
        )
        material = result["material"]
        return {"inbox_id": int(material.id), "material_id": int(material.id), "status": str(material.status)}

    @staticmethod
    def list_inbox(
        db: Session,
        owner_id: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        source_channel: Optional[str] = None,
        keyword: Optional[str] = None,
        risk_status: Optional[str] = None,
        is_duplicate: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
        include_source_content: bool = False,
        include_knowledge: bool = False,
        include_generation: bool = False,
        include_chunks: bool = False,
    ) -> list[MaterialItem]:
        query = AcquisitionIntakeService._material_item_query(
            db=db,
            owner_id=owner_id,
            include_source_content=include_source_content,
            include_knowledge=include_knowledge,
            include_generation=include_generation,
            include_chunks=include_chunks,
        )
        if status:
            query = query.filter(MaterialItem.status == status)
        if platform:
            query = query.filter(MaterialItem.platform == platform)
        if source_channel:
            query = query.filter(MaterialItem.source_channel == source_channel)
        if keyword:
            query = query.filter(MaterialItem.keyword.contains(keyword))
        if risk_status:
            query = query.filter(MaterialItem.risk_status == risk_status)
        if is_duplicate is not None:
            query = query.filter(MaterialItem.is_duplicate == is_duplicate)
        return query.order_by(desc(MaterialItem.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def _material_item_query(
        db: Session,
        owner_id: int,
        include_source_content: bool = False,
        include_knowledge: bool = False,
        include_generation: bool = False,
        include_chunks: bool = False,
    ):
        query = db.query(MaterialItem).filter(MaterialItem.owner_id == owner_id)
        if include_source_content:
            query = query.options(selectinload(MaterialItem.source_content))
        if include_knowledge or include_chunks:
            knowledge_loader = selectinload(MaterialItem.knowledge_documents)
            if include_chunks:
                knowledge_loader = knowledge_loader.selectinload(KnowledgeDocument.knowledge_chunks)
            query = query.options(knowledge_loader)
        if include_generation:
            query = query.options(selectinload(MaterialItem.generation_tasks))
        return query

    @staticmethod
    def get_inbox_item(
        db: Session,
        owner_id: int,
        inbox_id: int,
        include_source_content: bool = False,
        include_knowledge: bool = False,
        include_generation: bool = False,
        include_chunks: bool = False,
    ) -> Optional[MaterialItem]:
        return (
            AcquisitionIntakeService._material_item_query(
                db=db,
                owner_id=owner_id,
                include_source_content=include_source_content,
                include_knowledge=include_knowledge,
                include_generation=include_generation,
                include_chunks=include_chunks,
            )
            .filter(MaterialItem.id == inbox_id)
            .first()
        )

    @staticmethod
    def get_material_item(
        db: Session,
        owner_id: int,
        material_id: int,
        include_source_content: bool = False,
        include_knowledge: bool = False,
        include_generation: bool = False,
        include_chunks: bool = False,
    ) -> Optional[MaterialItem]:
        return AcquisitionIntakeService.get_inbox_item(
            db=db,
            owner_id=owner_id,
            inbox_id=material_id,
            include_source_content=include_source_content,
            include_knowledge=include_knowledge,
            include_generation=include_generation,
            include_chunks=include_chunks,
        )

    @staticmethod
    def reindex_material(db: Session, owner_id: int, material_id: int) -> dict[str, Any]:
        material = AcquisitionIntakeService.get_material_item(db, owner_id, material_id)
        if material is None:
            raise ValueError("素材不存在")

        document = AcquisitionIntakeService._replace_knowledge(db, owner_id, material)
        db.commit()
        db.refresh(material)
        return {
            "material_id": material.id,
            "knowledge_document_id": document.id,
            "account_type": document.account_type,
            "target_audience": document.target_audience,
            "content_type": document.content_type,
            "topic": document.topic,
            "summary": document.summary,
            "chunk_count": len(document.knowledge_chunks or []),
        }

    @staticmethod
    def get_primary_knowledge_document(material: MaterialItem) -> Optional[KnowledgeDocument]:
        documents = sorted(material.knowledge_documents or [], key=lambda item: item.id)
        if not documents:
            return None
        return documents[0]

    @staticmethod
    def update_inbox_status(
        db: Session,
        owner_id: int,
        inbox_id: int,
        target_status: str,
        review_note: Optional[str] = None,
    ) -> dict[str, Any]:
        item = AcquisitionIntakeService.get_inbox_item(db, owner_id, inbox_id)
        if item is None:
            raise ValueError("收件箱内容不存在")

        current_status = str(item.status or "pending")
        if target_status not in AcquisitionIntakeService._STATUS_TRANSITIONS:
            raise ValueError("无效状态，仅支持 pending/review/discard")
        if target_status != current_status and target_status not in AcquisitionIntakeService._STATUS_TRANSITIONS[current_status]:
            raise ValueError(f"不允许从 {current_status} 流转到 {target_status}")

        item.status = target_status
        if review_note is not None:
            item.review_note = review_note
        db.commit()
        db.refresh(item)
        return {
            "inbox_id": int(item.id),
            "material_id": int(item.id),
            "status": str(item.status),
            "review_note": item.review_note,
        }

    @staticmethod
    def _apply_structure_filter(
        query,
        platform: str,
        account_type: str,
        target_audience: str,
    ):
        query = query.filter(KnowledgeDocument.platform == platform)
        query = query.filter(KnowledgeDocument.account_type == account_type)
        query = query.filter(KnowledgeDocument.target_audience == target_audience)
        return query

    @staticmethod
    def _keyword_score(query_tokens: list[str], document: KnowledgeDocument) -> float:
        doc_text = f"{document.title or ''} {document.summary or ''} {document.content_text or ''}"
        return float(sum(1 for token in query_tokens if token and token in doc_text))

    @staticmethod
    def _semantic_score(query_text: str, document: KnowledgeDocument) -> float:
        doc_text = f"{document.title or ''}\n{document.summary or ''}\n{document.content_text or ''}"
        if not query_text or not doc_text:
            return 0.0
        token_set_query = set(AcquisitionIntakeService._tokenize(query_text))
        token_set_doc = set(AcquisitionIntakeService._tokenize(doc_text))
        overlap = 0.0
        if token_set_query and token_set_doc:
            overlap = len(token_set_query & token_set_doc) / max(len(token_set_query | token_set_doc), 1)
        seq_ratio = SequenceMatcher(None, query_text[:500], doc_text[:500]).ratio()
        return round((overlap * 0.7) + (seq_ratio * 0.3), 4)

    @staticmethod
    def retrieve(
        db: Session,
        owner_id: int,
        query_text: str,
        platform: str,
        account_type: str,
        target_audience: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        base_query = (
            db.query(KnowledgeDocument)
            .options(
                selectinload(KnowledgeDocument.material_item),
                selectinload(KnowledgeDocument.knowledge_chunks),
            )
            .filter(KnowledgeDocument.owner_id == owner_id)
        )
        filtered_query = AcquisitionIntakeService._apply_structure_filter(base_query, platform, account_type, target_audience)
        candidates = filtered_query.order_by(desc(KnowledgeDocument.id)).limit(100).all()

        if not candidates:
            candidates = (
                db.query(KnowledgeDocument)
                .options(
                    selectinload(KnowledgeDocument.material_item),
                    selectinload(KnowledgeDocument.knowledge_chunks),
                )
                .filter(KnowledgeDocument.owner_id == owner_id, KnowledgeDocument.platform == platform)
                .order_by(desc(KnowledgeDocument.id))
                .limit(100)
                .all()
            )

        query_tokens = AcquisitionIntakeService._extract_keywords(query_text, limit=12)
        ranked: list[dict[str, Any]] = []
        for document in candidates:
            keyword_score = AcquisitionIntakeService._keyword_score(query_tokens, document)
            semantic_score = AcquisitionIntakeService._semantic_score(query_text, document)
            material = document.material_item
            hot_boost = 1.0 if material and material.hot_level == "high" else 0.5 if material and material.hot_level == "medium" else 0.0
            lead_boost = 1.0 if material and material.lead_level == "high" else 0.5 if material and material.lead_level == "medium" else 0.0
            final_score = round((keyword_score * 2.0) + (semantic_score * 10.0) + hot_boost + lead_boost, 4)
            chunks = sorted(document.knowledge_chunks or [], key=lambda item: item.chunk_index)[:3]
            ranked.append(
                {
                    "document_id": document.id,
                    "material_item_id": document.material_item_id,
                    "title": document.title,
                    "summary": document.summary,
                    "topic": document.topic,
                    "account_type": document.account_type,
                    "target_audience": document.target_audience,
                    "content_type": document.content_type,
                    "keyword_score": keyword_score,
                    "semantic_score": semantic_score,
                    "score": final_score,
                    "chunks": [chunk.chunk_text for chunk in chunks],
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:limit]

    @staticmethod
    def _load_rules(
        db: Session,
        owner_id: int,
        platform: str,
        account_type: str,
        target_audience: str,
    ) -> list[Rule]:
        query = db.query(Rule).filter(Rule.owner_id == owner_id)
        query = query.filter((Rule.platform == platform) | (Rule.platform.is_(None)))
        query = query.filter((Rule.account_type == account_type) | (Rule.account_type.is_(None)))
        query = query.filter((Rule.target_audience == target_audience) | (Rule.target_audience.is_(None)))
        rules = query.order_by(desc(Rule.priority), desc(Rule.id)).limit(20).all()
        if rules:
            return rules

        default_rules = [
            Rule(
                owner_id=owner_id,
                rule_type="platform_rule",
                platform=platform,
                account_type=account_type,
                target_audience=target_audience,
                name="禁止违规承诺",
                content="不得使用包过、百分百下款、绝对化收益、虚假资质背书等表达。",
                priority=100,
            ),
            Rule(
                owner_id=owner_id,
                rule_type="structure_rule",
                platform=platform,
                account_type=account_type,
                target_audience=target_audience,
                name="三段式输出",
                content="默认使用开场钩子、痛点展开、行动引导三段式结构，不要堆砌空话。",
                priority=90,
            ),
        ]
        db.add_all(default_rules)
        db.flush()
        return default_rules

    @staticmethod
    def _select_prompt_template(
        db: Session,
        owner_id: int,
        task_type: str,
        platform: str,
        account_type: str,
        target_audience: str,
    ) -> Optional[PromptTemplate]:
        query = db.query(PromptTemplate).filter(
            PromptTemplate.owner_id == owner_id,
            PromptTemplate.task_type == task_type,
        )
        query = query.filter((PromptTemplate.platform == platform) | (PromptTemplate.platform.is_(None)))
        query = query.filter((PromptTemplate.account_type == account_type) | (PromptTemplate.account_type.is_(None)))
        query = query.filter((PromptTemplate.target_audience == target_audience) | (PromptTemplate.target_audience.is_(None)))
        template = query.order_by(desc(PromptTemplate.id)).first()
        if template is not None:
            return template

        template = PromptTemplate(
            owner_id=owner_id,
            task_type=task_type,
            platform=platform,
            account_type=account_type,
            target_audience=target_audience,
            version="v1",
            system_prompt="你是内容生成助手，负责基于素材和知识库生成可发布文案，必须遵守业务规则，不得抄袭参考原文。",
            user_prompt_template=(
                "请基于以下素材生成一篇{task_type}文案。目标平台:{platform}；账号类型:{account_type}；目标人群:{target_audience}。"
                "输出要求：贴近业务、结构清晰、避免空泛表达、不能直接复述参考素材。"
            ),
        )
        db.add(template)
        db.flush()
        return template

    @staticmethod
    def _load_compliance_policy(
        db: Session,
        owner_id: int,
        platform: str,
    ) -> dict[str, Any]:
        threshold = AcquisitionIntakeService._DEFAULT_COMPLIANCE_BLOCK_SCORE
        custom_words: set[str] = set()

        rules = (
            db.query(Rule)
            .filter(
                Rule.owner_id == owner_id,
                Rule.rule_type.in_(["compliance_threshold", "compliance_risk_word"]),
                (Rule.platform == platform) | (Rule.platform.is_(None)),
            )
            .order_by(desc(Rule.priority), desc(Rule.id))
            .all()
        )

        for rule in rules:
            if rule.rule_type == "compliance_threshold":
                try:
                    threshold = max(0, min(100, int((rule.content or "").strip())))
                except Exception:
                    continue
            elif rule.rule_type == "compliance_risk_word":
                words = [seg.strip() for seg in re.split(r"[,，;；\s]+", rule.content or "") if seg.strip()]
                custom_words.update(words)

        return {
            "block_score_threshold": threshold,
            "custom_risk_words": sorted(custom_words),
        }

    @staticmethod
    async def generate(
        db: Session,
        owner_id: int,
        material_id: int,
        platform: str,
        account_type: str,
        target_audience: str,
        task_type: str,
        ai_service,
    ) -> dict[str, Any]:
        material = AcquisitionIntakeService.get_inbox_item(db, owner_id, material_id)
        if material is None:
            raise ValueError("素材不存在")

        references = AcquisitionIntakeService.retrieve(
            db=db,
            owner_id=owner_id,
            query_text=material.content_text or material.title or "",
            platform=platform,
            account_type=account_type,
            target_audience=target_audience,
            limit=5,
        )
        rules = AcquisitionIntakeService._load_rules(db, owner_id, platform, account_type, target_audience)
        compliance_policy = AcquisitionIntakeService._load_compliance_policy(db, owner_id, platform)
        template = AcquisitionIntakeService._select_prompt_template(db, owner_id, task_type, platform, account_type, target_audience)

        reference_lines = []
        for ref in references:
            chunk_text = "\n".join(ref["chunks"][:2])
            reference_lines.append(
                f"- 标题: {ref['title'] or '无标题'}\n  主题: {ref['topic'] or '未分类'}\n  摘要: {ref['summary'] or ''}\n  参考片段: {chunk_text}"
            )

        rule_lines = [f"- {rule.name}: {rule.content}" for rule in rules]
        system_prompt = template.system_prompt if template else "你是内容生成助手，负责基于素材和知识库生成可发布文案。"
        user_prompt = template.user_prompt_template if template else (
            "请基于以下素材生成一篇{task_type}文案。目标平台:{platform}；账号类型:{account_type}；目标人群:{target_audience}。"
            "必须吸收参考知识的结构和洞察，但不能直接复制原文。输出只返回最终文案。"
        )
        prompt_body = user_prompt.format(
            task_type=task_type,
            platform=platform,
            account_type=account_type,
            target_audience=target_audience,
        )
        final_prompt = (
            f"{prompt_body}\n\n"
            f"【原始素材】\n标题: {material.title or '无标题'}\n正文:\n{material.content_text or ''}\n\n"
            f"【素材属性】\n热度: {material.hot_level}\n线索等级: {material.lead_level}\n线索原因: {material.lead_reason or '无'}\n\n"
            f"【知识参考】\n{chr(10).join(reference_lines) if reference_lines else '无匹配知识'}\n\n"
            f"【规则约束】\n{chr(10).join(rule_lines) if rule_lines else '无附加规则'}"
        )

        output_text = await ai_service.call_llm(
            prompt=final_prompt,
            system_prompt=system_prompt,
            user_id=owner_id,
            scene=f"generation_{task_type}",
        )

        tags = AcquisitionIntakeService.build_material_tags(
            title=material.title or "",
            content_text=output_text or material.content_text or "",
        )
        variants = AcquisitionIntakeService.generate_copy_variants(
            platform=platform,
            title=material.title or "",
            content_text=output_text or material.content_text or "",
            tags=tags,
            keyword=material.keyword,
        )

        reviewed_variants: list[dict[str, Any]] = []
        for variant in variants:
            compliance = AcquisitionIntakeService.compliance_review_and_rewrite(variant["content"], compliance_policy)
            reviewed_variants.append(
                {
                    "variant_name": variant["variant_name"],
                    "title": variant["title"],
                    "content": compliance["content"],
                    "hashtags": variant.get("hashtags") or [],
                    "compliance": {
                        "corrected": compliance["corrected"],
                        "is_compliant": compliance["is_compliant"],
                        "risk_level": compliance["risk_level"],
                        "risk_score": compliance["risk_score"],
                        "risk_points": compliance["risk_points"],
                        "suggestions": compliance["suggestions"],
                        "publish_blocked": compliance["publish_blocked"],
                        "block_threshold": compliance["block_threshold"],
                    },
                }
            )

        preferred_variant = next(
            (
                item
                for item in reviewed_variants
                if item["compliance"]["is_compliant"] and not item["compliance"].get("publish_blocked")
            ),
            None,
        )
        if preferred_variant is None:
            preferred_variant = reviewed_variants[0] if reviewed_variants else {
                "variant_name": "默认版",
                "title": material.title or "改写结果",
                "content": output_text,
                "hashtags": [],
                "compliance": {
                    "corrected": False,
                    "is_compliant": True,
                    "risk_level": "low",
                    "risk_score": 0,
                    "risk_points": [],
                    "suggestions": [],
                    "publish_blocked": False,
                    "block_threshold": compliance_policy.get("block_score_threshold", AcquisitionIntakeService._DEFAULT_COMPLIANCE_BLOCK_SCORE),
                },
            }

        selected_output_text = preferred_variant["content"]
        final_compliance = preferred_variant["compliance"]
        selected_variant_index = next(
            (idx for idx, item in enumerate(reviewed_variants) if item.get("variant_name") == preferred_variant.get("variant_name")),
            None,
        )

        if final_compliance.get("publish_blocked"):
            material.status = "review"
            material.review_note = "改写结果风险高，已阻断发布并转入复核队列"

        generation = GenerationTask(
            owner_id=owner_id,
            material_item_id=material.id,
            platform=platform,
            account_type=account_type,
            target_audience=target_audience,
            task_type=task_type,
            prompt_snapshot=final_prompt,
            output_text=selected_output_text,
            reference_document_ids=[ref["document_id"] for ref in references],
            tags_json=tags,
            copies_json=reviewed_variants,
            compliance_json=final_compliance,
            selected_variant=preferred_variant.get("variant_name"),
            selected_variant_index=selected_variant_index,
            adoption_status="pending",
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)

        return {
            "generation_task_id": generation.id,
            "material_id": material.id,
            "platform": platform,
            "account_type": account_type,
            "target_audience": target_audience,
            "task_type": task_type,
            "output_text": selected_output_text,
            "llm_output": output_text,
            "tags": tags,
            "copies": reviewed_variants,
            "selected_variant": preferred_variant.get("variant_name"),
            "compliance": final_compliance,
            "references": references,
        }
