"""分类打标技能"""

import json
import logging

from app.skills import SkillRegistry
from app.skills.base_skill import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


@SkillRegistry.register
class ClassifySkill(BaseSkill):
    """内容分类打标技能"""

    name = "classify"
    version = "1.0.0"
    description = "对内容进行分类和标签标注"

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        封装 AIService.call_llm 方法进行分类

        输入: context.input_data 包含:
            - normalized_content: dict, 标准化内容
        """
        from app.core.database import SessionLocal
        from app.services.ai_service import AIService

        db = SessionLocal()
        try:
            content = context.input_data.get("normalized_content", {})
            title = content.get("title", "")
            body = content.get("content", content.get("snippet", ""))

            ai_service = AIService(db)

            # 构建分类提示词
            prompt = f"""请对以下内容进行分类打标，返回JSON格式。

标题：{title}
内容：{body[:500] if body else ''}

请返回JSON格式，包含以下字段：
- category: 内容分类（如：贷款知识、行业案例、风险提示、平台策略、通用知识）
- tags: 标签列表（最多5个）
- topic: 主题关键词
- audience: 目标人群

只返回JSON，不要其他说明。"""

            # 调用AI服务进行分类
            raw_response = await ai_service.call_llm(
                prompt=prompt, system_prompt="你是内容分类专家，请准确分析内容并返回JSON格式结果。", use_cloud=True
            )

            # 解析JSON响应
            classification = self._parse_classification(raw_response)

            return SkillResult(
                success=True,
                data={
                    **context.input_data,
                    "classification": classification,
                    "classified": True,
                },
            )
        except Exception as e:
            logger.warning(f"分类失败，继续流水线: {e}")
            # 分类失败不阻断流水线
            return SkillResult(
                success=True,
                data={**context.input_data, "classified": False, "classify_error": str(e)},
            )
        finally:
            db.close()

    def _parse_classification(self, raw_response: str) -> dict:
        """解析AI返回的分类结果"""
        try:
            # 尝试提取JSON部分
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = raw_response[start:end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        # 返回默认分类
        return {"category": "通用知识", "tags": [], "topic": "", "audience": ""}
