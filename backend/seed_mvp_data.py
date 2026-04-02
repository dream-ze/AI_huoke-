"""MVP种子数据 - 运行方式: cd backend && python seed_mvp_data.py"""

import os
import random
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.crm import Customer, Lead
from app.models.follow_up import FollowUpRecord
from app.models.models import (
    AutoRewriteTemplate,
    MvpComplianceRule,
    MvpInboxItem,
    MvpPromptTemplate,
    MvpTag,
    PlatformComplianceRule,
)
from app.models.publish_account import PublishAccount
from app.models.published_content import PublishedContent


def seed_tags(db):
    """种子标签数据 - 30+条"""
    tags_data = [
        # platform - 平台标签
        {"name": "小红书", "type": "platform"},
        {"name": "抖音", "type": "platform"},
        {"name": "知乎", "type": "platform"},
        {"name": "微博", "type": "platform"},
        {"name": "快手", "type": "platform"},
        # audience - 受众人群
        {"name": "负债人群", "type": "audience"},
        {"name": "上班族", "type": "audience"},
        {"name": "个体户/老板", "type": "audience"},
        {"name": "大学生", "type": "audience"},
        {"name": "宝妈群体", "type": "audience"},
        {"name": "中年人群", "type": "audience"},
        {"name": "征信修复人群", "type": "audience"},
        # style - 内容风格
        {"name": "专业型", "type": "style"},
        {"name": "口语型", "type": "style"},
        {"name": "种草型", "type": "style"},
        {"name": "避坑型", "type": "style"},
        {"name": "故事型", "type": "style"},
        {"name": "干货型", "type": "style"},
        # topic - 主题分类
        {"name": "贷款申请", "type": "topic"},
        {"name": "征信修复", "type": "topic"},
        {"name": "信用卡使用", "type": "topic"},
        {"name": "房贷公积金", "type": "topic"},
        {"name": "创业融资", "type": "topic"},
        # scenario - 场景标签
        {"name": "急需用钱", "type": "scenario"},
        {"name": "以贷养贷", "type": "scenario"},
        {"name": "首次贷款", "type": "scenario"},
        {"name": "经营周转", "type": "scenario"},
        {"name": "消费分期", "type": "scenario"},
        # content_type - 内容类型
        {"name": "干货型", "type": "content_type"},
        {"name": "故事型", "type": "content_type"},
        {"name": "测评型", "type": "content_type"},
        {"name": "问答型", "type": "content_type"},
        {"name": "清单型", "type": "content_type"},
        # product_type - 产品类型
        {"name": "信贷", "type": "product_type"},
        {"name": "抵押", "type": "product_type"},
        {"name": "企业贷", "type": "product_type"},
        {"name": "经营贷", "type": "product_type"},
        {"name": "消费贷", "type": "product_type"},
        # user_qualification - 用户资质
        {"name": "公积金", "type": "user_qualification"},
        {"name": "社保", "type": "user_qualification"},
        {"name": "个体户", "type": "user_qualification"},
        {"name": "企业主", "type": "user_qualification"},
        {"name": "征信花", "type": "user_qualification"},
        {"name": "负债高", "type": "user_qualification"},
        # content_intent - 内容意图
        {"name": "科普", "type": "content_intent"},
        {"name": "避坑", "type": "content_intent"},
        {"name": "案例", "type": "content_intent"},
        {"name": "引流", "type": "content_intent"},
        {"name": "转化", "type": "content_intent"},
        # platform_format - 平台格式
        {"name": "口播", "type": "platform_format"},
        {"name": "图文", "type": "platform_format"},
        {"name": "问答", "type": "platform_format"},
        {"name": "经验帖", "type": "platform_format"},
        # risk_level - 风险等级
        {"name": "低风险", "type": "risk_level"},
        {"name": "中风险", "type": "risk_level"},
        {"name": "高风险", "type": "risk_level"},
        # conversion_tendency - 转化倾向
        {"name": "强转化", "type": "conversion_tendency"},
        {"name": "弱转化", "type": "conversion_tendency"},
        {"name": "品牌向", "type": "conversion_tendency"},
    ]

    created = 0
    for tag_data in tags_data:
        existing = db.query(MvpTag).filter(MvpTag.name == tag_data["name"], MvpTag.type == tag_data["type"]).first()
        if not existing:
            db.add(MvpTag(**tag_data))
            created += 1

    db.commit()
    print(f"[标签] 已创建 {created} 条，跳过 {len(tags_data) - created} 条已存在")


