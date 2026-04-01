"""入知识库技能 - 封装 mvp_knowledge_service 的入库操作"""

import logging

from app.skills import SkillRegistry
from app.skills.base_skill import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


@SkillRegistry.register
class KnowledgeIngestSkill(BaseSkill):
    """内容入知识库技能"""

    name = "knowledge_ingest"
    version = "1.0.0"
    description = "将内容写入知识库并向量化"
    timeout_seconds = 120

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        封装 MvpKnowledgeService.create_knowledge 方法

        输入: context.input_data 包含:
            - normalized_content: dict, 标准化内容
            - classification: dict, 分类结果（可选）
        """
        from app.core.database import SessionLocal
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = SessionLocal()
        try:
            service = MvpKnowledgeService(db)
            content = context.input_data.get("normalized_content", context.input_data)
            classification = context.input_data.get("classification", {})

            # 准备入库数据
            title = content.get("title", "")
            body = content.get("content", content.get("snippet", ""))
            platform = content.get("source_platform", content.get("platform", ""))

            # 从分类结果中提取维度
            category = classification.get("category", "通用知识") if classification else "通用知识"
            audience = classification.get("audience", "") if classification else ""
            topic = classification.get("topic", "") if classification else ""
            tags = classification.get("tags", []) if classification else []

            # 调用知识库服务入库（create_knowledge 是同步方法，使用 to_thread 避免阻塞）
            import asyncio

            knowledge_item = await asyncio.to_thread(
                service.create_knowledge,
                {
                    "title": title,
                    "content": body,
                    "category": category,
                    "platform": platform,
                    "audience": audience,
                    "style": None,  # 可后续补充
                },
            )

            # 更新 topic 和 tags（如果模型支持）
            if hasattr(knowledge_item, "topic") and topic:
                knowledge_item.topic = topic
            if hasattr(knowledge_item, "tags") and tags:
                knowledge_item.tags = tags
            db.commit()

            return SkillResult(
                success=True,
                data={
                    **context.input_data,
                    "knowledge_item_id": knowledge_item.id if knowledge_item else None,
                    "knowledge_ingested": True,
                },
            )
        except Exception as e:
            logger.error(f"入库知识库失败: {e}")
            return SkillResult(success=False, data={}, error=str(e))
        finally:
            db.close()
