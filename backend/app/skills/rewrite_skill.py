"""AI改写技能 - 封装 mvp_rewrite_service"""

import logging

from app.skills import SkillRegistry
from app.skills.base_skill import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


@SkillRegistry.register
class RewriteSkill(BaseSkill):
    """AI内容改写技能"""

    name = "rewrite"
    version = "1.0.0"
    description = "基于知识库上下文进行AI内容改写，生成多版本"
    timeout_seconds = 180
    max_retries = 2

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        封装 MvpRewriteService.rewrite_hot 方法

        注意: MvpRewriteService.rewrite_hot 接收 material_id 参数，
        需要先有素材入库才能调用。此Skill也可直接调用AI进行改写。

        输入: context.input_data 包含:
            - material_id: int, 素材ID（优先使用）
            - normalized_content: dict, 标准化内容
            - knowledge_results: list, 知识检索结果（可选）
        """
        from app.core.database import SessionLocal
        from app.services.ai_service import AIService
        from app.services.mvp_rewrite_service import MvpRewriteService

        db = SessionLocal()
        try:
            material_id = context.input_data.get("material_id")

            if material_id:
                # 使用已有素材进行仿写
                service = MvpRewriteService(db)
                # 注意: rewrite_hot 是同步方法，内部处理了异步调用
                rewrite_result = service.rewrite_hot(material_id)

                return SkillResult(
                    success=True,
                    data={
                        **context.input_data,
                        "rewrite_result": (
                            rewrite_result if isinstance(rewrite_result, dict) else {"content": str(rewrite_result)}
                        ),
                        "rewritten": True,
                    },
                )
            else:
                # 没有素材ID时，直接使用AI服务进行改写
                content = context.input_data.get("normalized_content", context.input_data)
                knowledge_results = context.input_data.get("knowledge_results", [])

                title = content.get("title", "")
                body = content.get("content", content.get("snippet", ""))

                # 构建知识上下文
                knowledge_context = ""
                if knowledge_results:
                    knowledge_context = "\n\n参考知识：\n" + "\n".join(
                        [f"- {k.get('title', '')}: {k.get('content', '')[:200]}" for k in knowledge_results[:3]]
                    )

                ai_service = AIService(db)

                prompt = f"""请基于以下原始内容进行改写，生成3个不同风格的版本。

原标题：{title}
原内容：{body[:1000] if body else ''}
{knowledge_context}

请返回JSON格式：
{{
    "versions": [
        {{"title": "版本1标题", "text": "版本1内容", "style_label": "版本1风格"}},
        {{"title": "版本2标题", "text": "版本2内容", "style_label": "版本2风格"}},
        {{"title": "版本3标题", "text": "版本3内容", "style_label": "版本3风格"}}
    ]
}}"""

                raw_response = await ai_service.call_llm(
                    prompt=prompt,
                    system_prompt="你是爆款内容仿写专家，请生成多风格仿写版本。",
                    use_cloud=True,
                    max_tokens=1500,
                )

                # 解析结果
                rewrite_result = self._parse_rewrite_result(raw_response)

                return SkillResult(
                    success=True,
                    data={
                        **context.input_data,
                        "rewrite_result": rewrite_result,
                        "rewritten": True,
                    },
                )
        except Exception as e:
            logger.error(f"AI改写失败: {e}")
            return SkillResult(success=False, data={}, error=str(e))
        finally:
            db.close()

    def _parse_rewrite_result(self, raw_response: str) -> dict:
        """解析AI返回的改写结果"""
        import json

        try:
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = raw_response[start:end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        # 返回原始响应作为内容
        return {"versions": [{"title": "AI改写版本", "text": raw_response[:500], "style_label": "默认"}]}