def seed_compliance_rules(db):
    """种子合规规则 - 25+条"""
    rules_data = [
        # high 级别 - 严禁使用
        {"rule_type": "keyword", "keyword": "必过", "risk_level": "high", "suggestion": "删除该词，使用'审核快速'替代"},
        {"rule_type": "keyword", "keyword": "包过", "risk_level": "high", "suggestion": "删除该词，使用'通过率高'替代"},
        {"rule_type": "keyword", "keyword": "秒批", "risk_level": "high", "suggestion": "删除该词，使用'快速审批'替代"},
        {
            "rule_type": "keyword",
            "keyword": "黑户可贷",
            "risk_level": "high",
            "suggestion": "删除该词，不得针对征信黑户宣传",
        },
        {
            "rule_type": "keyword",
            "keyword": "无视征信",
            "risk_level": "high",
            "suggestion": "删除该词，不得忽视征信审核",
        },
        {"rule_type": "keyword", "keyword": "100%通过", "risk_level": "high", "suggestion": "删除该词，不得承诺通过率"},
        {"rule_type": "keyword", "keyword": "秒放款", "risk_level": "high", "suggestion": "删除该词，使用'放款快'替代"},
        {
            "rule_type": "keyword",
            "keyword": "不看征信",
            "risk_level": "high",
            "suggestion": "删除该词，所有正规贷款都需审核征信",
        },
        {
            "rule_type": "keyword",
            "keyword": "白户秒批",
            "risk_level": "high",
            "suggestion": "删除该词，白户同样需要正常审批",
        },
        {
            "rule_type": "keyword",
            "keyword": "征信花也能下",
            "risk_level": "high",
            "suggestion": "删除该词，不得承诺征信不良可贷",
        },
        # medium 级别 - 谨慎使用
        {
            "rule_type": "keyword",
            "keyword": "低门槛",
            "risk_level": "medium",
            "suggestion": "建议改为'申请便捷'或说明具体条件",
        },
        {
            "rule_type": "keyword",
            "keyword": "快速放款",
            "risk_level": "medium",
            "suggestion": "建议说明具体时间范围，如'1-3个工作日'",
        },
        {
            "rule_type": "keyword",
            "keyword": "零利息",
            "risk_level": "medium",
            "suggestion": "需注明适用期限和条件，避免误导",
        },
        {"rule_type": "keyword", "keyword": "免息", "risk_level": "medium", "suggestion": "需注明免息期限和后续利率"},
        {
            "rule_type": "keyword",
            "keyword": "不上征信",
            "risk_level": "medium",
            "suggestion": "需核实产品实际情况，正规产品一般上征信",
        },
        {
            "rule_type": "keyword",
            "keyword": "随借随还",
            "risk_level": "medium",
            "suggestion": "需注明是否有提前还款手续费",
        },
        {"rule_type": "keyword", "keyword": "超低利率", "risk_level": "medium", "suggestion": "需注明具体年化利率数字"},
        {"rule_type": "keyword", "keyword": "门槛低", "risk_level": "medium", "suggestion": "建议说明具体申请条件"},
        {
            "rule_type": "keyword",
            "keyword": "无抵押",
            "risk_level": "medium",
            "suggestion": "建议说明信用贷款的具体要求",
        },
        {
            "rule_type": "keyword",
            "keyword": "无担保",
            "risk_level": "medium",
            "suggestion": "建议说明信用贷款的审核标准",
        },
        # low 级别 - 可使用但注意
        {"rule_type": "keyword", "keyword": "利率低", "risk_level": "low", "suggestion": "建议标注具体年化利率"},
        {"rule_type": "keyword", "keyword": "额度高", "risk_level": "low", "suggestion": "建议说明额度范围和审批依据"},
        {"rule_type": "keyword", "keyword": "快速审批", "risk_level": "low", "suggestion": "可使用，建议说明大致时间"},
        {"rule_type": "keyword", "keyword": "线上申请", "risk_level": "low", "suggestion": "可正常使用"},
        {"rule_type": "keyword", "keyword": "手机申请", "risk_level": "low", "suggestion": "可正常使用"},
        {"rule_type": "keyword", "keyword": "放款快", "risk_level": "low", "suggestion": "可使用，建议注明具体时效"},
    ]

    created = 0
    for rule_data in rules_data:
        existing = db.query(MvpComplianceRule).filter(MvpComplianceRule.keyword == rule_data["keyword"]).first()
        if not existing:
            db.add(MvpComplianceRule(**rule_data))
            created += 1

    db.commit()
    print(f"[合规规则] 已创建 {created} 条，跳过 {len(rules_data) - created} 条已存在")


def seed_prompt_templates(db):
    """种子Prompt模板 - 5条"""
    templates_data = [
        {
            "platform": None,
            "audience": None,
            "style": None,
            "template": """你是一个专业的贷款内容创作助手。请根据以下素材改写一篇新的内容：

【原始素材】
{input_text}

【改写要求】
1. 保持核心信息不变
2. 改变表达方式，避免重复
3. 语言自然流畅
4. 符合平台调性

请输出改写后的内容：""",
        },
        {
            "platform": "xiaohongshu",
            "audience": None,
            "style": "种草型",
            "template": """你是小红书爆款文案写手。请将以下内容改写成小红书风格：

【原始内容】
{input_text}

【小红书风格要求】
1. 标题：使用emoji + 数字 + 痛点/利益点
2. 开头：直接抛出痛点或成果
3. 正文：分点陈述，每点一行
4. 结尾：引导评论或收藏
5. 语气：亲切、真诚、有温度

请输出：
【标题】
【正文】""",
        },
        {
            "platform": "douyin",
            "audience": None,
            "style": "口语型",
            "template": """你是抖音口播文案专家。请将以下内容改写成抖音口播脚本：

【原始内容】
{input_text}

【口播脚本要求】
1. 开头3秒：抓人眼球的hook
2. 中间：干货内容，简洁有力
3. 结尾：引导关注或评论
4. 语气：口语化、有节奏感
5. 时长：控制在30-60秒可读完

请输出口播脚本：""",
        },
        {
            "platform": None,
            "audience": None,
            "style": "专业型",
            "template": """你是爆款内容仿写专家。请分析以下爆款内容并仿写一篇新内容：

【爆款原文】
{input_text}

【仿写要求】
1. 分析原文的标题公式
2. 提取核心结构框架
3. 保持爆款元素（痛点、利益点、情绪点）
4. 更换具体案例和数据
5. 保持相似的节奏和语气

请先分析爆款要素，然后输出仿写内容：""",
        },
        {
            "platform": None,
            "audience": None,
            "style": None,
            "template": """你是金融内容合规审核专家。请检查以下内容的合规性并改写：

【待审内容】
{input_text}

【合规要求】
1. 不得使用"必过""秒批""100%通过"等承诺性词汇
2. 不得宣传"黑户可贷""不看征信"等违规信息
3. 利率说明需准确，不得使用"零利息"等误导词汇
4. 不得做虚假或夸大的收益承诺

请输出：
【风险点】（列出发现的违规内容）
【改写后内容】（合规版本）""",
        },
    ]

    created = 0
    for tmpl_data in templates_data:
        existing = (
            db.query(MvpPromptTemplate)
            .filter(
                MvpPromptTemplate.platform == tmpl_data["platform"],
                MvpPromptTemplate.audience == tmpl_data["audience"],
                MvpPromptTemplate.style == tmpl_data["style"],
            )
            .first()
        )
        if not existing:
            db.add(MvpPromptTemplate(**tmpl_data))
            created += 1

    db.commit()
    print(f"[Prompt模板] 已创建 {created} 条，跳过 {len(templates_data) - created} 条已存在")


