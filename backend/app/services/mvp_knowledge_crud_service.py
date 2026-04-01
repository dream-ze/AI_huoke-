"""MVP 知识库 CRUD 服务 - 创建、读取、更新、删除操作"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

from app.core.database import SessionLocal
from app.models.models import MvpKnowledgeItem, MvpMaterialItem, MvpMaterialTagRel, MvpTag
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# 分库类型定义
LIBRARY_TYPES = {
    "hot_content": "爆款内容",
    "industry_phrases": "行业话术",
    "platform_rules": "平台规则",
    "audience_profile": "人群画像",
    "account_positioning": "账号定位",
    "prompt_templates": "提示词模板",
    "compliance_rules": "合规规则",
}


class MvpKnowledgeCrudService:
    """知识库CRUD服务 - 负责创建、读取、更新、删除操作"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 读取操作 ====================

    def list_knowledge(
        self,
        page=1,
        size=20,
        platform=None,
        audience=None,
        style=None,
        category=None,
        keyword=None,
        topic=None,
        content_type=None,
        library_type=None,
    ):
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
                q = q.filter(
                    or_(MvpKnowledgeItem.title.ilike(f"%{keyword}%"), MvpKnowledgeItem.content.ilike(f"%{keyword}%"))
                )
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

    def get_categories(self) -> list:
        """获取所有分类"""
        try:
            categories = self.db.query(MvpKnowledgeItem.category).distinct().all()
            return [c[0] for c in categories if c[0]]
        except Exception:
            return []

    def get_library_stats(self) -> List[dict]:
        """获取各分库统计"""
        results = (
            self.db.query(
                MvpKnowledgeItem.library_type,
                func.count(MvpKnowledgeItem.id).label("count"),
                func.max(MvpKnowledgeItem.updated_at).label("last_updated"),
            )
            .group_by(MvpKnowledgeItem.library_type)
            .all()
        )

        stats = []
        for lib_type, label in LIBRARY_TYPES.items():
            row = next((r for r in results if r.library_type == lib_type), None)
            stats.append(
                {
                    "library_type": lib_type,
                    "label": label,
                    "count": row.count if row else 0,
                    "last_updated": str(row.last_updated) if row and row.last_updated else None,
                }
            )
        return stats

    def list_by_library(self, library_type: str, page: int = 1, size: int = 20, keyword: str = "") -> dict:
        """按分库类型列出知识条目"""
        query = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.library_type == library_type)
        if keyword:
            query = query.filter(
                MvpKnowledgeItem.title.ilike(f"%{keyword}%") | MvpKnowledgeItem.content.ilike(f"%{keyword}%")
            )
        total = query.count()
        items = query.order_by(MvpKnowledgeItem.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return {"items": items, "total": total, "page": page, "size": size}

    # ==================== 创建操作 ====================

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

    def build_from_material(self, material_id: int):
        """从素材构建结构化知识"""
        try:
            material = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if not material:
                raise ValueError("素材不存在")

            # 检查是否已有知识条目
            existing = (
                self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.source_material_id == material_id).first()
            )
            if existing:
                # 更新而非重复创建
                existing.title = f"知识: {material.title[:100]}"
                existing.content = self._extract_knowledge(material.content)
                existing.platform = material.platform
                self.db.commit()
                return existing

            # 从标签推断人群和风格
            tags = (
                self.db.query(MvpTag).join(MvpMaterialTagRel).filter(MvpMaterialTagRel.material_id == material_id).all()
            )
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

    def batch_build_from_materials(self, material_ids: List[int]) -> dict:
        """批量从素材构建知识，单条失败不影响整批

        Args:
            material_ids: 素材ID列表

        Returns:
            {
                "total": int,
                "success_count": int,
                "failed_count": int,
                "details": List[dict]
            }
        """
        results = []

        for mid in material_ids:
            try:
                knowledge = self.build_from_material(mid)
                results.append({"material_id": mid, "success": True, "knowledge_id": knowledge.id, "error": None})
            except Exception as e:
                # 单条失败记录错误，继续处理下一条
                results.append({"material_id": mid, "success": False, "knowledge_id": None, "error": str(e)})
                # 确保session状态干净，继续下一条
                try:
                    self.db.rollback()
                except Exception as e:
                    logger.warning(f"Database rollback failed: {e}")

        success_count = sum(1 for r in results if r["success"])
        return {
            "total": len(material_ids),
            "success_count": success_count,
            "failed_count": len(material_ids) - success_count,
            "details": results,
        }

    def auto_ingest_from_raw(
        self,
        title: str,
        content: str,
        platform: str = "unknown",
        source_url: Optional[str] = None,
        author: Optional[str] = None,
        extracted_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        自动入库Pipeline：接收原始内容，清洗去重，结构化抽取，直接入知识库（跳过收件箱审批）

        Args:
            title: 内容标题
            content: 原始内容
            platform: 来源平台
            source_url: 来源URL
            author: 作者
            extracted_fields: 预提取的结构化字段（可选，由搜索服务提供）

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
            existing = (
                self.db.query(MvpKnowledgeItem)
                .filter(MvpKnowledgeItem.title == title, MvpKnowledgeItem.content == content)
                .first()
            )
            if existing:
                return {
                    "success": False,
                    "knowledge_id": existing.id,
                    "message": "内容已存在，跳过重复入库",
                    "extracted_fields": None,
                }

            # 3. 使用传入的提取字段或自行推断
            if extracted_fields is None:
                extracted_fields = {}

            # 4. 推断分类
            category = self._infer_category(content)

            # 5. 推断分库类型和层级
            content_type = extracted_fields.get("content_type", "")
            library_type = self._infer_library_type(category, content_type)
            layer = self._infer_layer(library_type, content_type)

            # 6. 创建知识条目并入库
            knowledge = MvpKnowledgeItem(
                title=title[:200] if title else "未命名内容",
                content=content or "",
                category=category,
                platform=platform,
                audience=extracted_fields.get("audience"),
                topic=extracted_fields.get("topic"),
                content_type=content_type,
                opening_type=extracted_fields.get("opening_type"),
                hook_sentence=extracted_fields.get("hook_sentence"),
                cta_style=extracted_fields.get("cta_style"),
                risk_level=extracted_fields.get("risk_level"),
                summary=extracted_fields.get("summary"),
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

                async def run_chunking_task():
                    task_db = SessionLocal()
                    try:
                        chunking = get_chunking_service(task_db)
                        await chunking.process_and_store_chunks(knowledge.id, embedding_model="volcano")
                    finally:
                        task_db.close()

                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    asyncio.run(run_chunking_task())
                else:
                    loop.create_task(run_chunking_task())
            except Exception as e:
                logger.warning(f"切块向量化失败(不影响入库): {e}")

            return {
                "success": True,
                "knowledge_id": knowledge.id,
                "message": "内容已成功入库",
                "extracted_fields": extracted_fields,
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "knowledge_id": None, "message": f"入库失败: {str(e)}", "extracted_fields": None}

    def auto_ingest_batch(
        self, items: List[Dict[str, Any]], extracted_fields_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        批量自动入库Pipeline

        Args:
            items: 包含 {title, content, platform, source_url, author} 的字典列表
            extracted_fields_list: 预提取的结构化字段列表（可选）

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

        for i, item in enumerate(items):
            extracted = None
            if extracted_fields_list and i < len(extracted_fields_list):
                extracted = extracted_fields_list[i]

            result = self.auto_ingest_from_raw(
                title=item.get("title", ""),
                content=item.get("content", ""),
                platform=item.get("platform", "unknown"),
                source_url=item.get("source_url"),
                author=item.get("author"),
                extracted_fields=extracted,
            )
            results.append(result)
            if result["success"]:
                success_count += 1

        return {
            "total": len(items),
            "success_count": success_count,
            "failed_count": len(items) - success_count,
            "results": results,
        }

    # ==================== 更新操作 ====================

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

    # ==================== 删除操作 ====================

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

    # ==================== 辅助方法 ====================

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

    def auto_classify_library_type(self, knowledge_item) -> str:
        """根据内容自动分类到分库"""
        content = (knowledge_item.content or "").lower()
        title = (knowledge_item.title or "").lower()
        text = f"{title} {content}"

        # 规则分类
        if any(kw in text for kw in ["合规", "风险", "违规", "法律", "监管"]):
            return "compliance_rules"
        if any(kw in text for kw in ["模板", "提示词", "prompt"]):
            return "prompt_templates"
        if any(kw in text for kw in ["规则", "规范", "审核", "社区公约"]):
            return "platform_rules"
        if any(kw in text for kw in ["人群", "用户画像", "受众", "消费者"]):
            return "audience_profile"
        if any(kw in text for kw in ["定位", "人设", "账号"]):
            return "account_positioning"
        if any(kw in text for kw in ["话术", "金句", "行业"]):
            return "industry_phrases"
        return "hot_content"

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

    def _compute_content_hash(self, title: str, content: str) -> str:
        """计算内容hash用于去重"""
        text = f"{title or ''}{content or ''}".strip()
        return hashlib.md5(text.encode("utf-8")).hexdigest()
