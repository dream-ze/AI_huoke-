"""
线索归因服务

实现线索来源归因的完整链路追踪，包括：
- 线索创建时自动追溯来源
- 获取完整归因链
- 内容 ROI 分析
- 活动/平台/账号归因报告
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.models import Campaign, Customer, Lead, LeadSourceAttribution, PublishAccount, PublishedContent, User
from sqlalchemy import Date, and_, case, desc, func
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)


class AttributionService:
    """线索归因服务类"""

    @staticmethod
    def create_attribution(
        db: Session,
        lead_id: int,
        source_data: Dict[str, Any],
    ) -> LeadSourceAttribution:
        """
        线索创建时自动追溯来源

        Args:
            db: 数据库会话
            lead_id: 线索ID
            source_data: 来源数据，包含：
                - platform: 触点平台
                - account_id: 发布账号ID
                - content_id: 发布内容ID
                - campaign_id: 活动ID
                - audience_tags: 受众标签
                - topic_tags: 主题标签
                - channel: 渠道
                - first_contact_time: 首次接触时间
                - touchpoint_url: 触点URL
                - attribution_type: 归因类型 (默认 last_touch)

        Returns:
            LeadSourceAttribution: 创建的归因记录
        """
        try:
            # 提取参数
            platform = source_data.get("platform")
            account_id = source_data.get("account_id")
            content_id = source_data.get("content_id")
            campaign_id = source_data.get("campaign_id")
            channel = source_data.get("channel")
            first_contact_time = source_data.get("first_contact_time")
            touchpoint_url = source_data.get("touchpoint_url")
            attribution_type = source_data.get("attribution_type", "last_touch")

            # 创建归因记录
            attribution = LeadSourceAttribution(
                lead_id=lead_id,
                campaign_id=campaign_id,
                publish_account_id=account_id,
                published_content_id=content_id,
                touchpoint_platform=platform,
                touchpoint_url=touchpoint_url,
                first_touch_time=first_contact_time or datetime.utcnow(),
                last_touch_time=datetime.utcnow(),
                attribution_type=attribution_type,
                conversion_path=[
                    {
                        "platform": platform,
                        "account_id": account_id,
                        "content_id": content_id,
                        "campaign_id": campaign_id,
                        "channel": channel,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ],
            )

            db.add(attribution)

            # 同时更新 Lead 表的归因字段
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                lead.campaign_id = campaign_id
                lead.publish_account_id = account_id
                lead.published_content_id = content_id
                lead.first_touch_time = first_contact_time or datetime.utcnow()
                lead.attribution_chain = {
                    "platform": platform,
                    "account_id": account_id,
                    "content_id": content_id,
                    "campaign_id": campaign_id,
                    "channel": channel,
                }

            db.commit()
            db.refresh(attribution)

            logger.info(
                f"Created attribution for lead {lead_id}: platform={platform}, "
                f"account_id={account_id}, content_id={content_id}, campaign_id={campaign_id}"
            )

            return attribution

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create attribution for lead {lead_id}: {e}")
            raise

    @staticmethod
    def get_attribution_chain(db: Session, lead_id: int) -> Optional[Dict[str, Any]]:
        """
        获取完整归因链

        通过 JOIN 查询关联：
        leads -> lead_source_attributions -> campaigns -> publish_accounts -> published_contents

        Args:
            db: 数据库会话
            lead_id: 线索ID

        Returns:
            归因链信息字典，包含：
            - platform, account_name, content_title, campaign_name
            - audience_tags, topic_tags, channel, first_contact_time
            - current_stage, conversion_result
        """
        try:
            # 使用 JOIN 一次性查询所有关联数据
            result = (
                db.query(
                    Lead.id.label("lead_id"),
                    Lead.status.label("current_stage"),
                    Lead.platform.label("platform"),
                    Lead.first_touch_time.label("first_contact_time"),
                    LeadSourceAttribution.touchpoint_url.label("touchpoint_url"),
                    LeadSourceAttribution.touchpoint_platform.label("touchpoint_platform"),
                    Campaign.name.label("campaign_name"),
                    PublishAccount.account_name.label("account_name"),
                    PublishAccount.platform.label("account_platform"),
                    PublishedContent.title.label("content_title"),
                    Customer.id.label("customer_id"),
                    Customer.customer_status.label("conversion_result"),
                )
                .outerjoin(
                    LeadSourceAttribution,
                    Lead.id == LeadSourceAttribution.lead_id,
                )
                .outerjoin(
                    Campaign,
                    LeadSourceAttribution.campaign_id == Campaign.id,
                )
                .outerjoin(
                    PublishAccount,
                    LeadSourceAttribution.publish_account_id == PublishAccount.id,
                )
                .outerjoin(
                    PublishedContent,
                    LeadSourceAttribution.published_content_id == PublishedContent.id,
                )
                .outerjoin(
                    Customer,
                    Lead.id == Customer.lead_id,
                )
                .filter(Lead.id == lead_id)
                .first()
            )

            if not result:
                logger.warning(f"Lead {lead_id} not found")
                return None

            # 从 conversion_path 或 attribution_chain 提取标签信息
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            audience_tags = []
            topic_tags = []
            channel = None

            if lead and lead.attribution_chain:
                chain_data = lead.attribution_chain
                channel = chain_data.get("channel")
                # 如果有额外存储的标签信息
                audience_tags = chain_data.get("audience_tags", [])
                topic_tags = chain_data.get("topic_tags", [])

            return {
                "lead_id": result.lead_id,
                "platform": result.touchpoint_platform or result.platform,
                "account_name": result.account_name,
                "content_title": result.content_title,
                "campaign_name": result.campaign_name,
                "audience_tags": audience_tags,
                "topic_tags": topic_tags,
                "channel": channel,
                "first_contact_time": result.first_contact_time,
                "current_stage": result.current_stage or "new",
                "conversion_result": result.conversion_result,
                "touchpoint_url": result.touchpoint_url,
            }

        except Exception as e:
            logger.error(f"Failed to get attribution chain for lead {lead_id}: {e}")
            raise

    @staticmethod
    def get_content_roi(db: Session, content_id: int) -> Dict[str, Any]:
        """
        获取单条内容 ROI

        统计该内容带来的：
        - 线索数
        - 转化客户数
        - 各分级占比

        Args:
            db: 数据库会话
            content_id: 发布内容ID

        Returns:
            内容 ROI 信息
        """
        try:
            # 获取内容基本信息
            content = db.query(PublishedContent).filter(PublishedContent.id == content_id).first()

            if not content:
                logger.warning(f"Content {content_id} not found")
                return {
                    "content_id": content_id,
                    "content_title": None,
                    "platform": None,
                    "lead_count": 0,
                    "conversion_count": 0,
                    "stage_distribution": {},
                    "conversion_rate": 0.0,
                }

            # 使用 JOIN 查询统计线索数据
            stats = (
                db.query(
                    func.count(Lead.id).label("lead_count"),
                    func.sum(Lead.conversions).label("conversion_count"),
                    func.sum(case((Lead.status == "new", 1), else_=0)).label("new_count"),
                    func.sum(case((Lead.status == "contacted", 1), else_=0)).label("contacted_count"),
                    func.sum(case((Lead.status == "qualified", 1), else_=0)).label("qualified_count"),
                    func.sum(case((Lead.status == "converted", 1), else_=0)).label("converted_count"),
                    func.sum(case((Lead.status == "lost", 1), else_=0)).label("lost_count"),
                )
                .filter(Lead.published_content_id == content_id)
                .first()
            )

            lead_count = stats.lead_count or 0
            conversion_count = stats.conversion_count or 0
            conversion_rate = (conversion_count / lead_count) if lead_count > 0 else 0.0

            return {
                "content_id": content_id,
                "content_title": content.title,
                "platform": content.platform,
                "lead_count": lead_count,
                "conversion_count": conversion_count,
                "stage_distribution": {
                    "new": stats.new_count or 0,
                    "contacted": stats.contacted_count or 0,
                    "qualified": stats.qualified_count or 0,
                    "converted": stats.converted_count or 0,
                    "lost": stats.lost_count or 0,
                },
                "conversion_rate": round(conversion_rate, 4),
            }

        except Exception as e:
            logger.error(f"Failed to get content ROI for content {content_id}: {e}")
            raise

    @staticmethod
    def get_campaign_attribution_report(
        db: Session,
        campaign_id: int,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> Dict[str, Any]:
        """
        获取活动归因报告

        按平台、账号、内容维度聚合线索数和转化数

        Args:
            db: 数据库会话
            campaign_id: 活动ID
            date_range: 日期范围 (start_date, end_date)

        Returns:
            活动归因报告
        """
        try:
            # 获取活动基本信息
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

            if not campaign:
                logger.warning(f"Campaign {campaign_id} not found")
                return {
                    "campaign_id": campaign_id,
                    "campaign_name": None,
                    "total_leads": 0,
                    "total_conversions": 0,
                    "by_platform": [],
                    "by_account": [],
                    "by_content": [],
                    "date_range": {"start": None, "end": None},
                }

            # 构建基础查询条件
            base_filter = [Lead.campaign_id == campaign_id]
            if date_range:
                start_date, end_date = date_range
                base_filter.append(Lead.created_at >= start_date)
                base_filter.append(Lead.created_at <= end_date)

            # 总体统计
            total_stats = (
                db.query(
                    func.count(Lead.id).label("total_leads"),
                    func.sum(Lead.conversions).label("total_conversions"),
                )
                .filter(*base_filter)
                .first()
            )

            # 按平台聚合
            by_platform = (
                db.query(
                    Lead.platform,
                    func.count(Lead.id).label("lead_count"),
                    func.sum(Lead.conversions).label("conversion_count"),
                    func.sum(Lead.valid_leads).label("valid_lead_count"),
                )
                .filter(*base_filter)
                .group_by(Lead.platform)
                .all()
            )

            platform_list = []
            for row in by_platform:
                lead_count = row.lead_count or 0
                conv_count = row.conversion_count or 0
                platform_list.append(
                    {
                        "platform": row.platform,
                        "lead_count": lead_count,
                        "conversion_count": conv_count,
                        "valid_lead_count": row.valid_lead_count or 0,
                        "conversion_rate": round((conv_count / lead_count) if lead_count > 0 else 0, 4),
                    }
                )

            # 按账号聚合 - 通过 publish_account_id JOIN
            by_account = (
                db.query(
                    Lead.publish_account_id,
                    PublishAccount.account_name,
                    PublishAccount.platform,
                    func.count(Lead.id).label("lead_count"),
                    func.sum(Lead.conversions).label("conversion_count"),
                    func.sum(Lead.valid_leads).label("valid_lead_count"),
                )
                .outerjoin(PublishAccount, Lead.publish_account_id == PublishAccount.id)
                .filter(*base_filter)
                .group_by(Lead.publish_account_id, PublishAccount.account_name, PublishAccount.platform)
                .all()
            )

            account_list = []
            for row in by_account:
                lead_count = row.lead_count or 0
                conv_count = row.conversion_count or 0
                account_list.append(
                    {
                        "account_id": row.publish_account_id,
                        "account_name": row.account_name or "未知账号",
                        "platform": row.platform,
                        "lead_count": lead_count,
                        "conversion_count": conv_count,
                        "valid_lead_count": row.valid_lead_count or 0,
                        "conversion_rate": round((conv_count / lead_count) if lead_count > 0 else 0, 4),
                    }
                )

            # 按内容聚合 - 通过 published_content_id JOIN
            by_content = (
                db.query(
                    Lead.published_content_id,
                    PublishedContent.title,
                    PublishedContent.platform,
                    func.count(Lead.id).label("lead_count"),
                    func.sum(Lead.conversions).label("conversion_count"),
                    func.sum(Lead.valid_leads).label("valid_lead_count"),
                )
                .outerjoin(PublishedContent, Lead.published_content_id == PublishedContent.id)
                .filter(*base_filter)
                .group_by(Lead.published_content_id, PublishedContent.title, PublishedContent.platform)
                .all()
            )

            content_list = []
            for row in by_content:
                lead_count = row.lead_count or 0
                conv_count = row.conversion_count or 0
                content_list.append(
                    {
                        "content_id": row.published_content_id,
                        "content_title": row.title or "未知内容",
                        "platform": row.platform,
                        "lead_count": lead_count,
                        "conversion_count": conv_count,
                        "valid_lead_count": row.valid_lead_count or 0,
                        "conversion_rate": round((conv_count / lead_count) if lead_count > 0 else 0, 4),
                    }
                )

            # 按线索数降序排序
            platform_list.sort(key=lambda x: x["lead_count"], reverse=True)
            account_list.sort(key=lambda x: x["lead_count"], reverse=True)
            content_list.sort(key=lambda x: x["lead_count"], reverse=True)

            date_range_dict = {"start": None, "end": None}
            if date_range:
                date_range_dict = {
                    "start": date_range[0].isoformat(),
                    "end": date_range[1].isoformat(),
                }

            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "total_leads": total_stats.total_leads or 0,
                "total_conversions": total_stats.total_conversions or 0,
                "by_platform": platform_list,
                "by_account": account_list,
                "by_content": content_list,
                "date_range": date_range_dict,
            }

        except Exception as e:
            logger.error(f"Failed to get campaign attribution report for campaign {campaign_id}: {e}")
            raise

    @staticmethod
    def get_platform_attribution_summary(
        db: Session,
        owner_id: int,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取平台归因汇总

        各平台的线索数、转化率对比

        Args:
            db: 数据库会话
            owner_id: 用户ID
            date_range: 日期范围 (start_date, end_date)

        Returns:
            平台归因汇总列表
        """
        try:
            # 构建查询条件
            filters = [Lead.owner_id == owner_id]
            if date_range:
                start_date, end_date = date_range
                filters.append(Lead.created_at >= start_date)
                filters.append(Lead.created_at <= end_date)

            # 按平台聚合统计
            platform_stats = (
                db.query(
                    Lead.platform,
                    func.count(Lead.id).label("lead_count"),
                    func.sum(Lead.conversions).label("conversion_count"),
                    func.sum(Lead.valid_leads).label("valid_lead_count"),
                )
                .filter(*filters)
                .group_by(Lead.platform)
                .all()
            )

            result = []
            for row in platform_stats:
                lead_count = row.lead_count or 0
                conv_count = row.conversion_count or 0
                valid_count = row.valid_lead_count or 0
                result.append(
                    {
                        "platform": row.platform,
                        "lead_count": lead_count,
                        "conversion_count": conv_count,
                        "conversion_rate": round((conv_count / lead_count) if lead_count > 0 else 0, 4),
                        "valid_lead_count": valid_count,
                    }
                )

            # 按线索数降序排序
            result.sort(key=lambda x: x["lead_count"], reverse=True)

            return result

        except Exception as e:
            logger.error(f"Failed to get platform attribution summary for user {owner_id}: {e}")
            raise

    @staticmethod
    def get_account_attribution_summary(
        db: Session,
        owner_id: int,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取账号归因汇总

        各账号的线索数、转化率对比

        Args:
            db: 数据库会话
            owner_id: 用户ID
            date_range: 日期范围 (start_date, end_date)

        Returns:
            账号归因汇总列表
        """
        try:
            # 构建查询条件
            filters = [Lead.owner_id == owner_id]
            if date_range:
                start_date, end_date = date_range
                filters.append(Lead.created_at >= start_date)
                filters.append(Lead.created_at <= end_date)

            # 按账号聚合统计 - 使用 JOIN
            account_stats = (
                db.query(
                    Lead.publish_account_id,
                    PublishAccount.account_name,
                    PublishAccount.platform,
                    func.count(Lead.id).label("lead_count"),
                    func.sum(Lead.conversions).label("conversion_count"),
                    func.sum(Lead.valid_leads).label("valid_lead_count"),
                )
                .outerjoin(PublishAccount, Lead.publish_account_id == PublishAccount.id)
                .filter(*filters)
                .group_by(Lead.publish_account_id, PublishAccount.account_name, PublishAccount.platform)
                .all()
            )

            result = []
            for row in account_stats:
                lead_count = row.lead_count or 0
                conv_count = row.conversion_count or 0
                valid_count = row.valid_lead_count or 0
                result.append(
                    {
                        "account_id": row.publish_account_id,
                        "account_name": row.account_name or "未知账号",
                        "platform": row.platform,
                        "lead_count": lead_count,
                        "conversion_count": conv_count,
                        "conversion_rate": round((conv_count / lead_count) if lead_count > 0 else 0, 4),
                        "valid_lead_count": valid_count,
                    }
                )

            # 按线索数降序排序
            result.sort(key=lambda x: x["lead_count"], reverse=True)

            return result

        except Exception as e:
            logger.error(f"Failed to get account attribution summary for user {owner_id}: {e}")
            raise

    @staticmethod
    def update_lead_attribution(
        db: Session,
        lead_id: int,
        source_data: Dict[str, Any],
    ) -> Optional[LeadSourceAttribution]:
        """
        更新线索归因信息

        用于线索状态变化时更新归因链

        Args:
            db: 数据库会话
            lead_id: 线索ID
            source_data: 更新的来源数据

        Returns:
            更新后的归因记录
        """
        try:
            attribution = db.query(LeadSourceAttribution).filter(LeadSourceAttribution.lead_id == lead_id).first()

            if not attribution:
                logger.warning(f"No attribution found for lead {lead_id}, creating new one")
                return AttributionService.create_attribution(db, lead_id, source_data)

            # 更新 last_touch_time
            attribution.last_touch_time = datetime.utcnow()

            # 更新 conversion_path
            if attribution.conversion_path is None:
                attribution.conversion_path = []

            new_path_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                **source_data,
            }
            attribution.conversion_path.append(new_path_entry)

            db.commit()
            db.refresh(attribution)

            logger.info(f"Updated attribution for lead {lead_id}")
            return attribution

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update attribution for lead {lead_id}: {e}")
            raise

    @staticmethod
    def get_attribution_by_content(
        db: Session,
        content_id: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取特定内容带来的所有线索归因信息

        Args:
            db: 数据库会话
            content_id: 发布内容ID
            limit: 返回数量限制

        Returns:
            线索归因列表
        """
        try:
            results = (
                db.query(
                    Lead.id.label("lead_id"),
                    Lead.status.label("status"),
                    Lead.platform.label("platform"),
                    Lead.created_at.label("created_at"),
                    Lead.conversions.label("conversions"),
                    LeadSourceAttribution.first_touch_time.label("first_touch_time"),
                    Customer.id.label("customer_id"),
                    Customer.customer_status.label("customer_status"),
                )
                .outerjoin(LeadSourceAttribution, Lead.id == LeadSourceAttribution.lead_id)
                .outerjoin(Customer, Lead.id == Customer.lead_id)
                .filter(Lead.published_content_id == content_id)
                .order_by(desc(Lead.created_at))
                .limit(limit)
                .all()
            )

            return [
                {
                    "lead_id": row.lead_id,
                    "status": row.status,
                    "platform": row.platform,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "conversions": row.conversions or 0,
                    "first_touch_time": row.first_touch_time,
                    "customer_id": row.customer_id,
                    "customer_status": row.customer_status,
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Failed to get attribution by content {content_id}: {e}")
            raise


# 创建服务实例，方便导入使用
attribution_service = AttributionService()