def seed_inbox_items(db):
    """种子收件箱示例数据 - 5条"""
    inbox_data = [
        {
            "platform": "xiaohongshu",
            "title": "上班族贷款攻略｜月入5000如何申请10万额度",
            "content": """很多姐妹问我，月薪只有5000，能申请到多少贷款？

今天给大家分享我的亲身经历：
1. 首先养好征信，不要乱查
2. 信用卡正常使用，按时还款
3. 银行流水很重要！
4. 选择正规银行渠道

我用这个方法，成功申请到了10万额度，利率才4.5%！

有问题评论区问我～""",
            "author": "理财小姐姐",
            "source_url": "https://www.xiaohongshu.com/explore/example1",
            "source_type": "collect",
            "keyword": "上班族贷款",
            "risk_level": "low",
            "score": 85.0,
        },
        {
            "platform": "douyin",
            "title": "负债30万，我是这样上岸的",
            "content": """很多人问我，欠了30万怎么办？

别慌，我来告诉你：
第一步：盘点所有债务
第二步：和家人坦白
第三步：制定还款计划
第四步：增加收入来源

千万不要以贷养贷！这是深渊！

我用了2年时间，终于还清了。你也可以！""",
            "author": "债务规划师老王",
            "source_url": "https://www.douyin.com/video/example2",
            "source_type": "collect",
            "keyword": "负债上岸",
            "risk_level": "low",
            "score": 90.0,
        },
        {
            "platform": "zhihu",
            "title": "个体户如何申请经营贷？利率最低能到多少？",
            "content": """作为银行从业10年的信贷经理，今天系统讲一下个体户经营贷：

一、申请条件
1. 营业执照满1年
2. 有稳定经营流水
3. 征信良好

二、利率区间
目前市场上经营贷利率在3.2%-6%之间，具体看：
- 抵押物情况
- 经营年限
- 行业类型

三、注意事项
1. 不要听信"秒批"宣传
2. 正规银行渠道最安全
3. 利率过低要警惕

有问题可以评论交流。""",
            "author": "银行老张说信贷",
            "source_url": "https://www.zhihu.com/answer/example3",
            "source_type": "collect",
            "keyword": "个体户经营贷",
            "risk_level": "low",
            "score": 88.0,
        },
        {
            "platform": "xiaohongshu",
            "title": "征信查询多了怎么办？教你3招补救",
            "content": """征信被查花了？别急，看这篇！

很多人不知道，征信查询次数太多会影响贷款申请。

补救方法：
1️⃣ 停止申请新的贷款/信用卡（至少3个月）
2️⃣ 保持现有账户正常还款
3️⃣ 适当使用信用卡增加活跃度

一般3-6个月后，银行就不太在意之前的查询记录了。

关键是：不要再乱点网贷申请！

码住这篇，对你有用的话点个赞～""",
            "author": "征信修复顾问",
            "source_url": "https://www.xiaohongshu.com/explore/example4",
            "source_type": "collect",
            "keyword": "征信修复",
            "risk_level": "medium",
            "score": 75.0,
        },
        {
            "platform": "weibo",
            "title": "【科普】公积金贷款和商业贷款的区别",
            "content": """#房贷知识# #公积金贷款#

很多人买房前都在纠结：公积金贷款还是商业贷款？

简单说下区别：

【利率】
公积金：3.1%（首套）
商贷：4.2%左右

【额度】
公积金：有上限（各地不同）
商贷：看收入和房价

【审批】
公积金：较慢，1-2个月
商贷：较快，2-3周

建议：能用公积金就用公积金，不够的部分再商贷。

转发给需要的朋友！""",
            "author": "房产小百科",
            "source_url": "https://weibo.com/status/example5",
            "source_type": "collect",
            "keyword": "公积金贷款",
            "risk_level": "low",
            "score": 82.0,
        },
    ]

    created = 0
    for item_data in inbox_data:
        existing = db.query(MvpInboxItem).filter(MvpInboxItem.title == item_data["title"]).first()
        if not existing:
            db.add(MvpInboxItem(**item_data))
            created += 1

    db.commit()
    print(f"[收件箱示例] 已创建 {created} 条，跳过 {len(inbox_data) - created} 条已存在")


