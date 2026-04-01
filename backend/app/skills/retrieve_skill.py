"""知识检索技能 - 封装知识库检索"""

import logging

from app.skills import SkillRegistry
from app.skills.base_skill import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


@SkillRegistry.register
class RetrieveSkill(BaseSkill):
    """知识库检索技能"""

    name = "knowledge_retrieve"
    version = "1.0.0"
    description = "从知识库中检索相关内容"
    timeout_seconds = 30

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        封装 MvpKnowledgeService.search_knowledge 方法

        输入: context.input_data 包含:
            - query: str, 检索查询词
            - normalized_content: dict, 可从中提取标题作为查询词
            - platform: str, 平台过滤（可选）
            - audience: str, 人群过滤（可选）
            - top_k: int, 返回条数（默认5）
        """
        from app.core.database import SessionLocal
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = SessionLocal()
        try:
            service = MvpKnowledgeService(db)

            # 获取查询词
            query = context.input_data.get("query", "")
            if not query:
                content = context.input_data.get("normalized_content", {})
                query = content.get("title", content.get("keyword", ""))

            top_k = context.input_data.get("top_k", 5)
            platform = context.input_data.get("platform")
            audience = context.input_data.get("audience")

            # 调用知识库检索
            # 注意: search_knowledge 是同步方法
            results = service.search_knowledge(query=query, platform=platform, audience=audience, limit=top_k)

            # 序列化结果
            serialized_results = []
            for item in results:
                serialized_results.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "content": item.content[:500] if item.content else "",
                        "category": item.category,
                        "platform": item.platform,
                        "audience": item.audience,
                        "topic": getattr(item, "topic", None),
                    }
                )

            return SkillResult(
                success=True,
                data={
                    **context.input_data,
                    "knowledge_results": serialized_results,
                    "knowledge_retrieved": True,
                },
            )
        except Exception as e:
            logger.warning(f"知识检索失败，继续流水线: {e}")
            # 检索失败不阻断流水线
            return SkillResult(
                success=True,
                data={**context.input_data, "knowledge_results": [], "knowledge_retrieved": False},
            )
        finally:
            db.close()
