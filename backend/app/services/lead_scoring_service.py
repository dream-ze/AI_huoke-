"""
线索分级服务 - 自动为线索评分并分级为 A/B/C/D

分级标准：
- A级：高意向 + 资质较好（公积金/社保/有房产）
- B级：有需求 + 需补充资料
- C级：弱意向 + 需养熟
- D级：高风险 + 不建议推进

评分维度（总分100）：
- 贷款需求明确度：30%
- 资质条件：30%
- 沟通意愿：20%
- 紧急程度：20%
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LeadScoringService:
    """线索自动评分分级服务"""

    # 分级阈值
    GRADE_THRESHOLDS = {
        "A": 75,  # >= 75 分
        "B": 50,  # >= 50 分
        "C": 25,  # >= 25 分
        "D": 0,  # < 25 分
    }

    def __init__(self, db: Session = None):
        """初始化服务

        Args:
            db: 数据库会话（可选，部分方法可接收 db 参数）
        """
        self.db = db

    def score_lead(self, db: Session, lead_id: int) -> dict:
        """对线索进行自动评分和分级。

        Args:
            db: 数据库会话
            lead_id: 线索ID

        Returns:
            {"score": int, "grade": str, "reason": str, "details": dict}
        """
        from app.models.crm import Customer, Lead, LeadProfile

        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.warning(f"线索 {lead_id} 不存在")
            return {"score": 0, "grade": "D", "reason": "线索不存在", "details": {}}

        # 获取线索画像
        profile = db.query(LeadProfile).filter(LeadProfile.lead_id == lead_id).first()

        # 四维评分
        need_score = self._score_need_clarity(lead, profile)
        qualification_score = self._score_qualification(lead, profile)
        willingness_score = self._score_willingness(lead)
        urgency_score = self._score_urgency(lead, profile)

        # 加权总分
        total_score = int(need_score * 0.3 + qualification_score * 0.3 + willingness_score * 0.2 + urgency_score * 0.2)

        # 确定等级
        grade = self._determine_grade(total_score)

        # 生成原因说明
        details = {
            "need_clarity": need_score,
            "qualification": qualification_score,
            "willingness": willingness_score,
            "urgency": urgency_score,
        }
        reason = self._generate_reason(grade, details)

        # 写入 Customer 表（如果关联了客户）
        customer = db.query(Customer).filter(Customer.lead_id == lead_id).first()
        if customer:
            customer.qualification_score = grade
            customer.auto_score_reason = reason
            db.commit()
            logger.info(f"线索 {lead_id} 评分完成: {grade}({total_score}分)")

        return {
            "score": total_score,
            "grade": grade,
            "reason": reason,
            "details": details,
        }

    def _score_need_clarity(self, lead, profile) -> int:
        """评估贷款需求明确度（0-100）

        评分依据：
        - 有明确贷款金额需求：+30分
        - 紧急程度高/中：+25/+15分
        - 意向等级高/中：+15/+8分
        """
        score = 30  # 基础分

        if profile:
            # 贷款金额需求（字符串类型，非空即有需求）
            if hasattr(profile, "loan_amount_need") and profile.loan_amount_need:
                score += 30  # 有明确金额需求

            # 紧急程度
            if hasattr(profile, "urgency_level") and profile.urgency_level:
                urgency = str(profile.urgency_level).lower()
                if urgency in ("high", "urgent"):
                    score += 25
                elif urgency == "medium":
                    score += 15
                else:
                    score += 5

        # 从lead的意向等级补充
        if hasattr(lead, "intention_level") and lead.intention_level:
            level = str(lead.intention_level).lower()
            if level in ("high", "a", "高"):
                score += 15
            elif level in ("medium", "b", "中"):
                score += 8

        return min(score, 100)

    def _score_qualification(self, lead, profile) -> int:
        """评估资质条件（0-100）

        评分依据：
        - 有房产：+25分
        - 有车：+15分
        - 有公积金：+20分
        - 征信良好/一般：+25/+10分，征信差：-10分
        """
        score = 20  # 基础分

        if profile:
            # 房产
            if hasattr(profile, "has_house") and profile.has_house:
                score += 25

            # 车辆
            if hasattr(profile, "has_car") and profile.has_car:
                score += 15

            # 公积金（重要资质指标）
            if hasattr(profile, "has_provident_fund") and profile.has_provident_fund:
                score += 20

            # 征信状态
            if hasattr(profile, "credit_status") and profile.credit_status:
                status = str(profile.credit_status).lower()
                if status in ("good", "良好", "优秀"):
                    score += 25
                elif status in ("normal", "一般", "fair"):
                    score += 10
                elif status in ("poor", "差", "不良"):
                    score -= 10  # 征信不好扣分

        return max(min(score, 100), 0)

    def _score_willingness(self, lead) -> int:
        """评估沟通意愿（0-100）

        评分依据：
        - 线索状态活跃/已联系：+35/+20分
        - 线索状态冷淡：-15分
        - 意向等级高/中：+25/+10分
        """
        score = 40  # 基础分（有线索记录说明有一定意愿）

        if hasattr(lead, "status") and lead.status:
            status = str(lead.status).lower()
            if status in ("active", "engaged", "活跃", "qualified"):
                score += 35
            elif status in ("contacted", "已联系"):
                score += 20
            elif status in ("cold", "冷淡", "lost"):
                score -= 15

        if hasattr(lead, "intention_level") and lead.intention_level:
            level = str(lead.intention_level).lower()
            if level in ("high", "a", "高"):
                score += 25
            elif level in ("medium", "b", "中"):
                score += 10

        return max(min(score, 100), 0)

    def _score_urgency(self, lead, profile) -> int:
        """评估紧急程度（0-100）

        评分依据：
        - 紧急程度高/中/低：+50/+25/+5分
        """
        score = 30  # 基础分

        if profile and hasattr(profile, "urgency_level") and profile.urgency_level:
            level = str(profile.urgency_level).lower()
            if level in ("urgent", "紧急", "high"):
                score += 50
            elif level in ("medium", "中等"):
                score += 25
            elif level in ("low", "低"):
                score += 5

        return min(score, 100)

    def _determine_grade(self, score: int) -> str:
        """根据总分确定等级

        Args:
            score: 总分（0-100）

        Returns:
            等级字符 A/B/C/D
        """
        if score >= self.GRADE_THRESHOLDS["A"]:
            return "A"
        elif score >= self.GRADE_THRESHOLDS["B"]:
            return "B"
        elif score >= self.GRADE_THRESHOLDS["C"]:
            return "C"
        else:
            return "D"

    def _generate_reason(self, grade: str, details: dict) -> str:
        """生成评分原因说明

        Args:
            grade: 等级
            details: 各维度评分详情

        Returns:
            评分原因字符串
        """
        reasons = {
            "A": "高意向客户，资质较好，建议优先跟进",
            "B": "有贷款需求，需补充资料确认资质，建议正常跟进",
            "C": "意向较弱，建议持续培育后再跟进",
            "D": "风险较高或意向极低，建议暂缓跟进",
        }
        base = reasons.get(grade, "未知等级")
        detail_str = (
            f"（需求{details['need_clarity']}分/资质{details['qualification']}分"
            f"/意愿{details['willingness']}分/紧急{details['urgency']}分）"
        )
        return base + detail_str

    def batch_score_leads(self, db: Session, lead_ids: List[int]) -> List[dict]:
        """批量评分

        Args:
            db: 数据库会话
            lead_ids: 线索ID列表

        Returns:
            评分结果列表
        """
        results = []
        for lead_id in lead_ids:
            try:
                result = self.score_lead(db, lead_id)
                result["lead_id"] = lead_id
                results.append(result)
            except Exception as e:
                logger.error(f"线索 {lead_id} 评分失败: {e}")
                results.append(
                    {
                        "lead_id": lead_id,
                        "score": 0,
                        "grade": "D",
                        "reason": f"评分异常: {str(e)}",
                        "details": {},
                    }
                )
        return results

    def override_grade(self, db: Session, lead_id: int, grade: str, reason: Optional[str] = None) -> dict:
        """手动覆盖线索分级

        Args:
            db: 数据库会话
            lead_id: 线索ID
            grade: 目标等级（A/B/C/D）
            reason: 覆盖原因

        Returns:
            操作结果
        """
        from app.models.crm import Customer

        if grade not in ("A", "B", "C", "D"):
            raise ValueError(f"无效等级: {grade}，必须为 A/B/C/D")

        customer = db.query(Customer).filter(Customer.lead_id == lead_id).first()
        if customer:
            customer.qualification_score = grade
            customer.auto_score_reason = reason or f"手动设置为{grade}级"
            db.commit()
            logger.info(f"线索 {lead_id} 手动设置为 {grade} 级")

        return {"lead_id": lead_id, "grade": grade, "reason": reason or f"手动设置为{grade}级"}

    def get_scoring_stats(self, db: Session) -> Dict[str, int]:
        """获取线索分级统计

        Args:
            db: 数据库会话

        Returns:
            各等级数量统计
        """
        from app.models.crm import Customer
        from sqlalchemy import func

        stats = (
            db.query(Customer.qualification_score, func.count(Customer.id))
            .filter(Customer.qualification_score.isnot(None))
            .group_by(Customer.qualification_score)
            .all()
        )

        result = {"A": 0, "B": 0, "C": 0, "D": 0, "ungraded": 0}
        for grade, count in stats:
            if grade in result:
                result[grade] = count

        # 统计未分级数量
        total_customers = db.query(Customer).count()
        graded_count = sum(result[g] for g in ["A", "B", "C", "D"])
        result["ungraded"] = total_customers - graded_count

        return result

    def get_leads_by_grade(self, db: Session, grade: str) -> List[int]:
        """获取指定等级的线索ID列表

        Args:
            db: 数据库会话
            grade: 等级（A/B/C/D）

        Returns:
            线索ID列表
        """
        from app.models.crm import Customer

        if grade not in ("A", "B", "C", "D"):
            raise ValueError(f"无效等级: {grade}")

        customers = db.query(Customer).filter(Customer.qualification_score == grade, Customer.lead_id.isnot(None)).all()

        return [c.lead_id for c in customers if c.lead_id]

    def suggest_follow_priority(self, db: Session, lead_id: int) -> dict:
        """建议跟进优先级

        根据评分结果，给出跟进建议

        Args:
            db: 数据库会话
            lead_id: 线索ID

        Returns:
            跟进建议信息
        """
        score_result = self.score_lead(db, lead_id)
        grade = score_result["grade"]
        details = score_result["details"]

        suggestions = {
            "A": {
                "priority": "高",
                "action": "立即跟进",
                "tips": "客户意向强、资质好，建议24小时内联系，重点推荐适合产品",
                "expected_conversion": "高",
            },
            "B": {
                "priority": "中",
                "action": "正常跟进",
                "tips": "客户有需求但资质待确认，建议补充资料后推荐合适方案",
                "expected_conversion": "中",
            },
            "C": {
                "priority": "低",
                "action": "培育跟进",
                "tips": "客户意向较弱，建议定期触达、内容培育，等待时机",
                "expected_conversion": "低",
            },
            "D": {
                "priority": "暂缓",
                "action": "暂不跟进",
                "tips": "客户风险较高或无意向，建议先排除或转交给风控评估",
                "expected_conversion": "极低",
            },
        }

        suggestion = suggestions.get(grade, suggestions["D"])

        return {
            "lead_id": lead_id,
            "grade": grade,
            "score": score_result["score"],
            "priority": suggestion["priority"],
            "action": suggestion["action"],
            "tips": suggestion["tips"],
            "expected_conversion": suggestion["expected_conversion"],
            "score_details": details,
            "reason": score_result["reason"],
        }