def seed_platform_rules(db):
    """种子平台合规规则 - 每平台10+条，共40+条"""
    rules_data = [
        # ========== 小红书规则 (12条) ==========
        {
            "platform": "xiaohongshu",
            "rule_category": "引流禁止",
            "keyword_or_pattern": "点击链接",
            "risk_level": "high",
            "description": "禁止直接引导用户点击外部链接",
            "suggestion": '使用"了解更多"或"查看详情"替代',
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "引流禁止",
            "keyword_or_pattern": "加微信",
            "risk_level": "high",
            "description": "禁止直接引导添加微信",
            "suggestion": "引导私信或评论区互动",
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "引流禁止",
            "keyword_or_pattern": "二维码",
            "risk_level": "high",
            "description": "禁止提及二维码引流",
            "suggestion": "移除二维码相关内容",
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "百分百",
            "risk_level": "high",
            "description": "禁止使用绝对承诺词汇",
            "suggestion": '使用"通过率较高"替代',
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "承诺利率",
            "risk_level": "medium",
            "description": "不得承诺具体利率",
            "suggestion": "说明利率以实际审批为准",
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "黑户秒批",
            "risk_level": "high",
            "description": "禁止针对征信黑户的承诺",
            "suggestion": '使用"多种方案可选"替代',
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "诱导禁止",
            "keyword_or_pattern": "私信留联系方式",
            "risk_level": "medium",
            "description": "禁止诱导用户私信留联系方式",
            "suggestion": "引导合规互动方式",
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "真实性",
            "keyword_or_pattern": "虚假案例",
            "risk_level": "high",
            "description": "禁止编造虚假案例",
            "suggestion": "使用真实案例或通用说明",
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "真实性",
            "keyword_or_pattern": "夸大还款能力",
            "risk_level": "medium",
            "description": "不得夸大还款能力",
            "suggestion": "客观描述产品特点",
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "必下款",
            "risk_level": "high",
            "description": "禁止承诺必下款",
            "suggestion": '使用"方案匹配度高"替代',
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "金融推广",
            "keyword_or_pattern": "直接金融推广",
            "risk_level": "medium",
            "description": "避免直接金融产品推广",
            "suggestion": "以科普或经验分享形式呈现",
        },
        {
            "platform": "xiaohongshu",
            "rule_category": "诱导禁止",
            "keyword_or_pattern": "诱导分享",
            "risk_level": "medium",
            "description": "禁止诱导分享行为",
            "suggestion": "提供有价值内容自然吸引",
        },
        # ========== 抖音规则 (12条) ==========
        {
            "platform": "douyin",
            "rule_category": "引流禁止",
            "keyword_or_pattern": "私信我",
            "risk_level": "high",
            "description": "禁止引导用户私信",
            "suggestion": "引导评论区互动",
        },
        {
            "platform": "douyin",
            "rule_category": "利率禁止",
            "keyword_or_pattern": r"\\d+\\.\\d+%",
            "risk_level": "medium",
            "description": "避免出现具体利率数字",
            "suggestion": "说明利率区间或以实际为准",
        },
        {
            "platform": "douyin",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "承诺收益",
            "risk_level": "high",
            "description": "禁止承诺收益",
            "suggestion": "客观描述产品特点",
        },
        {
            "platform": "douyin",
            "rule_category": "引流禁止",
            "keyword_or_pattern": "点击下方链接",
            "risk_level": "high",
            "description": "禁止引导点击链接",
            "suggestion": "引导关注账号或私信",
        },
        {
            "platform": "douyin",
            "rule_category": "引流禁止",
            "keyword_or_pattern": "免费咨询",
            "risk_level": "medium",
            "description": "避免直接免费咨询引流",
            "suggestion": "提供有价值内容吸引",
        },
        {
            "platform": "douyin",
            "rule_category": "利率禁止",
            "keyword_or_pattern": "利率对比",
            "risk_level": "medium",
            "description": "避免利率对比误导",
            "suggestion": "客观说明产品优势",
        },
        {
            "platform": "douyin",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "不看征信",
            "risk_level": "high",
            "description": "禁止声称不看征信",
            "suggestion": "说明征信要求灵活",
        },
        {
            "platform": "douyin",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "当天放款",
            "risk_level": "high",
            "description": "禁止承诺当天放款",
            "suggestion": "说明审批时效范围",
        },
        {
            "platform": "douyin",
            "rule_category": "真实性",
            "keyword_or_pattern": "虚假成功率",
            "risk_level": "high",
            "description": "禁止编造成功率",
            "suggestion": "使用真实数据或不予提及",
        },
        {
            "platform": "douyin",
            "rule_category": "诱导禁止",
            "keyword_or_pattern": "评论区留联系方式",
            "risk_level": "medium",
            "description": "禁止诱导评论区留联系方式",
            "suggestion": "引导合规互动",
        },
        {
            "platform": "douyin",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "稳下",
            "risk_level": "high",
            "description": "禁止承诺稳下",
            "suggestion": '使用"通过率不错"替代',
        },
        {
            "platform": "douyin",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "必批",
            "risk_level": "high",
            "description": "禁止承诺必批",
            "suggestion": '使用"审批效率高"替代',
        },
        # ========== 知乎规则 (12条) ==========
        {
            "platform": "zhihu",
            "rule_category": "内容风格",
            "keyword_or_pattern": "软文痕迹",
            "risk_level": "medium",
            "description": "避免软文痕迹过重",
            "suggestion": "以专业问答形式呈现",
        },
        {
            "platform": "zhihu",
            "rule_category": "内容风格",
            "keyword_or_pattern": "过度口语化",
            "risk_level": "low",
            "description": "知乎用户偏好专业内容",
            "suggestion": "保持专业严谨风格",
        },
        {
            "platform": "zhihu",
            "rule_category": "广告禁止",
            "keyword_or_pattern": "明显广告植入",
            "risk_level": "high",
            "description": "禁止明显广告植入",
            "suggestion": "以经验分享形式呈现",
        },
        {
            "platform": "zhihu",
            "rule_category": "引流禁止",
            "keyword_or_pattern": "私信了解",
            "risk_level": "medium",
            "description": "避免直接引导私信",
            "suggestion": "提供公开专业解答",
        },
        {
            "platform": "zhihu",
            "rule_category": "真实性",
            "keyword_or_pattern": "虚假身份背书",
            "risk_level": "high",
            "description": "禁止虚假身份背书",
            "suggestion": "使用真实专业背景",
        },
        {
            "platform": "zhihu",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "利率承诺",
            "risk_level": "medium",
            "description": "不得承诺具体利率",
            "suggestion": "说明利率以实际为准",
        },
        {
            "platform": "zhihu",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "包过",
            "risk_level": "high",
            "description": "禁止承诺包过",
            "suggestion": "客观分析申请条件",
        },
        {
            "platform": "zhihu",
            "rule_category": "诱导禁止",
            "keyword_or_pattern": "诱导点赞收藏",
            "risk_level": "low",
            "description": "避免诱导点赞收藏",
            "suggestion": "以内容质量自然吸引",
        },
        {
            "platform": "zhihu",
            "rule_category": "真实性",
            "keyword_or_pattern": "夸大产品优势",
            "risk_level": "medium",
            "description": "不得夸大产品优势",
            "suggestion": "客观对比分析",
        },
        {
            "platform": "zhihu",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "全网最低",
            "risk_level": "medium",
            "description": "禁止使用全网最低等表述",
            "suggestion": "说明利率有竞争力",
        },
        {
            "platform": "zhihu",
            "rule_category": "内容风格",
            "keyword_or_pattern": "标题党",
            "risk_level": "medium",
            "description": "避免标题党",
            "suggestion": "使用专业准确标题",
        },
        {
            "platform": "zhihu",
            "rule_category": "引流禁止",
            "keyword_or_pattern": "加好友",
            "risk_level": "medium",
            "description": "禁止引导添加好友",
            "suggestion": "引导知乎站内互动",
        },
        # ========== 微信规则 (12条) ==========
        {
            "platform": "weixin",
            "rule_category": "诱导禁止",
            "keyword_or_pattern": "诱导分享",
            "risk_level": "high",
            "description": "禁止诱导分享",
            "suggestion": "以内容价值吸引自然传播",
        },
        {
            "platform": "weixin",
            "rule_category": "真实性",
            "keyword_or_pattern": "夸大表述",
            "risk_level": "medium",
            "description": "避免夸大表述",
            "suggestion": "使用客观准确描述",
        },
        {
            "platform": "weixin",
            "rule_category": "真实性",
            "keyword_or_pattern": "虚假案例",
            "risk_level": "high",
            "description": "禁止虚假案例",
            "suggestion": "使用真实案例或通用说明",
        },
        {
            "platform": "weixin",
            "rule_category": "诱导禁止",
            "keyword_or_pattern": "转发有奖",
            "risk_level": "high",
            "description": "禁止转发有奖诱导",
            "suggestion": "提供有价值内容",
        },
        {
            "platform": "weixin",
            "rule_category": "诱导禁止",
            "keyword_or_pattern": "限时优惠",
            "risk_level": "medium",
            "description": "避免施压式限时优惠",
            "suggestion": "客观说明优惠信息",
        },
        {
            "platform": "weixin",
            "rule_category": "利率禁止",
            "keyword_or_pattern": "利率误导",
            "risk_level": "medium",
            "description": "避免利率误导",
            "suggestion": "准确说明利率信息",
        },
        {
            "platform": "weixin",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "无条件贷款",
            "risk_level": "high",
            "description": "禁止无条件贷款承诺",
            "suggestion": "说明申请条件",
        },
        {
            "platform": "weixin",
            "rule_category": "真实性",
            "keyword_or_pattern": "虚假客户证言",
            "risk_level": "high",
            "description": "禁止虚假客户证言",
            "suggestion": "使用真实反馈或不予提及",
        },
        {
            "platform": "weixin",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "秒到账",
            "risk_level": "high",
            "description": "禁止承诺秒到账",
            "suggestion": "说明到账时效范围",
        },
        {
            "platform": "weixin",
            "rule_category": "诱导禁止",
            "keyword_or_pattern": "诱导添加好友",
            "risk_level": "medium",
            "description": "避免诱导添加好友",
            "suggestion": "提供公众号内服务",
        },
        {
            "platform": "weixin",
            "rule_category": "承诺禁止",
            "keyword_or_pattern": "百分百通过",
            "risk_level": "high",
            "description": "禁止百分百通过承诺",
            "suggestion": '使用"通过率较高"替代',
        },
        {
            "platform": "weixin",
            "rule_category": "真实性",
            "keyword_or_pattern": "收益承诺",
            "risk_level": "high",
            "description": "禁止收益承诺",
            "suggestion": "客观描述产品特点",
        },
    ]

    created = 0
    for rule_data in rules_data:
        existing = (
            db.query(PlatformComplianceRule)
            .filter(
                PlatformComplianceRule.platform == rule_data["platform"],
                PlatformComplianceRule.keyword_or_pattern == rule_data["keyword_or_pattern"],
            )
            .first()
        )
        if not existing:
            db.add(PlatformComplianceRule(**rule_data))
            created += 1

    db.commit()
    print(f"[平台规则] 已创建 {created} 条，跳过 {len(rules_data) - created} 条已存在")


