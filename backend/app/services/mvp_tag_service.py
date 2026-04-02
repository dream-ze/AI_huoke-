"""MVP 标签服务 - 基于规则的标签识别"""

from typing import Dict, List, Optional

from app.models.mvp import TAG_TYPE_DIMENSIONS, TAG_TYPE_LOAN_DIMENSIONS, MvpMaterialItem, MvpMaterialTagRel, MvpTag
from sqlalchemy import func
from sqlalchemy.orm import Session

# 标签识别规则
TAG_RULES = {
    "audience": [
        (["负债", "征信", "逾期", "催收", "还款"], "负债人群"),
        (["工资", "上班", "打卡", "月薪", "职场"], "上班族"),
        (["老板", "经营", "流水", "生意", "创业"], "个体户/老板"),
        (["大学", "学生", "毕业", "校园"], "大学生"),
        (["宝妈", "孩子", "育儿", "家庭"], "宝妈群体"),
        (["中年", "40岁", "50岁", "养老"], "中年人群"),
    ],
    "content_type": [
        (["怎么", "如何", "步骤", "方法", "教程"], "干货型"),
        (["真实经历", "我当时", "亲身经历", "分享一下"], "故事型"),
        (["对比", "测评", "评测", "哪个好"], "测评型"),
        (["问", "答", "是不是", "能不能"], "问答型"),
        (["清单", "盘点", "汇总", "合集"], "清单型"),
    ],
    "style": [
        (["避坑", "注意", "千万别", "小心", "踩雷"], "避坑型"),
        (["推荐", "种草", "安利", "真香"], "种草型"),
        (["专业", "分析", "深度", "报告"], "专业型"),
        (["哈哈", "笑死", "绝了", "太真实"], "口语型"),
    ],
    "scenario": [
        (["急需", "急用钱", "救急", "马上要"], "急需用钱"),
        (["以贷养贷", "拆东墙", "循环"], "以贷养贷"),
        (["第一次", "首次", "新手", "小白"], "首次贷款"),
        (["经营", "周转", "进货", "资金链"], "经营周转"),
        (["消费", "分期", "购物", "旅游"], "消费分期"),
    ],
}

# ============================================================
# 助贷业务专用标签识别规则
# ============================================================
LOAN_TAG_RULES = {
    # 产品类型: 识别贷款产品类型
    "product_type": [
        (["信用贷", "信贷", "无抵押", "纯信用", "凭身份证", "不用抵押"], "信贷"),
        (["抵押贷", "房产抵押", "房屋抵押", "绿本贷", "车抵贷", "按揭房"], "抵押贷"),
        (["企业贷", "公司贷", "企业信用贷", "经营性贷款"], "企业贷"),
        (["经营贷", "经营性", "个体户贷", "商户贷", "流水贷"], "经营贷"),
        (["消费贷", "消费金融", "消费分期", "购物分期", "装修贷", "旅游贷"], "消费贷"),
    ],
    # 用户资质: 识别用户具备的资质条件
    "user_qualification": [
        (["公积金", "公积金缴存", "公积金贷款", "公积金余额"], "公积金"),
        (["社保", "社保缴纳", "社保记录", "连续社保"], "社保"),
        (["个体户", "个体工商户", "营业执照", "小店主"], "个体户"),
        (["企业主", "公司老板", "法人", "股东", "开公司"], "企业主"),
        (["征信花", "查询多", "大数据花", "多次查询", "征信查询"], "征信花"),
        (["负债高", "负债多", "负债率", "债务多", "欠款多"], "负债高"),
    ],
    # 内容意图: 识别内容的意图倾向
    "content_intent": [
        (["科普", "知识", "介绍", "什么是", "了解", "讲解", "干货"], "科普"),
        (["避坑", "注意", "千万别", "小心", "踩雷", "套路", "被骗"], "避坑"),
        (["案例", "真实经历", "亲身经历", "分享", "故事", "经历"], "案例"),
        (["引流", "私信", "咨询", "联系", "加V", "加微"], "引流"),
        (["转化", "办理", "申请", "找我", "专业办理", "快速下款"], "转化"),
    ],
    # 平台风格: 识别内容在平台上的呈现风格
    "platform_style": [
        (["口播", "视频", "真人出镜", "讲解视频"], "口播"),
        (["图文", "图片", "笔记", "图文并茂"], "图文"),
        (["问答", "提问", "回答", "Q&A", "答疑"], "问答"),
        (["经验帖", "经验分享", "心得", "总结", "攻略"], "经验帖"),
    ],
    # 风险等级: 基于内容判断风险
    "risk_level": [
        (["合规", "正规", "银行", "官方", "安全"], "低风险"),
        (["注意", "谨慎", "风险", "适度"], "中风险"),
        (["套现", "洗白", "黑户秒过", "包装资料", "无视征信"], "高风险"),
    ],
    # 转化倾向: 判断内容的转化意图强度
    "conversion_tendency": [
        (["找我", "私信我", "加我", "咨询我", "专业办理", "快速办理"], "强转化"),
        (["建议", "可以了解", "参考", "对比"], "弱转化"),
        (["品牌", "口碑", "信誉", "专业", "服务"], "品牌向"),
    ],
}


