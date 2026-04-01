"""评论/私信回复建议技能"""

import logging

from app.skills import SkillRegistry
from app.skills.base_skill import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


@SkillRegistry.register
class ReplySkill(BaseSkill):
    """评论/私信回复建议技能

    基于 PRD 3.4.2 实现：
    1. 意图识别（投诉、高意向咨询、普通咨询、闲聊）
    2. 知识库检索
    3. 生成回复建议
    4. 判断是否需要人工接管
    """

    name = "reply_suggestion"
    version = "1.0.0"
    description = "基于知识库生成评论/私信回复建议"

    async def execute(self, context: SkillContext) -> SkillResult:
        """执行回复建议生成

        输入: context.input_data 包含:
            - message: str, 用户消息内容
            - platform: str, 平台标识 (默认 xiaohongshu)
            - history: list, 对话历史 (可选)

        输出: SkillResult.data 包含:
            - intent: str, 意图类型
            - confidence: float, 置信度
            - suggestions: list, 回复建议列表
            - should_takeover: bool, 是否需要人工接管
            - takeover_reason: str, 接管原因 (可选)
        """
        from app.core.database import SessionLocal
        from app.services.ai_service import AIService
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        input_data = context.input_data
        user_message = input_data.get("message", "")
        platform = input_data.get("platform", "xiaohongshu")
        conversation_history = input_data.get("history", [])

        db = SessionLocal()
        try:
            # 1. 意图识别
            intent = await self._identify_intent(user_message)

            # 2. 知识库检索
            knowledge_service = MvpKnowledgeService(db)
            knowledge_results = knowledge_service.search_knowledge(
                query=user_message,
                platform=platform,
                limit=3,
            )

            # 转换 ORM 对象为字典
            knowledge_context = []
            for item in knowledge_results:
                knowledge_context.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "content": item.content,
                        "category": item.category,
                    }
                )

            # 3. 生成回复建议
            ai_service = AIService(db)
            suggestions = await self._generate_suggestions(
                ai_service=ai_service,
                user_message=user_message,
                intent=intent,
                knowledge_context=knowledge_context,
                conversation_history=conversation_history,
                platform=platform,
                user_id=context.user_id,
            )

            # 4. 判断是否需要人工接管
            should_takeover = self._check_takeover_conditions(intent, user_message)

            return SkillResult(
                success=True,
                data={
                    "intent": intent["type"],
                    "confidence": intent["confidence"],
                    "suggestions": suggestions,
                    "should_takeover": should_takeover,
                    "takeover_reason": intent.get("takeover_reason"),
                    "knowledge_used": len(knowledge_context),
                },
            )
        except Exception as e:
            logger.error(f"[ReplySkill] 生成回复建议失败: {e}")
            return SkillResult(
                success=False,
                data={},
                error=str(e),
            )
        finally:
            db.close()

    async def _identify_intent(self, message: str) -> dict:
        """意图识别

        返回:
            - type: 意图类型 (complaint, high_intent_inquiry, general_inquiry, casual)
            - confidence: 置信度 0-1
            - takeover_reason: 接管原因 (可选)
        """
        # 风险关键词 - 检测投诉/负面内容
        risk_keywords = ["投诉", "骗子", "举报", "曝光", "黑心", "诈骗", "套路", "被骗"]

        # 高意向关键词 - 检测潜在客户
        high_intent_keywords = [
            "利率",
            "额度",
            "征信",
            "放款",
            "申请",
            "多久",
            "条件",
            "利息",
            "通过率",
            "审批",
            "资质",
            "能贷",
            "多少钱",
        ]

        # 检测投诉/负面内容
        if any(kw in message for kw in risk_keywords):
            return {"type": "complaint", "confidence": 0.9, "takeover_reason": "检测到投诉/负面内容，建议人工介入处理"}

        # 检测高意向咨询
        if any(kw in message for kw in high_intent_keywords):
            return {"type": "high_intent_inquiry", "confidence": 0.85}

        # 检测普通咨询
        if "?" in message or "？" in message or "吗" in message or "怎么" in message:
            return {"type": "general_inquiry", "confidence": 0.7}

        # 默认为闲聊
        return {"type": "casual", "confidence": 0.6}

    async def _generate_suggestions(
        self,
        ai_service,
        user_message: str,
        intent: dict,
        knowledge_context: list,
        conversation_history: list,
        platform: str,
        user_id: int,
    ) -> list:
        """生成回复建议"""

        # 构建知识库上下文
        context_text = ""
        if knowledge_context:
            context_parts = []
            for item in knowledge_context[:3]:
                content = item.get("content", "")[:200]
                if content:
                    context_parts.append(f"- {content}")
            context_text = "\n".join(context_parts)
        else:
            context_text = "无相关知识库内容"

        # 根据平台调整风格
        platform_style = {
            "xiaohongshu": "小红书风格：亲切、口语化、可适当使用emoji",
            "douyin": "抖音风格：简短有力、节奏感强",
            "zhihu": "知乎风格：专业、逻辑清晰",
        }.get(platform, "亲切友好风格")

        prompt = f"""用户消息：{user_message}
用户意图：{intent['type']}（置信度: {intent['confidence']}）
平台风格：{platform_style}
相关知识：
{context_text}

请生成3个回复建议，要求：
1. 专业友好，不要过度承诺
2. 引导用户提供更多信息或私信咨询
3. 符合平台调性，自然不生硬
4. 不使用"100%下款"、"一定放款"等违规承诺词语
5. 针对用户意图给出合适的回复

输出格式（严格按此格式）：
回复1：[第一个建议]
回复2：[第二个建议]
回复3：[第三个建议]
"""

        try:
            response = await ai_service.call_llm(
                prompt=prompt,
                system_prompt="你是一位专业的社交媒体运营客服，擅长生成友好、专业、合规的回复。",
                use_cloud=True,
                user_id=user_id,
                scene="reply_suggestion",
            )

            # 解析回复建议
            suggestions = []
            for line in response.split("\n"):
                line = line.strip()
                if line.startswith("回复") and "：" in line:
                    suggestion = line.split("：", 1)[-1].strip()
                    if suggestion:
                        suggestions.append(suggestion)

            # 确保至少有一个建议
            if not suggestions:
                suggestions = ["感谢您的关注，详情可以私信我了解~"]

            return suggestions[:3]

        except Exception as e:
            logger.warning(f"[ReplySkill] AI生成建议失败，使用默认回复: {e}")
            return ["感谢您的关注，详情可以私信我了解~"]

    def _check_takeover_conditions(self, intent: dict, message: str) -> bool:
        """判断是否需要人工接管

        接管条件：
        1. 检测到投诉/负面内容
        2. 高意向咨询且置信度 > 0.8
        3. 消息过长（> 200字）可能包含复杂问题
        """
        # 投诉类型直接接管
        if intent["type"] == "complaint":
            return True

        # 高意向咨询且置信度高
        if intent["type"] == "high_intent_inquiry" and intent["confidence"] > 0.8:
            return True

        # 消息过长
        if len(message) > 200:
            return True

        return False
