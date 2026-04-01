"""MVP改写服务 - 处理内容改写和口吻调整

包含内容改写、口吻调整/模板应用、合规版本生成、风格转换等功能。
"""

import logging
from typing import List

from app.schemas.generate_schema import FullPipelineRequest, VersionItem
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MvpRewriteService:
    """MVP改写服务 - 处理内容改写和风格转换"""

    # 映射表（与核心服务保持一致）
    ACCOUNT_TYPE_MAP = {
        "loan_advisor": "助贷顾问",
        "agent": "贷款中介",
        "knowledge_account": "金融科普号",
    }

    AUDIENCE_MAP = {
        "bad_credit": "征信花的人",
        "high_debt": "负债高的人",
        "office_worker": "上班族",
        "self_employed": "个体户",
    }

    TOPIC_MAP = {
        "loan": "贷款",
        "credit": "征信",
        "online_loan": "网贷",
        "housing_fund": "公积金",
    }

    GOAL_MAP = {
        "private_message": "引导私信",
        "consultation": "引导咨询",
        "conversion": "促进转化",
    }

    PLATFORM_STYLE_MAP = {
        "xiaohongshu": "小红书风格：口语化、emoji丰富、种草感、真实分享调调",
        "douyin": "抖音风格：短句为主、节奏感强、开头3秒必须抓人、口播化",
        "zhihu": "知乎风格：专业理性、逻辑清晰、有分析过程、数据支撑",
    }

    # 语气风格映射表
    TONE_MAP = {
        "professional": "专业严谨、逻辑清晰",
        "friendly": "亲切友好、平易近人",
        "humorous": "幽默风趣、轻松活泼",
        "empathetic": "共情走心、温暖感人",
        "urgent": "紧迫感强、催促行动",
    }

    def __init__(self, db: Session):
        self.db = db

    async def _generate_rewrite_base(
        self, request: FullPipelineRequest, context_str: str, extra_requirements: str, use_cloud: bool
    ) -> str:
        """
        Step 3: 基于知识库上下文，生成高质量基础改写版
        这是多风格版本的基础
        """
        try:
            from app.services.ai_service import AIService

            ai_svc = AIService(self.db)

            audience_desc = self.AUDIENCE_MAP.get(request.audience, request.audience)
            topic_desc = self.TOPIC_MAP.get(request.topic, request.topic)
            goal_desc = self.GOAL_MAP.get(request.goal, request.goal)
            role_name = self.ACCOUNT_TYPE_MAP.get(request.account_type, "助贷顾问")
            platform_style = self.PLATFORM_STYLE_MAP.get(request.platform, "通用风格")

            # 构建语气风格描述
            tone_desc = ""
            if hasattr(request, "tone") and request.tone:
                tone_desc = self.TONE_MAP.get(request.tone, request.tone)

            system_prompt = f"""你是一位专业的{role_name}，正在为{request.platform}平台创作获客内容。
你的文案需要符合{platform_style}。
请用中文回复，确保内容合规，不使用绝对承诺词汇。"""

            prompt = f"""请基于以下知识库参考和要求，创作一篇高质量的基础文案：

【目标人群】{audience_desc}
【内容主题】{topic_desc}
【内容目标】{goal_desc}
【目标平台】{request.platform}
"""

            if tone_desc:
                prompt += f"【语气风格要求】{tone_desc}\n"

            if context_str:
                prompt += f"""
【知识库参考（仅供学习风格和要点，不要照抄）】
{context_str}
"""

            if extra_requirements:
                prompt += f"""
【额外要求】
{extra_requirements}
"""

            prompt += """
【输出要求】
请输出一篇完整的文案，包含标题和正文。
文案应具有以下特点：
1. 标题吸引人，能让目标人群想点击
2. 内容真实可信，结合实际场景
3. 结构清晰，重点突出
4. 结尾有明确的行动引导
5. 禁止使用"必过""包过""100%通过"等违规词"""

            raw_response = await ai_svc.call_llm(
                prompt=prompt, system_prompt=system_prompt, use_cloud=use_cloud, scene="generate_rewrite_base"
            )

            # 防御：LLM返回空值时使用mock内容
            if not raw_response or not raw_response.strip():
                logger.warning("[Pipeline] Step 3: LLM返回空值，使用mock内容")
                return self._mock_rewrite_base(request)

            return raw_response.strip()

        except Exception as e:
            logger.error(f"[Pipeline] Step 3 failed: 生成基础改写版失败: {e}")
            return self._mock_rewrite_base(request)

    def _mock_rewrite_base(self, request: FullPipelineRequest) -> str:
        """基础改写版的Mock内容"""
        audience_desc = self.AUDIENCE_MAP.get(request.audience, request.audience)
        topic_desc = self.TOPIC_MAP.get(request.topic, request.topic)

        return f"""【标题】{topic_desc}的正确打开方式，{audience_desc}必看！

【正文】
很多{audience_desc}朋友都在问关于{topic_desc}的问题。

今天给大家整理了一些实用建议：

1️⃣ 先了解自己的实际情况
2️⃣ 对比多家产品，选择合适的
3️⃣ 量力而行，不要盲目追求

有任何疑问，欢迎在评论区留言或私信咨询！"""

    async def _generate_style_versions(
        self, request: FullPipelineRequest, rewrite_base: str, context_str: str, use_cloud: bool
    ) -> List[VersionItem]:
        """
        Step 4: 基于基础改写版，并发生成3个风格版本（professional/casual/seeding）
        """
        version_configs = [
            ("professional", "专业型：专业、权威、数据支撑、逻辑清晰，像金融专家给建议"),
            ("casual", "口语型：口语化、亲切、接地气、像朋友聊天，短句为主"),
            ("seeding", "种草型：种草风、emoji丰富、吸引眼球、制造好奇，真实分享感"),
        ]

        # 使用 asyncio.gather 并发生成所有版本
        import asyncio

        tasks = [
            self._generate_single_style(request, rewrite_base, version_key, style_desc, use_cloud)
            for version_key, style_desc in version_configs
        ]
        versions = await asyncio.gather(*tasks)
        return list(versions)

    async def _generate_single_style(
        self, request: FullPipelineRequest, rewrite_base: str, version_key: str, style_desc: str, use_cloud: bool
    ) -> VersionItem:
        """生成单个风格版本（供并发调用）"""
        from app.services.ai_service import AIService

        ai_svc = AIService(self.db)

        try:
            prompt = self._build_style_version_prompt(
                request=request, rewrite_base=rewrite_base, version_key=version_key, style_desc=style_desc
            )
            system_prompt = self._build_system_prompt(request, version_key)

            raw_response = await ai_svc.call_llm(
                prompt=prompt, system_prompt=system_prompt, use_cloud=use_cloud, scene=f"generate_{version_key}"
            )

            # 防御：LLM返回空值时使用fallback
            if not raw_response or not raw_response.strip():
                logger.warning(f"[Pipeline] Step 4: LLM返回空值，使用fallback版本: {version_key}")
                return self._fallback_single_version(request, version_key)

            title, text = self._parse_title_text(raw_response)

            # 防御：解析结果为空时使用fallback
            if not title or not text:
                logger.warning(f"[Pipeline] Step 4: 解析结果为空，使用fallback版本: {version_key}")
                return self._fallback_single_version(request, version_key)

            return VersionItem(style=version_key, title=title, text=text)

        except Exception as e:
            logger.error(f"[Pipeline] Step 4 failed: 生成{version_key}版本失败: {e}")
            return self._fallback_single_version(request, version_key)

    def _build_style_version_prompt(
        self, request: FullPipelineRequest, rewrite_base: str, version_key: str, style_desc: str
    ) -> str:
        """构建风格版本生成提示词（基于基础改写版）"""
        audience_desc = self.AUDIENCE_MAP.get(request.audience, request.audience)
        goal_desc = self.GOAL_MAP.get(request.goal, request.goal)

        prompt = f"""请将以下基础文案改写为【{style_desc}】版本：

【基础文案】
{rewrite_base[:1000]}

【目标人群】{audience_desc}
【内容目标】{goal_desc}
【目标平台】{request.platform}

【输出要求】
请严格按以下格式输出：
【标题】（不超过20字的吸引人标题）
【正文】（正文内容，300-800字）

注意：
1. 保持原文案的核心信息和观点
2. 根据风格要求调整表达方式
3. 结尾需有引导动作（私信/评论/收藏）
4. 禁止使用"必过""包过""100%通过"等违规词"""

        return prompt

    def _build_system_prompt(self, request: FullPipelineRequest, version_key: str) -> str:
        """构建系统提示词"""
        role_name = self.ACCOUNT_TYPE_MAP.get(request.account_type, "助贷顾问")
        platform_style = self.PLATFORM_STYLE_MAP.get(request.platform, "通用风格")

        base = f"""你是一位专业的{role_name}，正在为{request.platform}平台创作获客内容。
你的文案需要符合{platform_style}。
请用中文回复，确保内容合规，不使用绝对承诺词汇。"""

        if version_key == "professional":
            base += "\n本次需要输出【专业型】内容：逻辑清晰、数据支撑、理性分析、专业术语适当使用。"
        elif version_key == "casual":
            base += "\n本次需要输出【口语型】内容：短句为主、接地气、像朋友聊天、代入感强。"
        else:  # seeding
            base += "\n本次需要输出【种草型】内容：真实分享感、emoji适当装饰、制造好奇、引导互动。"

        return base

    def _parse_title_text(self, raw_response: str) -> tuple:
        """解析LLM返回的标题和正文"""
        import re

        # 防御：空值检查
        if not raw_response or not raw_response.strip():
            logger.warning("[Pipeline] _parse_title_text: 输入为空，返回默认值")
            return "内容生成中", "正在生成中，请稍后..."

        # 尝试用正则解析【标题】和【正文】
        title_match = re.search(r"【标题】[：:]?\s*(.+?)(?=\n|【正文】|$)", raw_response, re.DOTALL)
        text_match = re.search(r"【正文】[：:]?\s*(.+)", raw_response, re.DOTALL)

        if title_match and text_match:
            title = title_match.group(1).strip()[:50]
            text = text_match.group(1).strip()
            if title and text:
                return title, text

        # Fallback：第一行作为标题，其余作为正文
        lines = raw_response.strip().split("\n")
        if len(lines) >= 2:
            title = lines[0].strip()[:50]
            text = "\n".join(lines[1:]).strip()
            if title and text:
                return title, text

        # 最终fallback：确保返回非空值
        fallback_title = "内容生成中"
        fallback_text = raw_response.strip() if raw_response.strip() else "正在生成中，请稍后..."
        return fallback_title, fallback_text

    def _fallback_single_version(self, request: FullPipelineRequest, version_key: str) -> VersionItem:
        """单个版本的fallback"""
        audience_desc = self.AUDIENCE_MAP.get(request.audience, request.audience)
        topic_desc = self.TOPIC_MAP.get(request.topic, request.topic)

        style_map = {
            "professional": (
                "专业分析",
                f"关于{topic_desc}，针对{audience_desc}群体，建议先了解自身情况，再选择合适的方案。专业建议：1. 先查询征信报告；2. 评估自身还款能力；3. 对比多家产品。有任何疑问欢迎咨询。",
            ),
            "casual": (
                "聊聊看",
                f"家人们！今天聊聊{topic_desc}这个话题～很多{audience_desc}朋友都问过我这个问题。说真的，方法很重要！记住这几点就够了：别盲目申请、先看清条件、量力而行。有问题评论区聊！",
            ),
            "seeding": (
                "亲测分享",
                f"姐妹们看过来！关于{topic_desc}，我身边好多{audience_desc}的朋友都踩过坑。今天整理了避坑指南分享给大家～记得收藏！有用的话给我点个赞呀~",
            ),
        }

        title, text = style_map.get(version_key, ("内容生成中", "正在生成中..."))
        return VersionItem(style=version_key, title=title, text=text)

    # ========== 公开API方法 ==========

    async def rewrite_content(
        self, content: str, target_style: str, platform: str = "xiaohongshu", extra_requirements: str = ""
    ) -> dict:
        """
        内容改写 - 将内容改写为指定风格

        Args:
            content: 原始内容
            target_style: 目标风格 (professional/casual/seeding)
            platform: 目标平台
            extra_requirements: 额外要求

        Returns:
            dict: 包含改写后的内容
        """
        try:
            from app.services.ai_service import AIService

            ai_svc = AIService(self.db)

            style_desc_map = {
                "professional": "专业型：专业、权威、数据支撑、逻辑清晰",
                "casual": "口语型：口语化、亲切、接地气、像朋友聊天",
                "seeding": "种草型：种草风、emoji丰富、吸引眼球、真实分享感",
            }

            style_desc = style_desc_map.get(target_style, "通用风格")
            platform_style = self.PLATFORM_STYLE_MAP.get(platform, "通用风格")

            system_prompt = f"""你是一位专业的内容创作助手。
请将内容改写为{style_desc}。
文案需要符合{platform_style}。
请用中文回复，确保内容合规。"""

            prompt = f"""请将以下内容改写为【{style_desc}】版本：

【原始内容】
{content[:1500]}

【输出要求】
请严格按以下格式输出：
【标题】（吸引人的标题）
【正文】（改写后的正文内容）

注意：
1. 保持原文的核心信息和观点
2. 根据风格要求调整表达方式
3. 禁止使用"必过""包过""100%通过"等违规词"""

            if extra_requirements:
                prompt += f"\n\n【额外要求】\n{extra_requirements}"

            raw_response = await ai_svc.call_llm(
                prompt=prompt, system_prompt=system_prompt, use_cloud=True, scene=f"rewrite_{target_style}"
            )

            title, text = self._parse_title_text(raw_response)

            return {"success": True, "title": title, "text": text, "style": target_style, "platform": platform}

        except Exception as e:
            logger.exception("内容改写失败")
            return {"success": False, "error": str(e), "title": "改写失败", "text": content}

    async def apply_tone_template(self, content: str, tone: str, platform: str = "xiaohongshu") -> dict:
        """
        应用口吻模板 - 调整内容的语气风格

        Args:
            content: 原始内容
            tone: 语气风格 (professional/friendly/humorous/empathetic/urgent)
            platform: 目标平台

        Returns:
            dict: 包含调整后的内容
        """
        try:
            from app.services.ai_service import AIService

            ai_svc = AIService(self.db)

            tone_desc = self.TONE_MAP.get(tone, tone)
            platform_style = self.PLATFORM_STYLE_MAP.get(platform, "通用风格")

            system_prompt = f"""你是一位专业的内容创作助手。
请将内容的语气调整为：{tone_desc}。
文案需要符合{platform_style}。
请用中文回复。"""

            prompt = f"""请将以下内容的语气调整为【{tone_desc}】：

【原始内容】
{content[:1500]}

【输出要求】
请严格按以下格式输出：
【标题】（吸引人的标题）
【正文】（调整语气后的正文内容）

注意：
1. 保持原文的核心信息和观点
2. 重点调整语气和表达方式，使其符合要求的风格
3. 禁止使用违规词汇"""

            raw_response = await ai_svc.call_llm(
                prompt=prompt, system_prompt=system_prompt, use_cloud=True, scene=f"apply_tone_{tone}"
            )

            title, text = self._parse_title_text(raw_response)

            return {
                "success": True,
                "title": title,
                "text": text,
                "tone": tone,
                "tone_desc": tone_desc,
                "platform": platform,
            }

        except Exception as e:
            logger.exception("应用口吻模板失败")
            return {"success": False, "error": str(e), "title": "调整失败", "text": content}

    async def generate_compliance_version(self, content: str, risk_points: list = None) -> dict:
        """
        生成合规版本 - 修复内容中的合规风险

        Args:
            content: 原始内容
            risk_points: 风险点列表

        Returns:
            dict: 包含合规修正后的内容
        """
        try:
            from app.services.ai_service import AIService

            ai_svc = AIService(self.db)

            risk_info = ""
            if risk_points:
                risk_info = "\n".join([f"- {rp.get('keyword', '')}: {rp.get('reason', '')}" for rp in risk_points])

            system_prompt = """你是一位专业的内容合规审核助手。
请修复内容中的合规风险，确保内容符合金融监管要求。
禁止使用"必过""包过""100%通过""零门槛"等违规词汇。
请用中文回复。"""

            prompt = f"""请修复以下内容的合规风险：

【原始内容】
{content[:1500]}
"""

            if risk_info:
                prompt += f"""
【已知风险点】
{risk_info}
"""

            prompt += """
【输出要求】
请严格按以下格式输出：
【标题】（合规的标题）
【正文】（合规修正后的正文内容）

注意：
1. 保持原文的核心信息和观点
2. 替换或删除违规词汇和表达
3. 确保内容真实可信，不使用绝对承诺
4. 保留内容的可读性和吸引力"""

            raw_response = await ai_svc.call_llm(
                prompt=prompt, system_prompt=system_prompt, use_cloud=True, scene="compliance_rewrite"
            )

            title, text = self._parse_title_text(raw_response)

            return {
                "success": True,
                "title": title,
                "text": text,
                "original_content": content,
                "risk_points_fixed": len(risk_points) if risk_points else 0,
            }

        except Exception as e:
            logger.exception("生成合规版本失败")
            return {"success": False, "error": str(e), "title": "合规修正失败", "text": content}

    async def convert_style(self, content: str, source_platform: str, target_platform: str) -> dict:
        """
        平台风格转换 - 将内容从一个平台风格转换为另一个平台风格

        Args:
            content: 原始内容
            source_platform: 源平台
            target_platform: 目标平台

        Returns:
            dict: 包含转换后的内容
        """
        try:
            from app.services.ai_service import AIService

            ai_svc = AIService(self.db)

            source_style = self.PLATFORM_STYLE_MAP.get(source_platform, "通用风格")
            target_style = self.PLATFORM_STYLE_MAP.get(target_platform, "通用风格")

            system_prompt = f"""你是一位专业的跨平台内容创作助手。
请将内容从{source_platform}风格转换为{target_platform}风格。
请用中文回复，确保内容合规。"""

            prompt = f"""请将以下内容从【{source_style}】转换为【{target_style}】：

【原始内容】
{content[:1500]}

【输出要求】
请严格按以下格式输出：
【标题】（适合目标平台的标题）
【正文】（转换后的正文内容）

注意：
1. 保持原文的核心信息和观点
2. 根据目标平台的调性调整表达方式
3. 目标平台特点：{target_style}
4. 禁止使用违规词汇"""

            raw_response = await ai_svc.call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                use_cloud=True,
                scene=f"convert_{source_platform}_to_{target_platform}",
            )

            title, text = self._parse_title_text(raw_response)

            return {
                "success": True,
                "title": title,
                "text": text,
                "source_platform": source_platform,
                "target_platform": target_platform,
            }

        except Exception as e:
            logger.exception("平台风格转换失败")
            return {"success": False, "error": str(e), "title": "转换失败", "text": content}
