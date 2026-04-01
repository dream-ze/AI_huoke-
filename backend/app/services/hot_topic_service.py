"""热门话题服务"""

import logging
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Optional

from app.models.models import HotTopic, MvpInboxItem, MvpKnowledgeItem
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class HotTopicService:
    def __init__(self, db: Session):
        self.db = db

    def list_hot_topics(
        self,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> list:
        """获取热门话题列表"""
        try:
            query = self.db.query(HotTopic).filter(
                or_(
                    HotTopic.expires_at.is_(None),
                    HotTopic.expires_at > datetime.utcnow(),
                )
            )

            if platform:
                query = query.filter(HotTopic.platform == platform)
            if category:
                query = query.filter(HotTopic.category == category)

            topics = query.order_by(desc(HotTopic.heat_score)).limit(limit).all()

            return [self._serialize_topic(t) for t in topics]
        except Exception as e:
            logger.error(f"获取热门话题列表失败: {e}")
            return []

    def discover_hot_topics(self, platform: str) -> list:
        """从已采集内容中发现热门话题"""
        try:
            discovered = []
            cutoff_date = datetime.utcnow() - timedelta(days=7)

            # 1. 从 MvpInboxItem 分析高频关键词
            inbox_items = (
                self.db.query(MvpInboxItem)
                .filter(
                    MvpInboxItem.platform == platform,
                    MvpInboxItem.created_at >= cutoff_date,
                )
                .all()
            )

            # 2. 从 MvpKnowledgeItem 分析热门内容
            knowledge_items = (
                self.db.query(MvpKnowledgeItem)
                .filter(
                    MvpKnowledgeItem.platform == platform,
                    MvpKnowledgeItem.is_hot == True,
                )
                .limit(50)
                .all()
            )

            # 3. 提取标题中的关键词
            all_titles = [item.title for item in inbox_items if item.title]
            all_titles.extend([item.title for item in knowledge_items if item.title])

            keywords = self._extract_keywords(all_titles)

            # 4. 从知识库内容中提取主题
            topics_from_knowledge = self._extract_topics_from_knowledge(knowledge_items)

            # 5. 合并并创建热门话题
            for keyword, count in keywords.most_common(10):
                # 检查是否已存在
                existing = (
                    self.db.query(HotTopic).filter(HotTopic.platform == platform, HotTopic.title == keyword).first()
                )

                if existing:
                    # 更新热度分数
                    existing.heat_score = count * 10
                    existing.trend_direction = self._calculate_trend(existing.heat_score, count * 10)
                    discovered.append(self._serialize_topic(existing))
                else:
                    # 创建新话题
                    hot_topic = HotTopic(
                        platform=platform,
                        title=keyword,
                        heat_score=count * 10,
                        trend_direction="up",
                        category=self._infer_category(keyword),
                        expires_at=datetime.utcnow() + timedelta(days=7),
                    )
                    self.db.add(hot_topic)
                    discovered.append(
                        {
                            "title": keyword,
                            "heat_score": count * 10,
                            "trend_direction": "up",
                            "category": self._infer_category(keyword),
                            "is_new": True,
                        }
                    )

            # 6. 添加从知识库提取的主题
            for topic_info in topics_from_knowledge:
                topic_title = topic_info.get("title", "")
                if topic_title:
                    existing = (
                        self.db.query(HotTopic)
                        .filter(HotTopic.platform == platform, HotTopic.title == topic_title)
                        .first()
                    )

                    if not existing:
                        hot_topic = HotTopic(
                            platform=platform,
                            title=topic_title,
                            heat_score=topic_info.get("score", 50),
                            trend_direction="stable",
                            category=topic_info.get("topic"),
                            expires_at=datetime.utcnow() + timedelta(days=7),
                        )
                        self.db.add(hot_topic)
                        discovered.append(
                            {
                                "title": topic_title,
                                "heat_score": topic_info.get("score", 50),
                                "trend_direction": "stable",
                                "category": topic_info.get("topic"),
                                "is_new": True,
                            }
                        )

            self.db.commit()
            return discovered

        except Exception as e:
            self.db.rollback()
            logger.error(f"发现热门话题失败: {e}")
            return []

    def update_trend(
        self,
        topic_id: int,
        heat_score: float,
        trend_direction: str,
    ) -> Optional[HotTopic]:
        """更新话题趋势"""
        try:
            topic = self.db.query(HotTopic).filter(HotTopic.id == topic_id).first()
            if not topic:
                return None

            topic.heat_score = heat_score
            topic.trend_direction = trend_direction

            self.db.commit()
            self.db.refresh(topic)
            return topic
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新话题趋势失败: {e}")
            return None

    def cleanup_expired(self) -> int:
        """清理已过期的热门话题"""
        try:
            now = datetime.utcnow()
            expired = self.db.query(HotTopic).filter(HotTopic.expires_at < now).delete()
            self.db.commit()
            return expired
        except Exception as e:
            self.db.rollback()
            logger.error(f"清理过期话题失败: {e}")
            return 0

    def get_topic_by_id(self, topic_id: int) -> Optional[HotTopic]:
        """获取单个热门话题"""
        try:
            return self.db.query(HotTopic).filter(HotTopic.id == topic_id).first()
        except Exception:
            return None

    # === 私有方法 ===
    def _extract_keywords(self, titles: List[str]) -> Counter:
        """从标题列表中提取高频关键词"""
        # 停用词列表
        stopwords = {
            "的",
            "了",
            "是",
            "在",
            "有",
            "和",
            "与",
            "或",
            "我",
            "你",
            "他",
            "她",
            "这",
            "那",
            "个",
            "们",
            "着",
            "过",
            "就",
            "都",
            "也",
            "还",
            "要",
            "可以",
            "怎么",
            "什么",
            "如何",
            "为什么",
            "哪",
            "吗",
            "呢",
            "啊",
        }

        # 金融行业关键词模式
        keyword_patterns = [
            r"贷款",
            r"征信",
            r"信用",
            r"额度",
            r"负债",
            r"逾期",
            r"公积金",
            r"房贷",
            r"车贷",
            r"网贷",
            r"黑户",
            r"白户",
            r"查询",
            r"审批",
            r"利率",
            r"利息",
            r"下款",
            r"放款",
            r"提额",
            r"降额",
            r"封卡",
            r"风控",
            r"套现",
            r"分期",
            r"还款",
        ]

        all_words = []
        for title in titles:
            if not title:
                continue

            # 提取金融关键词
            for pattern in keyword_patterns:
                matches = re.findall(pattern, title)
                all_words.extend(matches)

            # 提取其他有意义的词（简单分词：2-4字的词）
            # 去除标点符号
            clean_title = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", title)
            for length in range(4, 1, -1):
                for i in range(len(clean_title) - length + 1):
                    word = clean_title[i : i + length]
                    if word not in stopwords and len(word) >= 2:
                        all_words.append(word)

        return Counter(all_words)

    def _extract_topics_from_knowledge(self, items: List[MvpKnowledgeItem]) -> List[dict]:
        """从知识库条目中提取主题"""
        topics = []
        for item in items:
            if not item.title:
                continue

            topic_info = {
                "title": item.title[:100] if item.title else None,
                "score": 50 + (item.use_count or 0) * 5,
                "topic": item.topic,
            }

            # 如果有 hook_sentence，作为额外参考
            if item.hook_sentence:
                topic_info["hook"] = item.hook_sentence[:100]

            topics.append(topic_info)

        return topics

    def _infer_category(self, keyword: str) -> Optional[str]:
        """推断关键词所属分类"""
        category_keywords = {
            "贷款知识": ["贷款", "借款", "额度", "审批", "下款", "放款"],
            "征信修复": ["征信", "信用", "查询", "黑户", "白户", "逾期"],
            "负债管理": ["负债", "还款", "分期", "利息", "利率"],
            "公积金贷款": ["公积金", "房贷", "住房"],
            "车辆贷款": ["车贷", "汽车", "二手车"],
            "网贷避坑": ["网贷", "套现", "风控"],
            "信用卡技巧": ["提额", "降额", "封卡", "信用卡"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in keyword for kw in keywords):
                return category

        return "其他"

    def _calculate_trend(self, old_score: float, new_score: float) -> str:
        """计算趋势方向"""
        if old_score == 0:
            return "up"
        change_ratio = (new_score - old_score) / old_score
        if change_ratio > 0.1:
            return "up"
        elif change_ratio < -0.1:
            return "down"
        else:
            return "stable"

    def _serialize_topic(self, topic: HotTopic) -> dict:
        """序列化热门话题"""
        return {
            "id": topic.id,
            "platform": topic.platform,
            "title": topic.title,
            "heat_score": topic.heat_score,
            "trend_direction": topic.trend_direction,
            "category": topic.category,
            "source_url": topic.source_url,
            "discovered_at": topic.discovered_at.isoformat() if topic.discovered_at else None,
            "expires_at": topic.expires_at.isoformat() if topic.expires_at else None,
        }
