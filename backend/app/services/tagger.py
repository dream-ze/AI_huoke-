from __future__ import annotations

import re

from app.schemas import TagResult


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def _count_any(text: str, keywords: list[str]) -> int:
    return sum(text.count(k) for k in keywords)


def detect_topic_tag(text: str) -> str:
    rules = {
        "车贷": ["车贷", "车子贷款", "按揭车", "绿本", "解押", "提前还款", "免息车贷"],
        "房贷": ["房贷", "按揭房", "公积金贷款", "商贷", "首付", "月供"],
        "网贷": ["网贷", "借呗", "花呗", "度小满", "360借条", "微粒贷", "平台借款"],
        "信用卡": ["信用卡", "刷卡", "账单", "分期", "逾期", "停息挂账"],
        "征信": ["征信", "查询次数", "大数据花", "风控", "黑户", "白户"],
    }
    for tag, keywords in rules.items():
        if _contains_any(text, keywords):
            return tag
    return "贷款泛话题"


def detect_intent_tag(text: str) -> str:
    if _contains_any(text, ["怎么办", "咋办", "怎么解决", "求助", "有没有人懂", "能不能", "怎么办啊"]):
        return "求助"
    if _contains_any(text, ["被拒", "拒贷", "下不来", "过不了", "审核不过"]):
        return "被拒"
    if _contains_any(text, ["避坑", "套路", "坑", "被骗", "千万别", "后悔"]):
        return "避坑"
    if _contains_any(text, ["攻略", "经验", "分享", "终于懂了", "提前还款"]):
        return "经验分享"
    if _contains_any(text, ["推荐", "中介", "有人做", "私我", "咨询我"]):
        return "转化引导"
    return "普通讨论"


def detect_crowd_tag(text: str) -> str:
    if _contains_any(text, ["负债", "欠款", "欠了", "还不上", "逾期"]):
        return "负债人群"
    if _contains_any(text, ["征信花", "大数据花", "查询多", "白户", "黑户"]):
        return "征信问题人群"
    if _contains_any(text, ["买车", "提车", "按揭车"]):
        return "购车人群"
    if _contains_any(text, ["买房", "首付", "上车"]):
        return "购房人群"
    return "泛需求人群"


def detect_risk_tag(text: str) -> str:
    high_risk_words = [
        "套现", "洗白", "黑户秒过", "包装资料", "刷流水",
        "百分百下款", "无视风控", "无视征信", "内部渠道",
    ]
    medium_risk_words = [
        "私信", "加v", "加微", "VX", "微信", "联系我", "中介",
    ]

    if _contains_any(text, high_risk_words):
        return "high"
    if _contains_any(text, medium_risk_words):
        return "medium"
    return "low"


def calc_heat_score(text: str) -> int:
    score = 30
    score += min(_count_any(text, ["贷款", "车贷", "房贷", "网贷", "征信"]) * 5, 20)
    score += min(_count_any(text, ["怎么办", "被拒", "逾期", "套路", "提前还款"]) * 8, 30)

    if len(text) > 200:
        score += 10
    if len(text) > 500:
        score += 10

    return min(score, 100)


def build_reason(topic_tag: str, intent_tag: str, crowd_tag: str, risk_tag: str) -> str:
    return (
        f"识别为【{topic_tag}】话题，"
        f"用户意图偏【{intent_tag}】，"
        f"目标人群属于【{crowd_tag}】，"
        f"风险等级为【{risk_tag}】。"
    )


def tag_material(title: str, content_text: str) -> TagResult:
    merged = f"{title}\n{content_text}".strip()
    merged = re.sub(r"\s+", " ", merged)

    topic_tag = detect_topic_tag(merged)
    intent_tag = detect_intent_tag(merged)
    crowd_tag = detect_crowd_tag(merged)
    risk_tag = detect_risk_tag(merged)
    heat_score = calc_heat_score(merged)
    reason = build_reason(topic_tag, intent_tag, crowd_tag, risk_tag)

    return TagResult(
        topic_tag=topic_tag,
        intent_tag=intent_tag,
        crowd_tag=crowd_tag,
        risk_tag=risk_tag,
        heat_score=heat_score,
        reason=reason,
    )
