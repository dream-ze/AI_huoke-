"""MVP种子数据 - 运行方式: cd backend && python seed_mvp_data.py"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.models import (
    MvpTag,
    MvpComplianceRule,
    MvpPromptTemplate,
    MvpInboxItem,
)


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
    ]

    created = 0
    for tag_data in tags_data:
        existing = db.query(MvpTag).filter(
            MvpTag.name == tag_data["name"],
            MvpTag.type == tag_data["type"]
        ).first()
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
        {"rule_type": "keyword", "keyword": "黑户可贷", "risk_level": "high", "suggestion": "删除该词，不得针对征信黑户宣传"},
        {"rule_type": "keyword", "keyword": "无视征信", "risk_level": "high", "suggestion": "删除该词，不得忽视征信审核"},
        {"rule_type": "keyword", "keyword": "100%通过", "risk_level": "high", "suggestion": "删除该词，不得承诺通过率"},
        {"rule_type": "keyword", "keyword": "秒放款", "risk_level": "high", "suggestion": "删除该词，使用'放款快'替代"},
        {"rule_type": "keyword", "keyword": "不看征信", "risk_level": "high", "suggestion": "删除该词，所有正规贷款都需审核征信"},
        {"rule_type": "keyword", "keyword": "白户秒批", "risk_level": "high", "suggestion": "删除该词，白户同样需要正常审批"},
        {"rule_type": "keyword", "keyword": "征信花也能下", "risk_level": "high", "suggestion": "删除该词，不得承诺征信不良可贷"},
        # medium 级别 - 谨慎使用
        {"rule_type": "keyword", "keyword": "低门槛", "risk_level": "medium", "suggestion": "建议改为'申请便捷'或说明具体条件"},
        {"rule_type": "keyword", "keyword": "快速放款", "risk_level": "medium", "suggestion": "建议说明具体时间范围，如'1-3个工作日'"},
        {"rule_type": "keyword", "keyword": "零利息", "risk_level": "medium", "suggestion": "需注明适用期限和条件，避免误导"},
        {"rule_type": "keyword", "keyword": "免息", "risk_level": "medium", "suggestion": "需注明免息期限和后续利率"},
        {"rule_type": "keyword", "keyword": "不上征信", "risk_level": "medium", "suggestion": "需核实产品实际情况，正规产品一般上征信"},
        {"rule_type": "keyword", "keyword": "随借随还", "risk_level": "medium", "suggestion": "需注明是否有提前还款手续费"},
        {"rule_type": "keyword", "keyword": "超低利率", "risk_level": "medium", "suggestion": "需注明具体年化利率数字"},
        {"rule_type": "keyword", "keyword": "门槛低", "risk_level": "medium", "suggestion": "建议说明具体申请条件"},
        {"rule_type": "keyword", "keyword": "无抵押", "risk_level": "medium", "suggestion": "建议说明信用贷款的具体要求"},
        {"rule_type": "keyword", "keyword": "无担保", "risk_level": "medium", "suggestion": "建议说明信用贷款的审核标准"},
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
        existing = db.query(MvpComplianceRule).filter(
            MvpComplianceRule.keyword == rule_data["keyword"]
        ).first()
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
        existing = db.query(MvpPromptTemplate).filter(
            MvpPromptTemplate.platform == tmpl_data["platform"],
            MvpPromptTemplate.audience == tmpl_data["audience"],
            MvpPromptTemplate.style == tmpl_data["style"],
        ).first()
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
        existing = db.query(MvpInboxItem).filter(
            MvpInboxItem.title == item_data["title"]
        ).first()
        if not existing:
            db.add(MvpInboxItem(**item_data))
            created += 1

    db.commit()
    print(f"[收件箱示例] 已创建 {created} 条，跳过 {len(inbox_data) - created} 条已存在")


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
