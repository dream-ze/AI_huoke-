"""选题规划服务"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.models.models import HotTopic, MvpInboxItem, MvpKnowledgeItem, TopicIdea, TopicPlan
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TopicPlanningService:
    def __init__(self, db: Session):
        self.db = db

    # === 选题计划 CRUD ===
    def list_plans(
        self,
        owner_id: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取选题计划列表"""
        try:
            query = self.db.query(TopicPlan).filter(TopicPlan.owner_id == owner_id)

            if status:
                query = query.filter(TopicPlan.status == status)
            if platform:
                query = query.filter(TopicPlan.platform == platform)

            total = query.count()
            items = query.order_by(TopicPlan.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return {
                "items": [self._serialize_plan(p) for p in items],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        except Exception as e:
            logger.error(f"获取选题计划列表失败: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    def get_plan(self, plan_id: int, owner_id: int) -> Optional[TopicPlan]:
        """获取单个选题计划"""
        try:
            return self.db.query(TopicPlan).filter(TopicPlan.id == plan_id, TopicPlan.owner_id == owner_id).first()
        except Exception as e:
            logger.error(f"获取选题计划失败: {e}")
            return None

    def create_plan(self, owner_id: int, data: dict) -> TopicPlan:
        """创建选题计划"""
        try:
            # 处理 scheduled_date 字符串转日期
            scheduled_date = data.get("scheduled_date")
            if isinstance(scheduled_date, str) and scheduled_date:
                scheduled_date = datetime.strptime(scheduled_date, "%Y-%m-%d").date()

            plan = TopicPlan(
                owner_id=owner_id,
                title=data.get("title", ""),
                platform=data.get("platform"),
                audience=data.get("audience"),
                status=data.get("status", "draft"),
                scheduled_date=scheduled_date,
                content_direction=data.get("content_direction"),
                reference_materials=data.get("reference_materials"),
                tags=data.get("tags"),
                notes=data.get("notes"),
            )
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
            return plan
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建选题计划失败: {e}")
            raise ValueError(f"创建选题计划失败: {str(e)}")

    def update_plan(self, plan_id: int, owner_id: int, data: dict) -> Optional[TopicPlan]:
        """更新选题计划"""
        try:
            plan = self.get_plan(plan_id, owner_id)
            if not plan:
                return None

            # 处理 scheduled_date 字符串转日期
            if "scheduled_date" in data:
                scheduled_date = data.get("scheduled_date")
                if isinstance(scheduled_date, str) and scheduled_date:
                    data["scheduled_date"] = datetime.strptime(scheduled_date, "%Y-%m-%d").date()

            updatable_fields = [
                "title",
                "platform",
                "audience",
                "status",
                "scheduled_date",
                "content_direction",
                "reference_materials",
                "tags",
                "notes",
            ]
            for field in updatable_fields:
                if field in data:
                    setattr(plan, field, data[field])

            self.db.commit()
            self.db.refresh(plan)
            return plan
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新选题计划失败: {e}")
            raise ValueError(f"更新选题计划失败: {str(e)}")

    def delete_plan(self, plan_id: int, owner_id: int) -> bool:
        """删除选题计划"""
        try:
            plan = self.get_plan(plan_id, owner_id)
            if not plan:
                return False

            self.db.delete(plan)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除选题计划失败: {e}")
            return False

    # === 选题创意 ===
    def add_idea(self, owner_id: int, data: dict) -> TopicIdea:
        """添加选题创意"""
        try:
            idea = TopicIdea(
                plan_id=data.get("plan_id"),
                title=data.get("title", ""),
                description=data.get("description"),
                keywords=data.get("keywords"),
                estimated_engagement=data.get("estimated_engagement"),
                source=data.get("source", "manual"),
                status=data.get("status", "pending"),
                platform=data.get("platform"),
                owner_id=owner_id,
            )
            self.db.add(idea)
            self.db.commit()
            self.db.refresh(idea)
            return idea
        except Exception as e:
            self.db.rollback()
            logger.error(f"添加选题创意失败: {e}")
            raise ValueError(f"添加选题创意失败: {str(e)}")

    def list_ideas(
        self,
        owner_id: int,
        plan_id: Optional[int] = None,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取选题创意列表"""
        try:
            query = self.db.query(TopicIdea).filter(TopicIdea.owner_id == owner_id)

            if plan_id:
                query = query.filter(TopicIdea.plan_id == plan_id)
            if status:
                query = query.filter(TopicIdea.status == status)
            if platform:
                query = query.filter(TopicIdea.platform == platform)

            total = query.count()
            items = query.order_by(TopicIdea.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            return {
                "items": [self._serialize_idea(i) for i in items],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        except Exception as e:
            logger.error(f"获取选题创意列表失败: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    def update_idea_status(self, idea_id: int, owner_id: int, status: str) -> Optional[TopicIdea]:
        """更新创意状态（accepted/rejected/used）"""
        try:
            idea = self.db.query(TopicIdea).filter(TopicIdea.id == idea_id, TopicIdea.owner_id == owner_id).first()
            if not idea:
                return None

            valid_statuses = ["pending", "accepted", "rejected", "used"]
            if status not in valid_statuses:
                raise ValueError(f"无效的状态: {status}")

            idea.status = status
            self.db.commit()
            self.db.refresh(idea)
            return idea
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新创意状态失败: {e}")
            raise

    # === 排期日历 ===
    def get_calendar(self, owner_id: int, start_date: str, end_date: str) -> list:
        """获取指定日期范围内的选题排期"""
        try:
            # 解析日期字符串
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

            plans = (
                self.db.query(TopicPlan)
                .filter(
                    TopicPlan.owner_id == owner_id,
                    TopicPlan.scheduled_date >= start,
                    TopicPlan.scheduled_date <= end,
                )
                .order_by(TopicPlan.scheduled_date)
                .all()
            )

            return [self._serialize_plan(p) for p in plans]
        except Exception as e:
            logger.error(f"获取排期日历失败: {e}")
            return []

    # === AI 选题推荐 ===
    def generate_recommendations(
        self,
        owner_id: int,
        platform: str,
        audience: Optional[str] = None,
        count: int = 5,
    ) -> list:
        """AI 生成选题推荐"""
        try:
            recommendations = []

            # 1. 从热门话题获取推荐
            hot_topics = (
                self.db.query(HotTopic)
                .filter(
                    HotTopic.platform == platform,
                    or_(
                        HotTopic.expires_at.is_(None),
                        HotTopic.expires_at > datetime.utcnow(),
                    ),
                )
                .order_by(desc(HotTopic.heat_score))
                .limit(count)
                .all()
            )

            for topic in hot_topics:
                recommendations.append(
                    {
                        "title": topic.title,
                        "description": f"热门话题，热度分数: {topic.heat_score:.1f}",
                        "source": "hot_trend",
                        "heat_score": topic.heat_score,
                        "category": topic.category,
                    }
                )

            # 2. 从知识库获取该平台的热门内容作为选题参考
            knowledge_items = (
                self.db.query(MvpKnowledgeItem)
                .filter(
                    MvpKnowledgeItem.platform == platform,
                    MvpKnowledgeItem.is_hot == True,
                )
                .order_by(desc(MvpKnowledgeItem.use_count))
                .limit(count)
                .all()
            )

            for item in knowledge_items:
                recommendations.append(
                    {
                        "title": item.title[:100] if item.title else "无标题",
                        "description": item.summary or item.content[:200] if item.content else "",
                        "source": "knowledge_base",
                        "use_count": item.use_count,
                        "topic": item.topic,
                    }
                )

            # 3. 如果有 audience，从知识库匹配人群
            if audience:
                audience_items = (
                    self.db.query(MvpKnowledgeItem)
                    .filter(
                        MvpKnowledgeItem.audience == audience,
                        or_(
                            MvpKnowledgeItem.platform == platform,
                            MvpKnowledgeItem.platform.is_(None),
                        ),
                    )
                    .order_by(desc(MvpKnowledgeItem.use_count))
                    .limit(count)
                    .all()
                )

                for item in audience_items:
                    recommendations.append(
                        {
                            "title": f"[{audience}] {item.title[:80] if item.title else '选题参考'}",
                            "description": item.summary or (item.content[:200] if item.content else ""),
                            "source": "audience_match",
                            "audience": audience,
                            "topic": item.topic,
                        }
                    )

            # 去重并限制数量
            seen_titles = set()
            unique_recommendations = []
            for rec in recommendations:
                if rec["title"] not in seen_titles:
                    seen_titles.add(rec["title"])
                    unique_recommendations.append(rec)
                    if len(unique_recommendations) >= count:
                        break

            # 4. 将推荐保存为 TopicIdea（source=ai_recommend）
            for rec in unique_recommendations:
                try:
                    idea = TopicIdea(
                        title=rec["title"],
                        description=rec.get("description", ""),
                        source="ai_recommend",
                        platform=platform,
                        owner_id=owner_id,
                        status="pending",
                    )
                    self.db.add(idea)
                except Exception:
                    pass  # 单条失败不影响整体

            self.db.commit()

            return unique_recommendations
        except Exception as e:
            self.db.rollback()
            logger.error(f"生成选题推荐失败: {e}")
            # 返回基于规则的简单推荐
            return self._generate_fallback_recommendations(platform, count)

    def _generate_fallback_recommendations(self, platform: str, count: int) -> list:
        """生成备用推荐（当主要方法失败时）"""
        # 基于平台的通用选题模板
        templates = {
            "xiaohongshu": [
                {"title": "分享一个普通人也能操作的贷款技巧", "description": "实用类选题"},
                {"title": "征信花还能贷款吗？亲测有效方案", "description": "问答类选题"},
                {"title": "负债高怎么破？教你3招", "description": "解决方案类选题"},
            ],
            "douyin": [
                {"title": "30秒说清楚：贷款避坑指南", "description": "短视频口播类"},
                {"title": "征信查询次数多怎么办？", "description": "问答类选题"},
                {"title": "这几个贷款误区你中了几个", "description": "盘点类选题"},
            ],
            "zhihu": [
                {"title": "征信花、负债高，还能贷款吗？", "description": "专业问答类"},
                {"title": "如何正确理解银行贷款审批逻辑？", "description": "知识科普类"},
                {"title": "网贷和银行贷款的区别在哪里？", "description": "对比分析类"},
            ],
        }

        platform_templates = templates.get(platform, templates["xiaohongshu"])
        return platform_templates[:count]

    # === 序列化方法 ===
    def _serialize_plan(self, plan: TopicPlan) -> dict:
        """序列化选题计划"""
        return {
            "id": plan.id,
            "owner_id": plan.owner_id,
            "title": plan.title,
            "platform": plan.platform,
            "audience": plan.audience,
            "status": plan.status,
            "scheduled_date": str(plan.scheduled_date) if plan.scheduled_date else None,
            "content_direction": plan.content_direction,
            "reference_materials": plan.reference_materials,
            "tags": plan.tags,
            "notes": plan.notes,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "ideas_count": len(plan.ideas) if plan.ideas else 0,
        }

    def _serialize_idea(self, idea: TopicIdea) -> dict:
        """序列化选题创意"""
        return {
            "id": idea.id,
            "plan_id": idea.plan_id,
            "title": idea.title,
            "description": idea.description,
            "keywords": idea.keywords,
            "estimated_engagement": idea.estimated_engagement,
            "source": idea.source,
            "status": idea.status,
            "platform": idea.platform,
            "owner_id": idea.owner_id,
            "created_at": idea.created_at.isoformat() if idea.created_at else None,
        }
