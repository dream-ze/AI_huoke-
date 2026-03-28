"""MVP 标签服务 - 基于规则的标签识别"""
from sqlalchemy.orm import Session
from app.models.models import MvpTag, MvpMaterialTagRel, MvpMaterialItem

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
                    tag = self.db.query(MvpTag).filter(
                        MvpTag.name == name, 
                        MvpTag.type == tag_type
                    ).first()
                    if not tag:
                        tag = MvpTag(name=name, type=tag_type)
                        self.db.add(tag)
                        self.db.flush()
                    # 添加关联（避免重复）
                    exists = self.db.query(MvpMaterialTagRel).filter_by(
                        material_id=material_id, 
                        tag_id=tag.id
                    ).first()
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
            existing = self.db.query(MvpTag).filter(
                MvpTag.name == name, 
                MvpTag.type == tag_type
            ).first()
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
            self.db.query(MvpMaterialTagRel).filter(
                MvpMaterialTagRel.material_id == material_id
            ).delete()
            for tid in tag_ids:
                self.db.add(MvpMaterialTagRel(material_id=material_id, tag_id=tid))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"更新标签失败: {str(e)}")

    def get_material_tags(self, material_id: int) -> list:
        """获取素材的所有标签"""
        try:
            tags = self.db.query(MvpTag).join(MvpMaterialTagRel).filter(
                MvpMaterialTagRel.material_id == material_id
            ).all()
            return [{"id": t.id, "name": t.name, "type": t.type} for t in tags]
        except Exception:
            return []

    def get_tag_stats(self) -> dict:
        """获取标签统计"""
        try:
            from sqlalchemy import func
            stats = self.db.query(
                MvpTag.type,
                func.count(MvpTag.id).label("count")
            ).group_by(MvpTag.type).all()
            return {s.type: s.count for s in stats}
        except Exception:
            return {}