class MvpTagService:
    def __init__(self, db: Session):
        self.db = db

    def identify_tags(self, text: str) -> dict:
        """基于规则识别文本标签，返回 {type: [tag_name, ...]}"""
        if not text:
            return {}
        result = {}
        text_lower = text.lower()
        for tag_type, rules in TAG_RULES.items():
            matched = []
            for keywords, tag_name in rules:
                if any(kw in text_lower for kw in keywords):
                    matched.append(tag_name)
            if matched:
                result[tag_type] = matched
        return result

    def auto_tag_material(self, material_id: int, text: str):
        """自动为素材识别并关联标签"""
        try:
            identified = self.identify_tags(text)
            for tag_type, tag_names in identified.items():
                for name in tag_names:
                    # 查找或创建标签
                    tag = self.db.query(MvpTag).filter(MvpTag.name == name, MvpTag.type == tag_type).first()
                    if not tag:
                        tag = MvpTag(name=name, type=tag_type)
                        self.db.add(tag)
                        self.db.flush()
                    # 添加关联（避免重复）
                    exists = self.db.query(MvpMaterialTagRel).filter_by(material_id=material_id, tag_id=tag.id).first()
                    if not exists:
                        self.db.add(MvpMaterialTagRel(material_id=material_id, tag_id=tag.id))
            self.db.flush()
        except Exception:
            pass  # 标签识别失败不影响主流程

    def list_tags(self, tag_type=None):
        """列出所有标签"""
        try:
            q = self.db.query(MvpTag)
            if tag_type:
                q = q.filter(MvpTag.type == tag_type)
            return q.order_by(MvpTag.type, MvpTag.name).all()
        except Exception:
            return []

    def create_tag(self, name: str, tag_type: str):
        """创建标签"""
        try:
            existing = self.db.query(MvpTag).filter(MvpTag.name == name, MvpTag.type == tag_type).first()
            if existing:
                return existing
            tag = MvpTag(name=name, type=tag_type)
            self.db.add(tag)
            self.db.commit()
            return tag
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"创建标签失败: {str(e)}")

    def update_material_tags(self, material_id: int, tag_ids: list):
        """更新素材的标签关联"""
        try:
            self.db.query(MvpMaterialTagRel).filter(MvpMaterialTagRel.material_id == material_id).delete()
            for tid in tag_ids:
                self.db.add(MvpMaterialTagRel(material_id=material_id, tag_id=tid))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"更新标签失败: {str(e)}")

    def get_material_tags(self, material_id: int) -> list:
        """获取素材的所有标签"""
        try:
            tags = (
                self.db.query(MvpTag).join(MvpMaterialTagRel).filter(MvpMaterialTagRel.material_id == material_id).all()
            )
            return [{"id": t.id, "name": t.name, "type": t.type} for t in tags]
        except Exception:
            return []

    def get_tag_stats(self) -> dict:
        """获取标签统计"""
        try:
            stats = self.db.query(MvpTag.type, func.count(MvpTag.id).label("count")).group_by(MvpTag.type).all()
            return {s.type: s.count for s in stats}
        except Exception:
            return {}

    # ============================================================
    # 助贷业务专用方法
    # ============================================================

    def get_tags_by_dimension(self, dimension: str) -> List[Dict]:
        """按维度批量查询标签

        Args:
            dimension: 标签维度，如 'product_type', 'user_qualification' 等

        Returns:
            该维度下的所有标签列表，格式为 [{"id": 1, "name": "信贷", "type": "product_type"}, ...]
        """
        try:
            tags = self.db.query(MvpTag).filter(MvpTag.type == dimension).order_by(MvpTag.name).all()
            return [{"id": t.id, "name": t.name, "type": t.type} for t in tags]
        except Exception:
            return []

    @staticmethod
    def get_all_dimensions() -> List[str]:
        """获取所有标签维度列表

        Returns:
            所有支持的标签维度列表
        """
        return TAG_TYPE_DIMENSIONS.copy()

    @staticmethod
    def get_loan_dimensions() -> List[str]:
        """获取助贷业务专用标签维度列表

        Returns:
            助贷业务专用的标签维度列表
        """
        return TAG_TYPE_LOAN_DIMENSIONS.copy()

    def get_tags_grouped_by_dimension(self, dimensions: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """按维度分组返回所有标签

        Args:
            dimensions: 可选，指定要查询的维度列表。默认查询所有维度

        Returns:
            按维度分组的标签字典，格式为 {"product_type": [...], "user_qualification": [...], ...}
        """
        try:
            query_dimensions = dimensions or TAG_TYPE_DIMENSIONS
            result = {}

            # 一次性查询所有标签，然后在内存中分组
            tags = (
                self.db.query(MvpTag).filter(MvpTag.type.in_(query_dimensions)).order_by(MvpTag.type, MvpTag.name).all()
            )

            for tag in tags:
                if tag.type not in result:
                    result[tag.type] = []
                result[tag.type].append({"id": tag.id, "name": tag.name, "type": tag.type})

            # 确保所有查询的维度都有返回（即使为空）
            for dim in query_dimensions:
                if dim not in result:
                    result[dim] = []

            return result
        except Exception:
            return {}

    def identify_loan_tags(self, text: str) -> Dict[str, List[str]]:
        """基于规则识别助贷业务标签

        Args:
            text: 待识别的文本内容

        Returns:
            识别结果字典，格式为 {"product_type": ["信贷", "抵押贷"], "user_qualification": ["公积金"], ...}
        """
        if not text:
            return {}
        result = {}
        text_lower = text.lower()
        for tag_type, rules in LOAN_TAG_RULES.items():
            matched = []
            for keywords, tag_name in rules:
                if any(kw in text_lower for kw in keywords):
                    matched.append(tag_name)
            if matched:
                # 去重
                result[tag_type] = list(set(matched))
        return result

    def auto_tag_for_loan_content(self, content_text: str, platform: Optional[str] = None) -> Dict[str, List[str]]:
        """自动为助贷内容打标签（基于关键词匹配）

        综合使用基础规则和助贷专用规则进行标签识别。

        Args:
            content_text: 待识别的内容文本
            platform: 可选，平台标识（如 'xiaohongshu', 'douyin'）

        Returns:
            识别结果字典，包含所有匹配的标签
        """
        if not content_text:
            return {}

        result = {}

        # 1. 应用基础标签规则
        base_tags = self.identify_tags(content_text)
        result.update(base_tags)

        # 2. 应用助贷专用标签规则
        loan_tags = self.identify_loan_tags(content_text)
        for tag_type, tag_names in loan_tags.items():
            if tag_type in result:
                # 合并并去重
                result[tag_type] = list(set(result[tag_type] + tag_names))
            else:
                result[tag_type] = tag_names

        # 3. 如果指定了平台，添加平台标签
        if platform:
            platform_map = {
                "xiaohongshu": "小红书",
                "douyin": "抖音",
                "zhihu": "知乎",
                "weixin": "微信",
            }
            platform_name = platform_map.get(platform, platform)
            result["platform"] = [platform_name]

        return result
