"""MVP 知识库服务"""
import hashlib
import logging
import re
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, case, desc
from app.models.models import MvpKnowledgeItem, MvpMaterialItem, MvpTag, MvpMaterialTagRel

logger = logging.getLogger(__name__)


class MvpKnowledgeService:
    def __init__(self, db: Session):
        self.db = db

    def list_knowledge(self, page=1, size=20, platform=None, audience=None, 
                       style=None, category=None, keyword=None, topic=None, content_type=None,
                       library_type=None):
        """列出知识库条目"""
        try:
            q = self.db.query(MvpKnowledgeItem)
            if platform:
                q = q.filter(MvpKnowledgeItem.platform == platform)
            if audience:
                q = q.filter(MvpKnowledgeItem.audience == audience)
            if style:
                q = q.filter(MvpKnowledgeItem.style == style)
            if category:
                q = q.filter(MvpKnowledgeItem.category == category)
            if topic:
                q = q.filter(MvpKnowledgeItem.topic == topic)
            if content_type:
                q = q.filter(MvpKnowledgeItem.content_type == content_type)
            if library_type:
                q = q.filter(MvpKnowledgeItem.library_type == library_type)
            if keyword:
                q = q.filter(or_(
                    MvpKnowledgeItem.title.ilike(f"%{keyword}%"),
                    MvpKnowledgeItem.content.ilike(f"%{keyword}%")
                ))
            total = q.count()
            items = q.order_by(MvpKnowledgeItem.created_at.desc()).offset((page - 1) * size).limit(size).all()
            return {"items": items, "total": total, "page": page, "size": size}
        except Exception as e:
            return {"items": [], "total": 0, "page": page, "size": size, "error": str(e)}

    def get_knowledge(self, knowledge_id: int):
        """获取知识条目详情"""
        try:
            return self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id == knowledge_id).first()
        except Exception:
            return None

    def build_from_material(self, material_id: int):
        """从素材构建结构化知识"""
        try:
            material = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if not material:
                raise ValueError("素材不存在")
            
            # 检查是否已有知识条目
            existing = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.source_material_id == material_id
            ).first()
            if existing:
                # 更新而非重复创建
                existing.title = f"知识: {material.title[:100]}"
                existing.content = self._extract_knowledge(material.content)
                existing.platform = material.platform
                self.db.commit()
                return existing
            
            # 从标签推断人群和风格
            tags = self.db.query(MvpTag).join(MvpMaterialTagRel).filter(
                MvpMaterialTagRel.material_id == material_id
            ).all()
            audience = next((t.name for t in tags if t.type == "audience"), None)
            style_tag = next((t.name for t in tags if t.type == "style"), None)
            category = self._infer_category(material.content)
            
            knowledge = MvpKnowledgeItem(
                title=f"知识: {material.title[:100]}",
                content=self._extract_knowledge(material.content),
                category=category,
                platform=material.platform,
                audience=audience,
                style=style_tag,
                source_material_id=material_id,
            )
            self.db.add(knowledge)
            self.db.commit()
            self.db.refresh(knowledge)
            return knowledge
        except ValueError:
            raise
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"构建知识失败: {str(e)}")

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
                q = q.filter(or_(
                    MvpKnowledgeItem.title.ilike(f"%{kw}%"),
                    MvpKnowledgeItem.content.ilike(f"%{kw}%")
                ))
            results = q.limit(limit).all()
            # 更新使用计数
            for r in results:
                r.use_count += 1
            self.db.commit()
            return results
        except Exception:
            self.db.rollback()
            return []

    def _extract_knowledge(self, content: str) -> str:
        """简单的知识抽取（MVP版，后续可替换为AI抽取）"""
        if not content:
            return ""
        # 按段落分割，保留有实质内容的段落
        paragraphs = [p.strip() for p in content.split("\n") if len(p.strip()) > 20]
        return "\n\n".join(paragraphs[:10])  # 最多保留10段

    def _infer_category(self, content: str) -> str:
        """简单分类推断"""
        if not content:
            return "通用知识"
        if any(kw in content for kw in ["贷款", "借款", "额度", "利率", "审批"]):
            return "贷款知识"
        if any(kw in content for kw in ["案例", "经历", "故事", "分享"]):
            return "行业案例"
        if any(kw in content for kw in ["风险", "注意", "避坑", "小心"]):
            return "风险提示"
        if any(kw in content for kw in ["平台", "渠道", "规则", "算法"]):
            return "平台策略"
        return "通用知识"
    
    def _infer_library_type(self, category: str, content_type: str = "") -> str:
        """根据category和content_type推断分库类型"""
        category_lower = (category or "").lower()
    
        if any(kw in category_lower for kw in ["爆款", "案例", "热门"]):
            return "hot_content"
        elif any(kw in category_lower for kw in ["人群", "画像", "洞察"]):
            return "audience_profile"
        elif any(kw in category_lower for kw in ["平台规则", "平台表达"]):
            return "platform_rules"
        elif any(kw in category_lower for kw in ["风险", "合规", "审核", "敏感"]):
            return "compliance_rules"
        elif any(kw in category_lower for kw in ["语气", "账号", "定位", "角色"]):
            return "account_positioning"
        elif any(kw in category_lower for kw in ["模板", "提示词", "prompt", "cta"]):
            return "prompt_templates"
        else:
            return "industry_phrases"  # 默认
    
    def _infer_layer(self, library_type: str, content_type: str = "") -> str:
        """推断知识层级"""
        if library_type in ("compliance_rules", "platform_rules"):
            return "rule"
        elif library_type in ("prompt_templates", "account_positioning"):
            return "generation"
        elif library_type == "hot_content":
            return "structured"
        else:
            return "structured"  # 默认

    def create_knowledge(self, data: dict):
        """手动创建知识条目"""
        try:
            knowledge = MvpKnowledgeItem(
                title=data.get("title", ""),
                content=data.get("content", ""),
                category=data.get("category", "通用知识"),
                platform=data.get("platform"),
                audience=data.get("audience"),
                style=data.get("style"),
            )
            self.db.add(knowledge)
            self.db.commit()
            self.db.refresh(knowledge)
            return knowledge
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"创建知识失败: {str(e)}")

    def update_knowledge(self, knowledge_id: int, data: dict):
        """更新知识条目"""
        try:
            item = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id == knowledge_id).first()
            if not item:
                raise ValueError("知识条目不存在")
            
            for key in ["title", "content", "category", "platform", "audience", "style"]:
                if key in data:
                    setattr(item, key, data[key])
            
            self.db.commit()
            return item
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"更新失败: {str(e)}")

    def delete_knowledge(self, knowledge_id: int):
        """删除知识条目"""
        try:
            item = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id == knowledge_id).first()
            if not item:
                raise ValueError("知识条目不存在")
            self.db.delete(item)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"删除失败: {str(e)}")

    def get_categories(self) -> list:
        """获取所有分类"""
        try:
            from sqlalchemy import func
            categories = self.db.query(MvpKnowledgeItem.category).distinct().all()
            return [c[0] for c in categories if c[0]]
        except Exception:
            return []

    def _serialize_knowledge_item(self, item: MvpKnowledgeItem) -> dict:
        """序列化知识条目为字典"""
        return {
            "id": item.id,
            "title": item.title,
            "content": item.content,
            "category": item.category,
            "platform": item.platform,
            "audience": item.audience,
            "topic": getattr(item, 'topic', None),
            "hook_sentence": getattr(item, 'hook_sentence', None),
            "cta_style": getattr(item, 'cta_style', None),
            "risk_level": getattr(item, 'risk_level', None),
            "summary": getattr(item, 'summary', None),
        }

    def search_for_generation(
        self,
        platform: str,
        audience: str,
        topic: str = None,
        content_type: str = None,
        account_type: str = None,
        goal: str = None
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
            hot_query = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.platform == platform
            )
            # 联合过滤: audience
            if audience:
                hot_query = hot_query.filter(
                    or_(
                        MvpKnowledgeItem.audience == audience,
                        MvpKnowledgeItem.audience.is_(None)
                    )
                )
            # 联合过滤: topic
            if topic:
                hot_query = hot_query.filter(
                    or_(
                        MvpKnowledgeItem.topic == topic,
                        MvpKnowledgeItem.title.ilike(f"%{topic}%"),
                        MvpKnowledgeItem.content.ilike(f"%{topic}%")
                    )
                )
            # 联合过滤: content_type
            if content_type:
                hot_query = hot_query.filter(
                    MvpKnowledgeItem.content_type == content_type
                )
            # 优先案例类型的排序：先按 content_type='案例' DESC，再按 use_count DESC
            hot_query = hot_query.order_by(
                desc(case((MvpKnowledgeItem.content_type == '案例', 1), else_=0)),
                MvpKnowledgeItem.use_count.desc()
            ).limit(5)
            hot_items = hot_query.all()
            result["hot_content"] = [self._serialize_knowledge_item(item) for item in hot_items]
            for item in hot_items:
                item.use_count += 1
            
            # 2. 人群洞察召回：audience匹配 + category='人群洞察'
            audience_query = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.category == '人群洞察',
                MvpKnowledgeItem.audience == audience
            ).limit(3)
            audience_items = audience_query.all()
            result["audience_insight"] = [self._serialize_knowledge_item(item) for item in audience_items]
            for item in audience_items:
                item.use_count += 1
            
            # 3. 平台表达规则召回：platform匹配 + category='平台规则'
            platform_rules_query = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.category == '平台规则',
                MvpKnowledgeItem.platform == platform
            ).limit(5)
            platform_rule_items = platform_rules_query.all()
            result["platform_rules"] = [self._serialize_knowledge_item(item) for item in platform_rule_items]
            for item in platform_rule_items:
                item.use_count += 1
            
            # 4. 风险规避规则召回：category='风险提示'
            risk_query = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.category == '风险提示'
            ).limit(5)
            risk_items = risk_query.all()
            result["risk_rules"] = [self._serialize_knowledge_item(item) for item in risk_items]
            for item in risk_items:
                item.use_count += 1
            
            # 5. 语气模板召回：category='语气模板' + platform匹配
            tone_query = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.category == '语气模板',
                MvpKnowledgeItem.platform == platform
            ).first()
            if tone_query:
                result["tone_template"] = self._serialize_knowledge_item(tone_query)
                tone_query.use_count += 1
            
            # 6. CTA模板召回：category='CTA模板'，如有goal优先匹配cta_style包含goal的
            cta_query = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.category == 'CTA模板'
            )
            if goal:
                # 优先匹配 cta_style 包含 goal 的
                cta_query = cta_query.order_by(
                    desc(case((MvpKnowledgeItem.cta_style.ilike(f"%{goal}%"), 1), else_=0))
                )
            cta_items = cta_query.limit(3).all()
            result["cta_templates"] = [self._serialize_knowledge_item(item) for item in cta_items]
            for item in cta_items:
                item.use_count += 1
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            # 发生异常时返回空结果，不报错
            pass
        
        return result

    # ====== 自动入库Pipeline 关键词配置 ======
    TOPIC_KEYWORDS = {
        "loan": ["贷款", "借款", "信贷", "单子", "报表", "贷"],
        "credit": ["征信", "信用", "申请", "卡"],
        "online_loan": ["网贷", "线上贷", "网上贷", "手机贷"],
        "housing_fund": ["公积金", "住房", "房贷"],
        "credit_card": ["信用卡", "卡债", "刷卡"],
        "car_loan": ["车贷", "汽车贷", "二手车"],
    }

    AUDIENCE_KEYWORDS = {
        "bad_credit": ["征信花", "黑户", "征信差", "查询次数多", "逾期", """白户"""],
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

    def _compute_content_hash(self, title: str, content: str) -> str:
        """计算内容hash用于去重"""
        text = f"{title or ''}{content or ''}".strip()
        return hashlib.md5(text.encode('utf-8')).hexdigest()

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
        sentences = re.split(r'[\n。！？!?]', content)
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
        clean = re.sub(r'\s+', ' ', content).strip()
        return clean[:200]

    def auto_ingest_from_raw(
        self,
        title: str,
        content: str,
        platform: str = "unknown",
        source_url: Optional[str] = None,
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        自动入库Pipeline：接收原始内容，清洗去重，结构化抽取，直接入知识库（跳过收件箱审批）
        
        Args:
            title: 内容标题
            content: 原始内容
            platform: 来源平台
            source_url: 来源URL
            author: 作者
            
        Returns:
            {
                "success": bool,
                "knowledge_id": int or None,
                "message": str,
                "extracted_fields": dict or None
            }
        """
        try:
            # 1. 计算content_hash用于去重
            content_hash = self._compute_content_hash(title, content)
            
            # 2. 检查是否已存在（基于标题+内容匹配）
            existing = self.db.query(MvpKnowledgeItem).filter(
                MvpKnowledgeItem.title == title,
                MvpKnowledgeItem.content == content
            ).first()
            if existing:
                return {
                    "success": False,
                    "knowledge_id": existing.id,
                    "message": "内容已存在，跳过重复入库",
                    "extracted_fields": None
                }
            
            # 3. 结构化字段抽取（基于规则+关键词）
            full_text = f"{title or ''} {content or ''}"
            extracted = {
                "topic": self._extract_topic(full_text),
                "audience": self._extract_audience(full_text),
                "content_type": self._extract_content_type(full_text),
                "opening_type": self._extract_opening_type(content),
                "hook_sentence": self._extract_hook_sentence(content),
                "cta_style": self._extract_cta_style(content),
                "risk_level": self._extract_risk_level(full_text),
                "summary": self._extract_summary(content),
            }
            
            # 4. 推断分类
            category = self._infer_category(content)
            
            # 5. 推断分库类型和层级
            library_type = self._infer_library_type(category, extracted["content_type"])
            layer = self._infer_layer(library_type, extracted["content_type"])
            
            # 6. 创建知识条目并入库
            knowledge = MvpKnowledgeItem(
                title=title[:200] if title else "未命名内容",
                content=content or "",
                category=category,
                platform=platform,
                audience=extracted["audience"],
                topic=extracted["topic"],
                content_type=extracted["content_type"],
                opening_type=extracted["opening_type"],
                hook_sentence=extracted["hook_sentence"],
                cta_style=extracted["cta_style"],
                risk_level=extracted["risk_level"],
                summary=extracted["summary"],
                library_type=library_type,
                layer=layer,
                source_url=source_url,
                author=author,
            )
            self.db.add(knowledge)
            self.db.commit()
            self.db.refresh(knowledge)
            
            # 7. 异步切块+向量化 (在同步上下文中启动)
            try:
                import asyncio
                from app.services.chunking_service import get_chunking_service
                chunking = get_chunking_service(self.db)
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在已有事件循环中，创建任务
                    asyncio.ensure_future(
                        chunking.process_and_store_chunks(knowledge.id, embedding_model="volcano")
                    )
                else:
                    loop.run_until_complete(
                        chunking.process_and_store_chunks(knowledge.id, embedding_model="volcano")
                    )
            except Exception as e:
                logger.warning(f"切块向量化失败(不影响入库): {e}")
            
            return {
                "success": True,
                "knowledge_id": knowledge.id,
                "message": "内容已成功入库",
                "extracted_fields": extracted
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "knowledge_id": None,
                "message": f"入库失败: {str(e)}",
                "extracted_fields": None
            }

    def auto_ingest_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量自动入库Pipeline
        
        Args:
            items: 包含 {title, content, platform, source_url, author} 的字典列表
            
        Returns:
            {
                "total": int,
                "success_count": int,
                "failed_count": int,
                "results": List[dict]
            }
        """
        results = []
        success_count = 0
        
        for item in items:
            result = self.auto_ingest_from_raw(
                title=item.get("title", ""),
                content=item.get("content", ""),
                platform=item.get("platform", "unknown"),
                source_url=item.get("source_url"),
                author=item.get("author")
            )
            results.append(result)
            if result["success"]:
                success_count += 1
        
        return {
            "total": len(items),
            "success_count": success_count,
            "failed_count": len(items) - success_count,
            "results": results
        }

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
        """升级版: 使用混合检索从多个分库召回知识
        
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
            # 1. 爆款内容库召回 3~5条
            hot_results = await hybrid.search(
                query=query,
                library_type="hot_content",
                platform=platform or None,
                audience=audience or None,
                topic=topic or None,
                top_k=5,
                embedding_model=embedding_model,
            )
            result["hot_content"] = [r.to_dict() for r in hot_results]
            
            # 2. 人群洞察库召回 2~3条
            audience_results = await hybrid.search(
                query=audience or query,
                library_type="audience_profile",
                audience=audience or None,
                top_k=3,
                embedding_model=embedding_model,
            )
            result["audience_insight"] = [r.to_dict() for r in audience_results]
            
            # 3. 平台规则库召回 3~5条
            platform_results = await hybrid.search(
                query=platform or query,
                library_type="platform_rules",
                platform=platform or None,
                top_k=5,
                embedding_model=embedding_model,
            )
            result["platform_rules"] = [r.to_dict() for r in platform_results]
            
            # 4. 审核规则库召回 3~5条
            risk_results = await hybrid.search(
                query="风险 合规 敏感词",
                library_type="compliance_rules",
                top_k=5,
                embedding_model=embedding_model,
            )
            result["risk_rules"] = [r.to_dict() for r in risk_results]
            
            # 5. 账号语气库召回 1条
            tone_results = await hybrid.search(
                query=f"{platform} {account_type} 语气",
                library_type="account_positioning",
                platform=platform or None,
                top_k=1,
                embedding_model=embedding_model,
            )
            if tone_results:
                result["tone_template"] = tone_results[0].to_dict()
            
            # 6. CTA模板库召回 2~3条
            cta_results = await hybrid.search(
                query=goal or "转化",
                library_type="prompt_templates",
                top_k=3,
                embedding_model=embedding_model,
            )
            result["cta_templates"] = [r.to_dict() for r in cta_results]
            
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
                self.db.query(MvpKnowledgeItem).filter(
                    MvpKnowledgeItem.id == kid
                ).update({MvpKnowledgeItem.use_count: MvpKnowledgeItem.use_count + 1})
            except:
                pass
        self.db.commit()
        
        return result