def seed_rewrite_templates(db):
    """种子改写模板 - 30+条"""
    templates_data = [
        # ========== 承诺类 (10条) ==========
        {"trigger_pattern": "必过", "safe_alternative": "通过率较高", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "包过", "safe_alternative": "成功率较高", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "秒批", "safe_alternative": "审批效率高", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "100%通过", "safe_alternative": "通过率较高", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "保证下款", "safe_alternative": "方案匹配度高", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "必下", "safe_alternative": "成功率较高", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "稳下", "safe_alternative": "通过率不错", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "包下款", "safe_alternative": "匹配合适方案", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "一定能批", "safe_alternative": "有较大概率", "risk_level": "high", "category": "承诺类"},
        {"trigger_pattern": "绝对能过", "safe_alternative": "审批通过率高", "risk_level": "high", "category": "承诺类"},
        # ========== 利率类 (10条) ==========
        {"trigger_pattern": "最低利率", "safe_alternative": "利率低至", "risk_level": "medium", "category": "利率类"},
        {"trigger_pattern": "零利息", "safe_alternative": "优惠利率", "risk_level": "medium", "category": "利率类"},
        {"trigger_pattern": "免息", "safe_alternative": "限时优惠", "risk_level": "medium", "category": "利率类"},
        {"trigger_pattern": "无利息", "safe_alternative": "低息方案", "risk_level": "medium", "category": "利率类"},
        {"trigger_pattern": "利息最低", "safe_alternative": "利率有优势", "risk_level": "medium", "category": "利率类"},
        {
            "trigger_pattern": "比银行还低",
            "safe_alternative": "利率有竞争力",
            "risk_level": "medium",
            "category": "利率类",
        },
        {"trigger_pattern": "0利率", "safe_alternative": "优惠利率政策", "risk_level": "medium", "category": "利率类"},
        {
            "trigger_pattern": "全网最低",
            "safe_alternative": "利率较有优势",
            "risk_level": "medium",
            "category": "利率类",
        },
        {"trigger_pattern": "无手续费", "safe_alternative": "费用透明", "risk_level": "medium", "category": "利率类"},
        {"trigger_pattern": "免费办理", "safe_alternative": "咨询不收费", "risk_level": "medium", "category": "利率类"},
        # ========== 资质类 (10条) ==========
        {"trigger_pattern": "无视征信", "safe_alternative": "征信要求宽松", "risk_level": "high", "category": "资质类"},
        {"trigger_pattern": "黑户可贷", "safe_alternative": "多种方案可选", "risk_level": "high", "category": "资质类"},
        {
            "trigger_pattern": "不查征信",
            "safe_alternative": "对征信要求灵活",
            "risk_level": "high",
            "category": "资质类",
        },
        {
            "trigger_pattern": "白户秒批",
            "safe_alternative": "新用户也可申请",
            "risk_level": "high",
            "category": "资质类",
        },
        {"trigger_pattern": "逾期也能贷", "safe_alternative": "有专属方案", "risk_level": "high", "category": "资质类"},
        {
            "trigger_pattern": "征信花也行",
            "safe_alternative": "提供多种选择",
            "risk_level": "high",
            "category": "资质类",
        },
        {
            "trigger_pattern": "什么都不要",
            "safe_alternative": "申请门槛较低",
            "risk_level": "medium",
            "category": "资质类",
        },
        {
            "trigger_pattern": "不看资质",
            "safe_alternative": "申请条件灵活",
            "risk_level": "medium",
            "category": "资质类",
        },
        {
            "trigger_pattern": "无条件贷款",
            "safe_alternative": "多种方案匹配",
            "risk_level": "high",
            "category": "资质类",
        },
        {
            "trigger_pattern": "随便贷",
            "safe_alternative": "提供个性化方案",
            "risk_level": "medium",
            "category": "资质类",
        },
        # ========== 引流类 (10条) ==========
        {
            "trigger_pattern": "点击链接",
            "safe_alternative": "了解更多",
            "risk_level": "high",
            "category": "引流类",
            "platform_scope": "xiaohongshu,douyin",
        },
        {
            "trigger_pattern": "加微信",
            "safe_alternative": "私信咨询",
            "risk_level": "high",
            "category": "引流类",
            "platform_scope": "xiaohongshu,douyin,zhihu",
        },
        {
            "trigger_pattern": "私信我",
            "safe_alternative": "评论区留言",
            "risk_level": "high",
            "category": "引流类",
            "platform_scope": "douyin",
        },
        {"trigger_pattern": "加好友", "safe_alternative": "关注账号", "risk_level": "medium", "category": "引流类"},
        {"trigger_pattern": "扫描二维码", "safe_alternative": "查看详情", "risk_level": "high", "category": "引流类"},
        {
            "trigger_pattern": "点击下方",
            "safe_alternative": "查看更多",
            "risk_level": "high",
            "category": "引流类",
            "platform_scope": "douyin",
        },
        {
            "trigger_pattern": "免费咨询",
            "safe_alternative": "了解更多信息",
            "risk_level": "medium",
            "category": "引流类",
        },
        {
            "trigger_pattern": "转发有奖",
            "safe_alternative": "参与活动",
            "risk_level": "high",
            "category": "引流类",
            "platform_scope": "weixin",
        },
        {
            "trigger_pattern": "限时优惠",
            "safe_alternative": "当前优惠",
            "risk_level": "medium",
            "category": "引流类",
            "platform_scope": "weixin",
        },
        {
            "trigger_pattern": "分享得",
            "safe_alternative": "推荐给朋友",
            "risk_level": "medium",
            "category": "引流类",
            "platform_scope": "weixin",
        },
    ]

    created = 0
    for tmpl_data in templates_data:
        existing = (
            db.query(AutoRewriteTemplate)
            .filter(
                AutoRewriteTemplate.trigger_pattern == tmpl_data["trigger_pattern"],
                AutoRewriteTemplate.category == tmpl_data.get("category"),
            )
            .first()
        )
        if not existing:
            db.add(AutoRewriteTemplate(**tmpl_data))
            created += 1

    db.commit()
    print(f"[改写模板] 已创建 {created} 条，跳过 {len(templates_data) - created} 条已存在")


