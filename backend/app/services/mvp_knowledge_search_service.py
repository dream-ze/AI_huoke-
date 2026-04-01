"""MVP 知识库搜索服务 - 检索、关键词提取、混合搜索"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from app.models.models import MvpKnowledgeItem
from sqlalchemy import case, desc, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MvpKnowledgeSearchService:
    """知识库搜索服务 - 负责搜索、检索、关键词提取"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 关键词配置 ====================
    # 用于关键词提取和分类

    TOPIC_KEYWORDS = {
        "loan": ["贷款", "借款", "信贷", "单子", "报表", "贷"],
        "credit": ["征信", "信用", "申请", "卡"],
        "online_loan": ["网贷", "线上贷", "网上贷", "手机贷"],
        "housing_fund": ["公积金", "住房", "房贷"],
        "credit_card": ["信用卡", "卡债", "刷卡"],
        "car_loan": ["车贷", "汽车贷", "二手车"],
    }

    AUDIENCE_KEYWORDS = {
        "bad_credit": ["征信花", "黑户", "征信差", "查询次数多", "逾期", "白户"],
        "high_debt": ["负债", "负债高", "很多债", "还不起", "欠钱"],
        "office_worker": ["上班族", "工资", "白领", "打工", "职员"],
        "self_employed": ["个体户", "店主", "创业", "老板", "生意", "自营"],
        "freelancer": ["自由职业", "外卖", "快递", "司机", "滴滴"],
    }

    CONTENT_TYPE_KEYWORDS = {
        "案例": ["案例", "故事", "经历", "分享", "成功", "亲身"],
        "知识": ["知识", "科普", "教程", "方法", "技巧", "攻略"],
        "规则": ["规则", "策略", "政策", "平台", "算法"],
        "模板": ["模板", "文案", "标题", "开头", "结尾"],
    }

    OPENING_TYPE_KEYWORDS = {
        "提问": ["？", "么", "吗", "呢", "有没有", "怎样", "如何"],
        "数据": ["%", "万", "亿", "数据", "统计", "调查"],
        "故事": ["我", "有个", "有位", "有人", "姐", "兄", "老铁"],
        "痛点": ["没钱", "着急", "却", "但是", "可惜", "犯愁"],
    }

    CTA_STYLE_KEYWORDS = {
        "私信": ["私信", "打我", "消息", "DM", "发我"],
        "评论": ["评论", "留言", "扣评论", "写评论"],
        "关注": ["关注", "粉丝", "点关注"],
    }

    RISK_KEYWORDS = {
        "high": ["干分区", "稳赚", "保证", "内部", "保函", "加急", "打表唇"],
        "medium": ["快速", "极速", "秒批", "必过", "口子"],
    }

    # ==================== 搜索方法 ====================

    def search_knowledge(self, query: str, platform=None, audience=None, limit=5):
        """关键词检索知识（MVP版，预留向量化接口）"""
        try:
            q = self.db.query(MvpKnowledgeItem)
            if platform:
                q = q.filter(MvpKnowledgeItem.platform == platform)
            if audience:
                q = q.filter(MvpKnowledgeItem.audience == audience)
            # 简单关键词匹配
            keywords = query.split()
            for kw in keywords[:3]:
                q = q.filter(or_(MvpKnowledgeItem.title.ilike(f"%{kw}%"), MvpKnowledgeItem.content.ilike(f"%{kw}%")))
            results = q.limit(limit).all()
            # 更新使用计数
            for r in results:
                r.use_count += 1
            self.db.commit()
            return results
        except Exception:
            self.db.rollback()
            return []

    def search_for_generation(
        self,
        platform: str,
        audience: str,
        topic: str = None,
        content_type: str = None,
        account_type: str = None,
        goal: str = None,
    ) -> dict:
        """
        为内容生成提供多维度知识召回。
        返回结构化字典：
        {
            "hot_content": [...],        # 爆款内容 3~5条
            "audience_insight": [...],   # 人群洞察 2~3条
            "platform_rules": [...],     # 平台表达规则 3~5条
            "risk_rules": [...],         # 风险规避规则 3~5条
            "tone_template": None,       # 账号语气模板 1套
            "cta_templates": [...]       # CTA模板 2~3条
        }
        """
        result = {
            "hot_content": [],
            "audience_insight": [],
            "platform_rules": [],
            "risk_rules": [],
            "tone_template": None,
            "cta_templates": [],
        }

        try:
            # 1. 爆款内容召回：platform + audience + topic + content_type 联合过滤
            hot_query = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.platform == platform)
            # 联合过滤: audience
            if audience:
                hot_query = hot_query.filter(
                    or_(MvpKnowledgeItem.audience == audience, MvpKnowledgeItem.audience.is_(None))
                )
            # 联合过滤: topic
            if topic:
                hot_query = hot_query.filter(
                    or_(
                        MvpKnowledgeItem.topic == topic,
                        MvpKnowledgeItem.title.ilike(f"%{topic}%"),
                        MvpKnowledgeItem.content.ilike(f"%{topic}%"),
                    )
                )
            # 联合过滤: content_type
            if content_type:
                hot_query = hot_query.filter(MvpKnowledgeItem.content_type == content_type)
            # 优先案例类型的排序：先按 content_type='案例' DESC，再按 use_count DESC
            hot_query = hot_query.order_by(
                desc(case((MvpKnowledgeItem.content_type == "案例", 1), else_=0)), MvpKnowledgeItem.use_count.desc()
            ).limit(5)
            hot_items = hot_query.all()
            result["hot_content"] = [self._serialize_knowledge_item(item) for item in hot_items]
            for item in hot_items:
                item.use_count += 1

            # 2. 人群洞察召回：audience匹配 + category='人群洞察'
            audience_query = (
                self.db.query(MvpKnowledgeItem)
                .filter(MvpKnowledgeItem.category == "人群洞察", MvpKnowledgeItem.audience == audience)
                .limit(3)
            )
            audience_items = audience_query.all()
            result["audience_insight"] = [self._serialize_knowledge_item(item) for item in audience_items]
            for item in audience_items:
                item.use_count += 1

            # 3. 平台表达规则召回：platform匹配 + category='平台规则'
            platform_rules_query = (
                self.db.query(MvpKnowledgeItem)
                .filter(MvpKnowledgeItem.category == "平台规则", MvpKnowledgeItem.platform == platform)
                .limit(5)
            )
            platform_rule_items = platform_rules_query.all()
            result["platform_rules"] = [self._serialize_knowledge_item(item) for item in platform_rule_items]
            for item in platform_rule_items:
                item.use_count += 1

            # 4. 风险规避规则召回：category='风险提示'
            risk_query = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.category == "风险提示").limit(5)
            risk_items = risk_query.all()
            result["risk_rules"] = [self._serialize_knowledge_item(item) for item in risk_items]
            for item in risk_items:
                item.use_count += 1

            # 5. 语气模板召回：category='语气模板' + platform匹配
            tone_query = (
                self.db.query(MvpKnowledgeItem)
                .filter(MvpKnowledgeItem.category == "语气模板", MvpKnowledgeItem.platform == platform)
                .first()
            )
            if tone_query:
                result["tone_template"] = self._serialize_knowledge_item(tone_query)
                tone_query.use_count += 1

            # 6. CTA模板召回：category='CTA模板'，如有goal优先匹配cta_style包含goal的
            cta_query = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.category == "CTA模板")
            if goal:
                # 优先匹配 cta_style 包含 goal 的
                cta_query = cta_query.order_by(desc(case((MvpKnowledgeItem.cta_style.ilike(f"%{goal}%"), 1), else_=0)))
            cta_items = cta_query.limit(3).all()
            result["cta_templates"] = [self._serialize_knowledge_item(item) for item in cta_items]
            for item in cta_items:
                item.use_count += 1

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            # 发生异常时返回空结果，不报错
            logger.warning(f"Knowledge query failed: {e}")

        return result

    async def search_for_generation_v2(
        self,
        platform: str = "",
        audience: str = "",
        topic: str = "",
        content_type: str = "",
        account_type: str = "",
        goal: str = "",
        embedding_model: str = "volcano",
    ) -> dict:
        """升级版: 使用混合检索从多个分库并发召回知识 (Task #11 并发优化)

        Returns:
            {
                "hot_content": [...],
                "audience_insight": [...],
                "platform_rules": [...],
                "risk_rules": [...],
                "tone_template": None or {...},
                "cta_templates": [...]
            }
        """
        from app.services.hybrid_search_service import get_hybrid_search_service

        hybrid = get_hybrid_search_service(self.db)

        # 构建检索query (组合用户选择的条件作为语义查询)
        query_parts = []
        if platform:
            query_parts.append(platform)
        if audience:
            query_parts.append(audience)
        if topic:
            query_parts.append(topic)
        if goal:
            query_parts.append(goal)
        query = " ".join(query_parts) if query_parts else "内容创作"

        result = {
            "hot_content": [],
            "audience_insight": [],
            "platform_rules": [],
            "risk_rules": [],
            "tone_template": None,
            "cta_templates": [],
        }

        try:
            # Task #11: 使用 asyncio.gather 并发检索所有分库
            async def search_hot_content():
                """爆款内容库召回 3~5条"""
                return await hybrid.search(
                    query=query,
                    library_type="hot_content",
                    platform=platform or None,
                    audience=audience or None,
                    topic=topic or None,
                    top_k=3,  # 从5减少为3，压缩上下文
                    embedding_model=embedding_model,
                )

            async def search_audience_profile():
                """人群洞察库召回 2~3条"""
                return await hybrid.search(
                    query=audience or query,
                    library_type="audience_profile",
                    audience=audience or None,
                    top_k=2,  # 从3减少为2，压缩上下文
                    embedding_model=embedding_model,
                )

            async def search_platform_rules():
                """平台规则库召回 3~5条"""
                return await hybrid.search(
                    query=platform or query,
                    library_type="platform_rules",
                    platform=platform or None,
                    top_k=3,  # 从5减少为3，压缩上下文
                    embedding_model=embedding_model,
                )

            async def search_compliance_rules():
                """审核规则库召回 3~5条"""
                return await hybrid.search(
                    query="风险 合规 敏感词",
                    library_type="compliance_rules",
                    top_k=3,  # 从5减少为3，压缩上下文
                    embedding_model=embedding_model,
                )

            async def search_account_positioning():
                """账号语气库召回 1条"""
                return await hybrid.search(
                    query=f"{platform} {account_type} 语气",
                    library_type="account_positioning",
                    platform=platform or None,
                    top_k=1,
                    embedding_model=embedding_model,
                )

            async def search_prompt_templates():
                """CTA模板库召回 2~3条"""
                return await hybrid.search(
                    query=goal or "转化",
                    library_type="prompt_templates",
                    top_k=2,  # 从3减少为2，压缩上下文
                    embedding_model=embedding_model,
                )

            # 并发执行所有检索，return_exceptions=True 确保单个失败不影响整体
            results = await asyncio.gather(
                search_hot_content(),
                search_audience_profile(),
                search_platform_rules(),
                search_compliance_rules(),
                search_account_positioning(),
                search_prompt_templates(),
                return_exceptions=True,
            )

            # 处理结果
            # 1. 爆款内容
            if not isinstance(results[0], Exception):
                result["hot_content"] = [r.to_dict() for r in results[0]]
            else:
                logger.warning(f"爆款内容库检索失败: {results[0]}")

            # 2. 人群洞察
            if not isinstance(results[1], Exception):
                result["audience_insight"] = [r.to_dict() for r in results[1]]
            else:
                logger.warning(f"人群洞察库检索失败: {results[1]}")

            # 3. 平台规则
            if not isinstance(results[2], Exception):
                result["platform_rules"] = [r.to_dict() for r in results[2]]
            else:
                logger.warning(f"平台规则库检索失败: {results[2]}")

            # 4. 合规规则
            if not isinstance(results[3], Exception):
                result["risk_rules"] = [r.to_dict() for r in results[3]]
            else:
                logger.warning(f"合规规则库检索失败: {results[3]}")

            # 5. 账号语气
            if not isinstance(results[4], Exception) and results[4]:
                result["tone_template"] = results[4][0].to_dict()
            else:
                if isinstance(results[4], Exception):
                    logger.warning(f"账号语气库检索失败: {results[4]}")

            # 6. CTA模板
            if not isinstance(results[5], Exception):
                result["cta_templates"] = [r.to_dict() for r in results[5]]
            else:
                logger.warning(f"CTA模板库检索失败: {results[5]}")

        except Exception as e:
            logger.error(f"混合检索异常: {e}")
            # 降级: 使用原有检索方法
            return self.search_for_generation(
                platform=platform,
                audience=audience,
                topic=topic,
                content_type=content_type,
                account_type=account_type,
                goal=goal,
            )

        # 更新使用计数
        all_knowledge_ids = set()
        for key in ["hot_content", "audience_insight", "platform_rules", "risk_rules", "cta_templates"]:
            for item in result[key]:
                kid = item.get("knowledge_id")
                if kid:
                    all_knowledge_ids.add(kid)
        if result["tone_template"]:
            kid = result["tone_template"].get("knowledge_id")
            if kid:
                all_knowledge_ids.add(kid)

        for kid in all_knowledge_ids:
            try:
                self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id == kid).update(
                    {MvpKnowledgeItem.use_count: MvpKnowledgeItem.use_count + 1}
                )
            except Exception as e:
                logger.warning(f"Failed to update use_count: {e}")
        self.db.commit()

        return result

    # ==================== 关键词提取方法 ====================

    def extract_all_fields(self, title: str, content: str) -> Dict[str, Any]:
        """提取所有结构化字段（供入库时使用）

        Args:
            title: 内容标题
            content: 原始内容

        Returns:
            包含所有提取字段的字典
        """
        full_text = f"{title or ''} {content or ''}"
        return {
            "topic": self._extract_topic(full_text),
            "audience": self._extract_audience(full_text),
            "content_type": self._extract_content_type(full_text),
            "opening_type": self._extract_opening_type(content),
            "hook_sentence": self._extract_hook_sentence(content),
            "cta_style": self._extract_cta_style(content),
            "risk_level": self._extract_risk_level(full_text),
            "summary": self._extract_summary(content),
        }

    def _extract_topic(self, content: str) -> Optional[str]:
        """基于关键词提取topic"""
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                return topic
        return None

    def _extract_audience(self, content: str) -> Optional[str]:
        """基于关键词提取目标人群"""
        for audience, keywords in self.AUDIENCE_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                return audience
        return None

    def _extract_content_type(self, content: str) -> str:
        """基于关键词提取内容类型"""
        for ctype, keywords in self.CONTENT_TYPE_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                return ctype
        return "通用"

    def _extract_opening_type(self, content: str) -> Optional[str]:
        """基于开头内容判断开头方式"""
        # 取前50字分析
        opening = content[:50] if content else ""
        for otype, keywords in self.OPENING_TYPE_KEYWORDS.items():
            if any(kw in opening for kw in keywords):
                return otype
        return None

    def _extract_hook_sentence(self, content: str) -> Optional[str]:
        """提取第一句作为钩子句"""
        if not content:
            return None
        # 尝试按标点符号切割
        sentences = re.split(r"[\\n。！？!?]", content)
        for s in sentences:
            s = s.strip()
            if len(s) >= 5:
                return s[:100]  # 最多100字
        return content[:100] if content else None

    def _extract_cta_style(self, content: str) -> Optional[str]:
        """检测CTA引导方式"""
        for cta, keywords in self.CTA_STYLE_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                return cta
        return None

    def _extract_risk_level(self, content: str) -> str:
        """基于敏感词判断风险等级"""
        for level, keywords in self.RISK_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                return level
        return "low"

    def _extract_summary(self, content: str) -> str:
        """截取前200字作为摘要"""
        if not content:
            return ""
        # 清理多余空白
        clean = re.sub(r"\s+", " ", content).strip()
        return clean[:200]

    # ==================== 辅助方法 ====================

    def _serialize_knowledge_item(self, item: MvpKnowledgeItem) -> dict:
        """序列化知识条目为字典"""
        return {
            "id": item.id,
            "title": item.title,
            "content": item.content,
            "category": item.category,
            "platform": item.platform,
            "audience": item.audience,
            "topic": getattr(item, "topic", None),
            "hook_sentence": getattr(item, "hook_sentence", None),
            "cta_style": getattr(item, "cta_style", None),
            "risk_level": getattr(item, "risk_level", None),
            "summary": getattr(item, "summary", None),
        }
