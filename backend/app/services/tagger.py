from __future__ import annotations

import re

from app.schemas import TagResult

# ============================================================
# 助贷业务专用标签识别规则
# ============================================================

# 产品类型关键词
PRODUCT_TYPE_KEYWORDS = {
    "信贷": ["信用贷", "信贷", "无抵押", "纯信用", "凭身份证", "不用抵押", "信用借款"],
    "抵押贷": ["抵押贷", "房产抵押", "房屋抵押", "绿本贷", "车抵贷", "按揭房", "抵押贷款", "房子抵押"],
    "企业贷": ["企业贷", "公司贷", "企业信用贷", "经营性贷款", "企业融资"],
    "经营贷": ["经营贷", "经营性", "个体户贷", "商户贷", "流水贷", "经营周转"],
    "消费贷": ["消费贷", "消费金融", "消费分期", "购物分期", "装修贷", "旅游贷", "教育分期"],
}

# 用户资质关键词
USER_QUALIFICATION_KEYWORDS = {
    "公积金": ["公积金", "公积金缴存", "公积金贷款", "公积金余额", "公积金基数"],
    "社保": ["社保", "社保缴纳", "社保记录", "连续社保", "社保满"],
    "个体户": ["个体户", "个体工商户", "营业执照", "小店主", "个体经营"],
    "企业主": ["企业主", "公司老板", "法人", "股东", "开公司", "企业法人"],
    "征信花": ["征信花", "查询多", "大数据花", "多次查询", "征信查询多", "查询次数多"],
    "负债高": ["负债高", "负债多", "负债率", "债务多", "欠款多", "负债比高"],
}

# 内容意图关键词
CONTENT_INTENT_KEYWORDS = {
    "科普": ["科普", "知识", "介绍", "什么是", "了解", "讲解", "干货", "基础知识", "入门"],
    "避坑": ["避坑", "注意", "千万别", "小心", "踩雷", "套路", "被骗", "陷阱", "防骗"],
    "案例": ["案例", "真实经历", "亲身经历", "分享", "故事", "经历", "实战", "成功案例"],
    "引流": ["引流", "私信", "咨询", "联系", "加V", "加微", "私信我", "评论区"],
    "转化": ["转化", "办理", "申请", "找我", "专业办理", "快速下款", "即刻办理"],
}


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
        "套现",
        "洗白",
        "黑户秒过",
        "包装资料",
        "刷流水",
        "百分百下款",
        "无视风控",
        "无视征信",
        "内部渠道",
    ]
    medium_risk_words = [
        "私信",
        "加v",
        "加微",
        "VX",
        "微信",
        "联系我",
        "中介",
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


# ============================================================
# 助贷业务专用标签检测函数
# ============================================================


def detect_product_type_tag(text: str) -> list[str]:
    """检测产品类型标签

    Args:
        text: 待检测的文本

    Returns:
        匹配到的产品类型标签列表
    """
    result = []
    for tag_name, keywords in PRODUCT_TYPE_KEYWORDS.items():
        if _contains_any(text, keywords):
            result.append(tag_name)
    return result


def detect_user_qualification_tags(text: str) -> list[str]:
    """检测用户资质标签

    Args:
        text: 待检测的文本

    Returns:
        匹配到的用户资质标签列表
    """
    result = []
    for tag_name, keywords in USER_QUALIFICATION_KEYWORDS.items():
        if _contains_any(text, keywords):
            result.append(tag_name)
    return result


def detect_content_intent_tag(text: str) -> str:
    """检测内容意图标签

    Args:
        text: 待检测的文本

    Returns:
        主要的内容意图标签（优先返回最匹配的）
    """
    # 优先级顺序：避坑 > 案例 > 转化 > 引流 > 科普
    priority_order = ["避坑", "案例", "转化", "引流", "科普"]

    for tag_name in priority_order:
        keywords = CONTENT_INTENT_KEYWORDS.get(tag_name, [])
        if _contains_any(text, keywords):
            return tag_name
    return "科普"  # 默认返回科普


def detect_platform_style_tag(text: str, platform: str | None = None) -> str:
    """检测平台风格标签

    基于文本特征和平台信息判断内容风格。

    Args:
        text: 待检测的文本
        platform: 可选的平台标识

    Returns:
        平台风格标签
    """
    # 视频平台默认口播
    if platform in ["douyin", "kuaishou", "shipinhao"]:
        return "口播"

    # 图文平台默认图文
    if platform in ["xiaohongshu", "weixin"]:
        # 检查是否有问答特征
        if _contains_any(text, ["问", "答", "是不是", "能不能", "为什么"]):
            return "问答"
        # 检查是否有经验帖特征
        if _contains_any(text, ["经验", "心得", "总结", "攻略"]):
            return "经验帖"
        return "图文"

    # 默认根据文本特征判断
    if _contains_any(text, ["视频", "口播", "真人出镜"]):
        return "口播"
    if _contains_any(text, ["问", "答", "Q&A", "答疑"]):
        return "问答"
    if _contains_any(text, ["经验", "心得", "总结", "攻略"]):
        return "经验帖"

    return "图文"


def detect_conversion_tendency_tag(text: str) -> str:
    """检测转化倾向标签

    Args:
        text: 待检测的文本

    Returns:
        转化倾向标签
    """
    # 强转化关键词
    strong_keywords = ["找我", "私信我", "加我", "咨询我", "专业办理", "快速办理", "即刻", "马上"]
    # 品牌向关键词
    brand_keywords = ["品牌", "口碑", "信誉", "专业团队", "多年经验", "服务"]

    if _contains_any(text, strong_keywords):
        return "强转化"
    if _contains_any(text, brand_keywords):
        return "品牌向"
    return "弱转化"


def tag_loan_content(title: str, content_text: str, platform: str | None = None) -> dict:
    """为助贷内容打标签（综合版）

    综合使用所有规则为助贷内容打标签。

    Args:
        title: 内容标题
        content_text: 内容正文
        platform: 可选的平台标识

    Returns:
        标签字典，包含各个维度的标签
    """
    merged = f"{title}\n{content_text}".strip()
    merged = re.sub(r"\s+", "", merged)

    # 基础标签
    topic_tag = detect_topic_tag(merged)
    intent_tag = detect_intent_tag(merged)
    crowd_tag = detect_crowd_tag(merged)
    risk_tag = detect_risk_tag(merged)

    # 助贷专用标签
    product_types = detect_product_type_tag(merged)
    user_quals = detect_user_qualification_tags(merged)
    content_intent = detect_content_intent_tag(merged)
    platform_style = detect_platform_style_tag(merged, platform)
    conversion_tendency = detect_conversion_tendency_tag(merged)

    return {
        # 基础标签
        "topic_tag": topic_tag,
        "intent_tag": intent_tag,
        "crowd_tag": crowd_tag,
        "risk_tag": risk_tag,
        # 助贷专用标签
        "product_types": product_types,
        "user_qualifications": user_quals,
        "content_intent": content_intent,
        "platform_style": platform_style,
        "conversion_tendency": conversion_tendency,
        # 热度分数
        "heat_score": calc_heat_score(merged),
    }