def seed_dashboard_demo_data(db, owner_id: int = 1):
    """Dashboard演示数据 - 包含线索、客户、发布账号等完整业务数据"""
    print("\n[Dashboard演示数据] 开始生成...")

    # 获取或创建演示用户
    from app.models.models import User

    user = db.query(User).filter(User.id == owner_id).first()
    if not user:
        # 创建演示用户
        user = db.query(User).filter(User.username == "demo").first()
        if not user:
            user = User(username="demo", email="demo@example.com", hashed_password="demo_password_hash", is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        owner_id = user.id

    # ========== 1. 创建发布账号 ==========
    accounts_data = [
        {"account_name": "助贷达人-小红书", "platform": "xiaohongshu", "account_id": "xhs_demo_001"},
        {"account_name": "贷款攻略-抖音", "platform": "douyin", "account_id": "dy_demo_001"},
        {"account_name": "金融科普-知乎", "platform": "zhihu", "account_id": "zh_demo_001"},
        {"account_name": "信贷服务-微信", "platform": "weixin", "account_id": "wx_demo_001"},
    ]

    created_accounts = []
    for acc_data in accounts_data:
        existing = db.query(PublishAccount).filter(PublishAccount.account_id == acc_data["account_id"]).first()
        if not existing:
            account = PublishAccount(owner_id=owner_id, **acc_data)
            db.add(account)
            created_accounts.append(account)
        else:
            created_accounts.append(existing)

    if created_accounts:
        db.commit()
        for acc in created_accounts:
            db.refresh(acc)
    print(f"[发布账号] 已创建/更新 {len(accounts_data)} 个账号")

    # ========== 2. 创建已发布内容 ==========
    content_templates = [
        {"title": "上班族贷款攻略｜月入5000如何申请10万额度", "platform": "xiaohongshu"},
        {"title": "负债30万，我是这样上岸的", "platform": "douyin"},
        {"title": "个体户如何申请经营贷？利率最低能到多少？", "platform": "zhihu"},
        {"title": "征信查询多了怎么办？教你3招补救", "platform": "xiaohongshu"},
        {"title": "公积金贷款和商业贷款的区别", "platform": "weixin"},
        {"title": "信用卡逾期了怎么办？别慌，有办法", "platform": "douyin"},
        {"title": "房贷提前还款划算吗？算笔账给你看", "platform": "zhihu"},
        {"title": "以贷养贷的陷阱，你一定要知道", "platform": "xiaohongshu"},
    ]

    created_contents = []
    for i, tmpl in enumerate(content_templates):
        account = created_accounts[i % len(created_accounts)]

        # 随机生成互动数据
        views = random.randint(1000, 50000)
        wechat_adds = random.randint(5, min(views // 100, 200))
        leads_count = random.randint(wechat_adds // 2, wechat_adds)

        content = PublishedContent(
            publish_account_id=account.id,
            platform=tmpl["platform"],
            title=tmpl["title"],
            content_text=f"这是{tmpl['title']}的示例内容...",
            post_url=f"https://example.com/content_{i:03d}",
            views=views,
            likes=random.randint(views // 20, views // 5),
            comments=random.randint(views // 100, views // 20),
            shares=random.randint(views // 200, views // 50),
            wechat_adds=wechat_adds,
            leads_count=leads_count,
            publish_time=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
        )
        db.add(content)
        created_contents.append(content)

    if created_contents:
        db.commit()
        for c in created_contents:
            db.refresh(c)
    print(f"[已发布内容] 已创建 {len(created_contents)} 条内容")

    # ========== 3. 创建线索数据（30+条）==========
    # 平台分布：小红书 40%、抖音 35%、知乎 15%、微信 10%
    platforms_dist = ["xiaohongshu"] * 12 + ["douyin"] * 11 + ["zhihu"] * 5 + ["weixin"] * 2
    # 分级分布：A 级 15%、B 级 30%、C 级 35%、D 级 20%
    grades_dist = ["A"] * 5 + ["B"] * 9 + ["C"] * 10 + ["D"] * 6

    # 中文昵称池
    nicknames = [
        "小明",
        "李华",
        "王芳",
        "张伟",
        "刘洋",
        "陈静",
        "杨帆",
        "赵敏",
        "黄磊",
        "周杰",
        "吴倩",
        "徐丽",
        "孙强",
        "马超",
        "朱婷",
        "胡军",
        "郭明",
        "林娜",
        "何伟",
        "高峰",
        "梁静",
        "宋阳",
        "郑浩",
        "谢薇",
        "韩梅",
        "唐勇",
        "冯磊",
        "于洋",
        "董洁",
        "萧峰",
        "程英",
        "曹颖",
        "袁华",
        "邓敏",
        "许强",
        "傅红",
        "沈冰",
        "曾黎",
        "彭丹",
        "吕良",
    ]

    # 行业池
    industries = [
        "互联网",
        "金融",
        "教育",
        "医疗",
        "制造业",
        "房地产",
        "零售",
        "餐饮",
        "物流",
        "咨询",
        "法律",
        "设计",
        "建筑",
        "能源",
        "传媒",
    ]

    # 职业池
    occupations = [
        "程序员",
        "产品经理",
        "销售经理",
        "财务专员",
        "人事主管",
        "市场经理",
        "设计师",
        "运营专员",
        "教师",
        "医生",
        "律师",
        "工程师",
        "创业者",
        "自由职业",
        "公务员",
        "银行职员",
        "保险顾问",
        "房产中介",
    ]

    # 贷款需求类型
    loan_types = ["房贷", "车贷", "消费贷", "经营贷", "信用贷"]

    created_leads = []
    for i in range(30):
        platform = random.choice(platforms_dist)
        grade = random.choice(grades_dist)
        nickname = random.choice(nicknames)
        industry = random.choice(industries)
        occupation = random.choice(occupations)

        # 关联到随机内容
        content = random.choice(created_contents) if created_contents else None
        account = random.choice(created_accounts) if created_accounts else None

        # 生成微信ID（60%概率有）
        wechat_id = f"wx_{nickname}_{random.randint(1000, 9999)}" if random.random() < 0.6 else None

        # 创建时间：最近30天内随机
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))

        # 根据分级设置意向度
        intention_map = {"A": "high", "B": "high", "C": "medium", "D": "low"}
        intention_level = intention_map.get(grade, "medium")

        lead = Lead(
            owner_id=owner_id,
            platform=platform,
            source="publish_task" if random.random() > 0.2 else "manual",
            title=f"{nickname}的咨询",
            post_url=content.post_url if content else None,
            wechat_adds=1 if wechat_id else 0,
            leads=1,
            valid_leads=1 if grade in ["A", "B"] else 0,
            conversions=1 if grade == "A" and random.random() < 0.5 else 0,
            status=random.choice(["new", "contacted", "qualified", "converted"]),
            intention_level=intention_level,
            note=f"来自{platform}的咨询，{industry}行业，{occupation}",
            publish_account_id=account.id if account else None,
            published_content_id=content.id if content else None,
            first_touch_time=created_at,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(lead)
        created_leads.append(lead)

    db.commit()
    for lead in created_leads:
        db.refresh(lead)
    print(f"[线索数据] 已创建 {len(created_leads)} 条线索")

    # ========== 4. 创建客户数据（15+条）==========
    customer_statuses = ["new", "contacted", "qualified", "converted", "lost"]
    status_weights = [0.2, 0.3, 0.2, 0.2, 0.1]  # 分布权重

    created_customers = []
    for i in range(15):
        # 关联到线索
        lead = created_leads[i] if i < len(created_leads) else None

        # 随机选择状态（按权重）
        status = random.choices(customer_statuses, weights=status_weights)[0]

        # 根据状态设置成交金额
        deal_value = None
        if status == "converted":
            deal_value = random.choice([5.0, 10.0, 15.0, 20.0, 30.0, 50.0])

        # 随机选择分级
        grade = random.choice(grades_dist)

        # 生成跟进记录（部分客户有）
        follow_records = []
        if random.random() < 0.7:  # 70%客户有跟进记录
            num_records = random.randint(1, 3)
            for r in range(num_records):
                follow_date = datetime.utcnow() - timedelta(days=random.randint(1, 20))
                follow_records.append(
                    {
                        "date": follow_date.isoformat(),
                        "content": random.choice(
                            [
                                "客户咨询贷款额度，已解答",
                                "了解客户资质情况，符合申请条件",
                                "发送产品资料给客户",
                                "客户有意愿，预约面谈",
                                "跟进还款计划，客户表示理解",
                                "解答利率问题，客户满意",
                            ]
                        ),
                        "owner": "demo",
                    }
                )

        customer = Customer(
            owner_id=owner_id,
            nickname=lead.title.replace("的咨询", "") if lead else random.choice(nicknames),
            wechat_id=f"wx_customer_{i:03d}" if random.random() < 0.8 else None,
            phone=f"138{random.randint(10000000, 99999999)}" if random.random() < 0.6 else None,
            source_platform=lead.platform if lead else random.choice(platforms_dist),
            source_content_id=lead.published_content_id if lead else None,
            lead_id=lead.id if lead else None,
            tags=[random.choice(["高意向", "急用钱", "优质客户", "待跟进", "已成交"])],
            intention_level=lead.intention_level if lead else random.choice(["low", "medium", "high"]),
            customer_status=status,
            inquiry_content=random.choice(
                [
                    "想了解一下个人信用贷款",
                    "咨询房贷相关问题",
                    "有经营贷需求，想了解一下",
                    "征信有点问题，能贷款吗？",
                    "需要资金周转，咨询贷款方案",
                ]
            ),
            follow_records=follow_records,
            qualification_score=grade,
            auto_score_reason=f"基于{random.choice(['互动行为', '资料完整度', '咨询深度'])}自动评分",
            company=random.choice(["某某科技", "某某贸易", "个体经营", None]),
            position=random.choice(occupations),
            industry=random.choice(industries),
            deal_value=deal_value,
            email=f"customer{i}@example.com" if random.random() < 0.3 else None,
            address=random.choice(["北京市朝阳区", "上海市浦东新区", "广州市天河区", None]),
            # 助贷业务字段
            loan_demand_type=random.choice(loan_types),
            expected_amount=float(random.randint(5, 100)),
            occupation=random.choice(occupations),
            social_security=random.choice(["有社保", "有公积金", "都有", "都无"]),
            debt_range=random.choice(["无负债", "5万以下", "5-20万", "20-50万"]),
            matchable_products=[random.choice(loan_types)],
            has_business_license=random.choice([True, False]),
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            updated_at=datetime.utcnow() - timedelta(days=random.randint(0, 10)),
        )
        db.add(customer)
        created_customers.append(customer)

    db.commit()
    for cust in created_customers:
        db.refresh(cust)
    print(f"[客户数据] 已创建 {len(created_customers)} 条客户")

    # ========== 5. 创建跟进记录 ==========
    created_follows = []
    for customer in created_customers:
        if customer.follow_records and len(customer.follow_records) > 0:
            for record in customer.follow_records:
                follow = FollowUpRecord(
                    lead_id=customer.lead_id,
                    customer_id=customer.id,
                    follow_by=owner_id,
                    follow_date=datetime.fromisoformat(record["date"]),
                    follow_type=random.choice(["phone", "wechat", "meeting"]),
                    content=record["content"],
                    outcome=random.choice(["有意向", "待跟进", "已成交", "无意向"]),
                    next_follow_at=(
                        datetime.utcnow() + timedelta(days=random.randint(1, 7)) if random.random() > 0.3 else None
                    ),
                    created_at=datetime.fromisoformat(record["date"]),
                )
                db.add(follow)
                created_follows.append(follow)

    db.commit()
    print(f"[跟进记录] 已创建 {len(created_follows)} 条跟进")

    print(f"[Dashboard演示数据] 生成完成！")
    return {
        "accounts": len(accounts_data),
        "contents": len(created_contents),
        "leads": len(created_leads),
        "customers": len(created_customers),
        "follow_ups": len(created_follows),
    }


def main():
    """主函数"""
    print("=" * 50)
    print("MVP 种子数据初始化")
    print("=" * 50)

    db = SessionLocal()
    try:
        seed_tags(db)
        seed_compliance_rules(db)
        seed_prompt_templates(db)
        seed_inbox_items(db)
        seed_platform_rules(db)
        seed_rewrite_templates(db)
        seed_dashboard_demo_data(db)  # 添加Dashboard演示数据
        print("=" * 50)
        print("种子数据初始化完成！")
        print("=" * 50)
    except Exception as e:
        print(f"错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
