"""
线索业务服务层 - LeadService

提供线索的完整生命周期管理，包括：
- 创建线索并自动评分分级
- 状态流转管理
- 线索分派
- 线索转客户
- 漏斗统计
- 按分级查询
- 批量导入
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.models.crm import Customer, Lead, LeadProfile
from app.models.models import PublishTask, User
from app.schemas.schemas import LeadConvertCustomerRequest, LeadCreate, LeadResponse
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LeadService:
    """线索业务服务类"""

    # ABCD 分级阈值（基于四维评分总分）
    GRADE_THRESHOLDS = {
        "A": 75,  # 高意向 + 资质较好
        "B": 50,  # 有需求 + 需补充资料
        "C": 25,  # 弱意向 + 需养熟
        "D": 0,  # 高风险 + 不建议推进
    }

    def __init__(self, db: Session):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    # ==================== 核心业务方法 ====================

    def create_lead(
        self,
        db: Session,
        data: LeadCreate,
        owner_id: int,
    ) -> dict:
        """创建线索，自动触发评分和分级

        Args:
            db: 数据库会话
            data: 线索创建数据
            owner_id: 所有者ID

        Returns:
            线索响应字典（包含 customer_id）
        """
        # 创建线索实体
        lead = Lead(owner_id=owner_id, **data.model_dump())
        db.add(lead)
        db.flush()  # 获取 lead.id

        logger.info(f"创建线索: id={lead.id}, owner_id={owner_id}, platform={data.platform}")

        # 自动评分分级
        score_result = self.auto_score(db, lead.id)
        logger.info(f"线索 {lead.id} 自动分级: {score_result['grade']} ({score_result['score']}分)")

        db.commit()
        db.refresh(lead)

        return self._lead_to_response(db, lead)

    def update_status(
        self,
        db: Session,
        lead_id: int,
        new_status: str,
        owner_id: int,
    ) -> dict:
        """更新线索状态

        Args:
            db: 数据库会话
            lead_id: 线索ID
            new_status: 新状态
            owner_id: 所有者ID（用于权限校验）

        Returns:
            更新后的线索响应字典
        """
        lead = self._get_lead_and_check_owner(db, lead_id, owner_id)

        old_status = lead.status
        setattr(lead, "status", new_status)
        db.commit()
        db.refresh(lead)

        logger.info(f"线索 {lead_id} 状态变更: {old_status} -> {new_status}")

        return self._lead_to_response(db, lead)

    def auto_score(self, db: Session, lead_id: int) -> dict:
        """基于 lead_profiles 资质字段自动评分，返回 ABCD 分级

        分级标准：
        - A级（高意向+资质好）：has_house=True 或 credit_status='良好'，且 urgency_level='高'
        - B级（有需求+需补资料）：有明确 loan_amount_need，但资质信息不完整
        - C级（弱意向+需养熟）：基础信息有但意向不明确
        - D级（高风险+不推进）：credit_status='差' 或 debt_range 过高

        Args:
            db: 数据库会话
            lead_id: 线索ID

        Returns:
            {"score": int, "grade": str, "reason": str, "details": dict}
        """
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
        grade = self._determine_grade(total_score, profile)

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
            db.flush()

        logger.info(f"线索 {lead_id} 评分完成: {grade}({total_score}分)")

        return {
            "score": total_score,
            "grade": grade,
            "reason": reason,
            "details": details,
        }

    def assign_lead(
        self,
        db: Session,
        lead_id: int,
        assignee_id: int,
        current_user_id: int,
    ) -> dict:
        """分派线索给销售

        Args:
            db: 数据库会话
            lead_id: 线索ID
            assignee_id: 被分派人ID
            current_user_id: 当前用户ID（用于权限校验）

        Returns:
            更新后的线索响应字典
        """
        lead = self._get_lead_and_check_owner(db, lead_id, current_user_id)

        # 验证被分派人存在
        assignee = db.query(User).filter(User.id == assignee_id).first()
        if not assignee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee user not found")

        old_owner_id = lead.owner_id
        setattr(lead, "owner_id", assignee_id)
        db.commit()
        db.refresh(lead)

        logger.info(f"线索 {lead_id} 分派: owner {old_owner_id} -> {assignee_id}")

        return self._lead_to_response(db, lead)

    def convert_to_customer(
        self,
        db: Session,
        lead_id: int,
        payload: LeadConvertCustomerRequest,
        owner_id: int,
    ) -> Customer:
        """线索转客户

        Args:
            db: 数据库会话
            lead_id: 线索ID
            payload: 转客户请求数据
            owner_id: 所有者ID（用于权限校验）

        Returns:
            新创建的 Customer 对象
        """
        lead = self._get_lead_and_check_owner(db, lead_id, owner_id)

        # 检查是否已转换
        existing = db.query(Customer).filter(Customer.lead_id == lead.id).first()
        if existing:
            logger.info(f"线索 {lead_id} 已转换为客户 {existing.id}")
            return existing

        # 创建客户
        customer = Customer(
            owner_id=lead.owner_id,
            nickname=payload.nickname or f"线索#{lead.id}",
            wechat_id=payload.wechat_id,
            phone=payload.phone,
            source_platform=lead.platform,
            source_content_id=None,
            lead_id=lead.id,
            tags=payload.tags or ["线索转客户"],
            intention_level=payload.intention_level or lead.intention_level,
            inquiry_content=payload.inquiry_content or lead.note,
            customer_status="new",
        )
        db.add(customer)

        # 更新线索状态为 converted
        setattr(lead, "status", "converted")

        db.commit()
        db.refresh(customer)

        logger.info(f"线索 {lead_id} 转换为客户 {customer.id}")

        return customer

    def get_lead_funnel_stats(
        self,
        db: Session,
        owner_id: int,
        days: int = 30,
    ) -> dict:
        """获取线索漏斗统计

        Args:
            db: 数据库会话
            owner_id: 所有者ID
            days: 统计天数

        Returns:
            漏斗统计数据
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # published: PublishTask 表的总数
        published_count = (
            db.query(func.count(PublishTask.id))
            .filter(PublishTask.owner_id == owner_id)
            .filter(PublishTask.created_at >= start_date)
            .scalar()
            or 0
        )

        # leads_generated: Lead 表总数
        leads_generated_count = (
            db.query(func.count(Lead.id))
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_date)
            .scalar()
            or 0
        )

        # contacted: status 为 contacted 及之后状态
        contacted_statuses = ["contacted", "qualified", "converted"]
        contacted_count = (
            db.query(func.count(Lead.id))
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_date)
            .filter(Lead.status.in_(contacted_statuses))
            .scalar()
            or 0
        )

        # qualified: status 为 qualified 及之后状态
        qualified_statuses = ["qualified", "converted"]
        qualified_count = (
            db.query(func.count(Lead.id))
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_date)
            .filter(Lead.status.in_(qualified_statuses))
            .scalar()
            or 0
        )

        # converted: status 为 converted
        converted_count = (
            db.query(func.count(Lead.id))
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_date)
            .filter(Lead.status == "converted")
            .scalar()
            or 0
        )

        # 计算转化率
        stages = [
            {
                "stage": "published",
                "stage_label": "发布内容",
                "count": published_count,
                "rate": 1.0,
            },
            {
                "stage": "leads_generated",
                "stage_label": "产生线索",
                "count": leads_generated_count,
                "rate": round(leads_generated_count / published_count, 4) if published_count > 0 else 0,
            },
            {
                "stage": "contacted",
                "stage_label": "已联系",
                "count": contacted_count,
                "rate": round(contacted_count / published_count, 4) if published_count > 0 else 0,
            },
            {
                "stage": "qualified",
                "stage_label": "已认定",
                "count": qualified_count,
                "rate": round(qualified_count / published_count, 4) if published_count > 0 else 0,
            },
            {
                "stage": "converted",
                "stage_label": "已转化",
                "count": converted_count,
                "rate": round(converted_count / published_count, 4) if published_count > 0 else 0,
            },
        ]

        return {
            "stages": stages,
            "period_days": days,
        }

    def get_leads_by_grade(
        self,
        db: Session,
        owner_id: int,
        grade: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """按分级查询线索

        Args:
            db: 数据库会话
            owner_id: 所有者ID
            grade: 分级（A/B/C/D）
            skip: 分页偏移
            limit: 分页限制

        Returns:
            线索响应列表
        """
        if grade not in ("A", "B", "C", "D"):
            raise ValueError(f"无效等级: {grade}，必须为 A/B/C/D")

        # 通过 Customer 表的 qualification_score 关联查询
        leads = (
            db.query(Lead)
            .join(Customer, Customer.lead_id == Lead.id)
            .filter(Lead.owner_id == owner_id)
            .filter(Customer.qualification_score == grade)
            .order_by(Lead.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        result = []
        for lead in leads:
            customer = db.query(Customer).filter(Customer.lead_id == lead.id).first()
            payload = LeadResponse.model_validate(lead).model_dump()
            payload["customer_id"] = customer.id if customer else None
            result.append(payload)

        return result

    def batch_import_leads(
        self,
        db: Session,
        leads_data: List[LeadCreate],
        owner_id: int,
    ) -> dict:
        """批量导入线索

        Args:
            db: 数据库会话
            leads_data: 线索数据列表
            owner_id: 所有者ID

        Returns:
            导入结果统计
        """
        success_count = 0
        failed_count = 0
        created_ids = []

        for data in leads_data:
            try:
                lead = Lead(owner_id=owner_id, **data.model_dump())
                db.add(lead)
                db.flush()

                # 自动评分
                self.auto_score(db, lead.id)

                created_ids.append(lead.id)
                success_count += 1
            except Exception as e:
                logger.error(f"批量导入线索失败: {e}")
                failed_count += 1

        db.commit()

        logger.info(f"批量导入线索完成: 成功 {success_count}, 失败 {failed_count}")

        return {
            "total": len(leads_data),
            "success": success_count,
            "failed": failed_count,
            "created_ids": created_ids,
        }

    # ==================== 统计查询方法 ====================

    def get_attribution_stats(
        self,
        db: Session,
        owner_id: int,
        days: int = 30,
    ) -> dict:
        """线索来源归因分析

        Args:
            db: 数据库会话
            owner_id: 所有者ID
            days: 统计天数

        Returns:
            归因统计数据
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # 按平台分组统计
        platform_stats = (
            db.query(
                Lead.platform,
                func.count(Lead.id).label("lead_count"),
                func.sum(Lead.valid_leads).label("valid_count"),
                func.sum(Lead.conversions).label("conversion_count"),
            )
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_date)
            .group_by(Lead.platform)
            .all()
        )

        by_platform = []
        for row in platform_stats:
            lead_count = row.lead_count or 0
            conversion_count = row.conversion_count or 0
            conversion_rate = (conversion_count / lead_count) if lead_count > 0 else 0
            by_platform.append(
                {
                    "platform": row.platform,
                    "lead_count": lead_count,
                    "valid_count": row.valid_count or 0,
                    "conversion_count": conversion_count,
                    "conversion_rate": round(conversion_rate, 4),
                }
            )

        # 按来源分组统计
        source_stats = (
            db.query(
                Lead.source,
                func.count(Lead.id).label("lead_count"),
                func.sum(Lead.valid_leads).label("valid_count"),
                func.sum(Lead.conversions).label("conversion_count"),
            )
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_date)
            .group_by(Lead.source)
            .all()
        )

        by_source = []
        for row in source_stats:
            lead_count = row.lead_count or 0
            conversion_count = row.conversion_count or 0
            conversion_rate = (conversion_count / lead_count) if lead_count > 0 else 0
            by_source.append(
                {
                    "source": row.source,
                    "lead_count": lead_count,
                    "valid_count": row.valid_count or 0,
                    "conversion_count": conversion_count,
                    "conversion_rate": round(conversion_rate, 4),
                }
            )

        # 最佳引流内容
        top_content_query = (
            db.query(
                Lead.title,
                Lead.platform,
                Lead.publish_task_id,
                PublishTask.task_title,
                func.count(Lead.id).label("lead_count"),
                func.sum(Lead.conversions).label("conversions"),
            )
            .outerjoin(PublishTask, Lead.publish_task_id == PublishTask.id)
            .filter(Lead.owner_id == owner_id)
            .filter(Lead.created_at >= start_date)
            .group_by(Lead.title, Lead.platform, Lead.publish_task_id, PublishTask.task_title)
            .order_by(func.count(Lead.id).desc())
            .limit(10)
            .all()
        )

        top_content = []
        for row in top_content_query:
            top_content.append(
                {
                    "title": row.task_title or row.title,
                    "platform": row.platform,
                    "lead_count": row.lead_count or 0,
                    "conversions": row.conversions or 0,
                }
            )

        return {
            "by_platform": by_platform,
            "by_source": by_source,
            "top_content": top_content,
            "period_days": days,
        }

    def list_leads(
        self,
        db: Session,
        owner_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """查询线索列表

        Args:
            db: 数据库会话
            owner_id: 所有者ID
            status: 状态过滤
            skip: 分页偏移
            limit: 分页限制

        Returns:
            线索响应列表
        """
        query = db.query(Lead).filter(Lead.owner_id == owner_id)

        if status and status != "all":
            query = query.filter(Lead.status == status)

        leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()

        if not leads:
            return []

        # 批量查询关联的 customer
        lead_ids = [item.id for item in leads]
        customer_rows = db.query(Customer.id, Customer.lead_id).filter(Customer.lead_id.in_(lead_ids)).all()
        customer_map = {lead_id: customer_id for customer_id, lead_id in customer_rows if lead_id is not None}

        result = []
        for item in leads:
            payload = LeadResponse.model_validate(item).model_dump()
            payload["customer_id"] = customer_map.get(item.id)
            result.append(payload)

        return result

    def get_lead_trace(
        self,
        db: Session,
        lead_id: int,
        owner_id: int,
    ) -> dict:
        """获取线索追溯信息

        Args:
            db: 数据库会话
            lead_id: 线索ID
            owner_id: 所有者ID（用于权限校验）

        Returns:
            线索追溯响应（包含 publish_record_id）
        """
        lead = self._get_lead_and_check_owner(db, lead_id, owner_id)

        customer = db.query(Customer).filter(Customer.lead_id == lead.id).first()
        publish_record_id = None
        publish_task_id = getattr(lead, "publish_task_id", None)

        if publish_task_id is not None:
            task = db.query(PublishTask).filter(PublishTask.id == publish_task_id).first()
            publish_record_id = task.publish_record_id if task else None

        return self._lead_to_response(db, lead, publish_record_id=publish_record_id)

    # ==================== 私有辅助方法 ====================

    def _get_lead_and_check_owner(
        self,
        db: Session,
        lead_id: int,
        owner_id: int,
    ) -> Lead:
        """获取线索并校验所有者权限

        Args:
            db: 数据库会话
            lead_id: 线索ID
            owner_id: 所有者ID

        Returns:
            Lead 对象

        Raises:
            HTTPException: 线索不存在或无权限
        """
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        if lead.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this lead")
        return lead

    def _lead_to_response(
        self,
        db: Session,
        lead: Lead,
        publish_record_id: Optional[int] = None,
    ) -> dict:
        """将 Lead 对象转换为响应字典

        Args:
            db: 数据库会话
            lead: Lead 对象
            publish_record_id: 发布记录ID（可选）

        Returns:
            响应字典
        """
        customer = db.query(Customer).filter(Customer.lead_id == lead.id).first()
        payload = LeadResponse.model_validate(lead).model_dump()
        payload["customer_id"] = customer.id if customer else None

        if publish_record_id is not None:
            payload["publish_record_id"] = publish_record_id

        return payload

    # ==================== 评分相关私有方法 ====================

    def _score_need_clarity(self, lead: Lead, profile: Optional[LeadProfile]) -> int:
        """评估贷款需求明确度（0-100）"""
        score = 30  # 基础分

        if profile:
            if profile.loan_amount_need:
                score += 30  # 有明确金额需求

            if profile.urgency_level:
                urgency = str(profile.urgency_level).lower()
                if urgency in ("high", "urgent", "高"):
                    score += 25
                elif urgency in ("medium", "中"):
                    score += 15
                else:
                    score += 5

        if lead.intention_level:
            level = str(lead.intention_level).lower()
            if level in ("high", "a", "高"):
                score += 15
            elif level in ("medium", "b", "中"):
                score += 8

        return min(score, 100)

    def _score_qualification(self, lead: Lead, profile: Optional[LeadProfile]) -> int:
        """评估资质条件（0-100）"""
        score = 20  # 基础分

        if profile:
            if profile.has_house:
                score += 25

            if profile.has_car:
                score += 15

            if profile.has_provident_fund:
                score += 20

            if profile.credit_status:
                status_val = str(profile.credit_status).lower()
                if status_val in ("good", "良好", "优秀"):
                    score += 25
                elif status_val in ("normal", "一般", "fair"):
                    score += 10
                elif status_val in ("poor", "差", "不良"):
                    score -= 10

        return max(min(score, 100), 0)

    def _score_willingness(self, lead: Lead) -> int:
        """评估沟通意愿（0-100）"""
        score = 40

        if lead.status:
            status_val = str(lead.status).lower()
            if status_val in ("active", "engaged", "活跃", "qualified"):
                score += 35
            elif status_val in ("contacted", "已联系"):
                score += 20
            elif status_val in ("cold", "冷淡", "lost"):
                score -= 15

        if lead.intention_level:
            level = str(lead.intention_level).lower()
            if level in ("high", "a", "高"):
                score += 25
            elif level in ("medium", "b", "中"):
                score += 10

        return max(min(score, 100), 0)

    def _score_urgency(self, lead: Lead, profile: Optional[LeadProfile]) -> int:
        """评估紧急程度（0-100）"""
        score = 30

        if profile and profile.urgency_level:
            level = str(profile.urgency_level).lower()
            if level in ("urgent", "紧急", "high"):
                score += 50
            elif level in ("medium", "中等"):
                score += 25
            elif level in ("low", "低"):
                score += 5

        return min(score, 100)

    def _determine_grade(self, score: int, profile: Optional[LeadProfile]) -> str:
        """根据总分和资质字段确定等级

        特殊规则：
        - A级需要满足资质条件
        - D级考虑高风险因素
        """
        # 先检查 D 级条件（高风险）
        if profile:
            if profile.credit_status:
                credit = str(profile.credit_status).lower()
                if credit in ("poor", "差", "不良"):
                    return "D"

        # 基于分数阈值确定等级
        if score >= self.GRADE_THRESHOLDS["A"]:
            # A级需要满足额外资质条件
            if profile:
                has_good_credit = profile.credit_status and str(profile.credit_status).lower() in (
                    "good",
                    "良好",
                    "优秀",
                )
                is_urgent = profile.urgency_level and str(profile.urgency_level).lower() in ("high", "urgent", "高")
                has_assets = profile.has_house or profile.has_car

                if has_good_credit or has_assets:
                    return "A"
                elif is_urgent and has_assets:
                    return "A"
            return "B"

        elif score >= self.GRADE_THRESHOLDS["B"]:
            return "B"

        elif score >= self.GRADE_THRESHOLDS["C"]:
            return "C"

        else:
            return "D"

    def _generate_reason(self, grade: str, details: dict) -> str:
        """生成评分原因说明"""
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
