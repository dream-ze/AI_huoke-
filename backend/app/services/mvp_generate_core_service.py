"""MVP生成服务 - 核心生成逻辑

包含多版本生成、LLM调用封装、Prompt构建、生成结果处理和存储、知识增强生成等功能。
"""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from app.models.models import MvpGenerationResult, MvpInboxItem, MvpMaterialItem
from app.schemas.generate_schema import (
    ComplianceResult,
    ConstrainedGenerateRequest,
    ConstrainedGenerateResponse,
    FullPipelineRequest,
    RiskPoint,
    StructuredGenerateOutput,
    VersionItem,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MvpGenerateCoreService:
    """MVP生成核心服务 - 处理内容生成的核心逻辑"""

    # 映射表
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
        self._prompts_dir = os.path.join(os.path.dirname(__file__), "..", "ai", "prompts")

    def generate_multi_version(
        self,
        source_type,
        source_id=None,
        manual_text=None,
        target_platform="xiaohongshu",
        audience="",
        style="",
        enable_knowledge=False,
        enable_rewrite=False,
        version_count=3,
        extra_requirements="",
        product_type=None,
    ):
        """多版本生成"""
        # 输入验证
        if not target_platform:
            raise ValueError("platform 参数必填")
        if not audience:
            raise ValueError("audience 参数必填")
        if not product_type:
            logger.warning("product_type 未提供，建议补充以提升生成质量")

        try:
            # 获取原文
            input_text = self._get_input_text(source_type, source_id, manual_text)

            # 知识库增强
            knowledge_context = ""
            if enable_knowledge:
                from app.services.mvp_knowledge_service import MvpKnowledgeService

                ksvc = MvpKnowledgeService(self.db)
                results = ksvc.search_knowledge(input_text[:100], platform=target_platform)
                if results:
                    knowledge_context = "\n---\n".join([f"参考知识: {r.title}\n{r.content[:300]}" for r in results[:3]])

            # 构建Prompt
            prompt = self._build_prompt(
                input_text, target_platform, audience, style, knowledge_context, extra_requirements
            )

            # 调用LLM（带Mock兜底）
            versions = self._call_llm_sync(prompt)

            # 保存生成结果
            material_id = source_id if source_type == "material" else None
            for v in versions:
                # 解析结构化输出
                parsed = self._parse_structured_output(v["text"])
                result = MvpGenerationResult(
                    source_material_id=material_id,
                    input_text=input_text[:500],
                    output_title=v["title"],
                    output_text=v["text"],
                    version=v["version"],
                    platform=target_platform,
                    audience=audience,
                    style=style,
                    # 结构化输出字段
                    opening_hook=parsed.get("opening_hook") or None,
                    cta_section=parsed.get("cta") or None,
                    risk_disclaimer=parsed.get("risk_points") or None,
                    alternative_v1=parsed.get("alternative_safe") or None,
                    alternative_v2=parsed.get("alternative_aggressive") or None,
                    output_structure=parsed if parsed.get("success") else None,
                )
                self.db.add(result)
            self.db.commit()

            return {"versions": versions}
        except Exception as e:
            logger.exception("生成失败")
            self.db.rollback()
            return {
                "versions": self._mock_versions("生成失败，使用默认内容", target_platform),
                "fallback": True,
                "error": str(e),
            }

    def generate_final(self, **kwargs):
        """完整主链路：标签识别→知识检索→多版本生成→合规审核"""
        try:
            # 自动标签识别
            from app.services.mvp_tag_service import MvpTagService

            input_text = self._get_input_text(
                kwargs.get("source_type"), kwargs.get("source_id"), kwargs.get("manual_text")
            )
            tag_svc = MvpTagService(self.db)
            tags = tag_svc.identify_tags(input_text)

            # 生成多版本
            result = self.generate_multi_version(**kwargs)
            if result.get("error"):
                raise RuntimeError(result["error"])

            # 合规审核第一个版本
            from app.services.mvp_compliance_service import MvpComplianceService

            comp_svc = MvpComplianceService(self.db)
            compliance = None
            if result["versions"]:
                compliance = comp_svc.check(result["versions"][0]["text"])

            return {
                "versions": result["versions"],
                "tags": tags,
                "compliance": compliance,
                "final_text": result["versions"][0]["text"] if result["versions"] else "",
            }
        except Exception as e:
            logger.exception("完整生成失败")
            return {
                "versions": self._mock_versions("生成失败", "通用"),
                "tags": {},
                "compliance": None,
                "final_text": "",
                "error": str(e),
            }

    def _get_input_text(self, source_type, source_id, manual_text):
        """获取输入文本"""
        if source_type == "manual" and manual_text:
            return manual_text
        if source_type == "inbox" and source_id:
            item = self.db.query(MvpInboxItem).filter(MvpInboxItem.id == source_id).first()
            if item:
                return f"{item.title}\n\n{item.content}"
        if source_type == "material" and source_id:
            item = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == source_id).first()
            if item:
                return f"{item.title}\n\n{item.content}"
        raise ValueError("无法获取输入内容")

    def _build_prompt(self, text, platform, audience, style, knowledge, extra):
        """构建生成提示词"""
        prompt_file = os.path.join(self._prompts_dir, "mvp_general_v1.txt")
        structured_output_requirement = """

【结构化输出要求】
请按以下JSON格式输出每个版本的内容：
{
  "title": "标题",
  "opening_hook": "开头钩子（吸引注意力的第一句话）",
  "body": "正文主体",
  "cta": "行动引导（引导读者下一步操作）",
  "risk_points": "可能的合规风险点说明",
  "alternative_safe": "低风险安全版本的完整文案",
  "alternative_aggressive": "高转化版本的完整文案"
}
"""
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                template = f.read()
            base_prompt = (
                template.replace("{original_text}", text[:1000])
                .replace("{platform}", platform)
                .replace("{audience}", audience or "通用")
                .replace("{style}", style or "通用")
                .replace("{knowledge_context}", knowledge or "无")
                .replace("{extra_requirements}", extra or "无")
            )
            return base_prompt + structured_output_requirement
        except Exception:
            return (
                f"请将以下内容改写为3个版本（专业型、口语型、种草型），目标平台：{platform}\n\n原文：{text[:1000]}"
                + structured_output_requirement
            )

    def _call_llm_sync(self, prompt: str) -> list:
        """同步调用LLM，失败时使用Mock"""
        try:
            from app.services.ai_service import AIService

            ai_svc = AIService(self.db)

            # 安全处理事件循环：检查是否已在事件循环中
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            async def _call():
                return await ai_svc.call_llm(
                    prompt=prompt,
                    system_prompt="你是专业的贷款行业内容创作助手。请生成JSON格式的多版本内容。",
                    use_cloud=True,
                )

            if loop and loop.is_running():
                # 已在事件循环中，使用线程执行避免嵌套事件循环问题
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _call())
                    raw = future.result(timeout=120)
            else:
                # 不在事件循环中，直接使用 asyncio.run
                raw = asyncio.run(_call())

            return self._parse_versions(raw)
        except Exception as e:
            logger.warning(f"LLM调用失败，使用Mock: {e}")
            return self._mock_versions("", "通用")

    def _parse_versions(self, raw_text):
        """尝试解析LLM返回的JSON"""
        try:
            # 尝试找到JSON部分
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw_text[start:end])
                if "versions" in data:
                    return [
                        {
                            "title": v.get("title", ""),
                            "text": v.get("text", ""),
                            "version": v.get("version", f"v{i+1}"),
                            "style_label": v.get("style_label", ""),
                        }
                        for i, v in enumerate(data["versions"][:3])
                    ]
        except (json.JSONDecodeError, KeyError):
            pass
        return self._mock_versions(raw_text[:200], "通用")

    def _mock_versions(self, text, platform):
        """Mock生成结果"""
        preview = text[:80] if text else "示例内容"
        return [
            {
                "title": f"[专业版] {preview}...",
                "text": f"【专业分析】{text[:200] if text else '内容生成中'}...\n\n从专业角度来看，这个问题涉及多个方面。首先需要了解基本概念，其次要注意风险控制。建议咨询正规金融机构获取专业建议。",
                "version": "professional",
                "style_label": "专业型",
            },
            {
                "title": f"[口语版] {preview}...",
                "text": f"家人们！今天聊聊这个话题～{text[:150] if text else ''}...\n\n说真的，很多人都遇到过这种情况。我身边就有朋友也是这样，后来找到了正确的方法。大家有什么想法评论区聊聊！",
                "version": "casual",
                "style_label": "口语型",
            },
            {
                "title": f"[种草版] {preview}...",
                "text": f"姐妹们看过来！{text[:150] if text else ''}...\n\n真的不是我夸张，这个方法太实用了！亲测有效，分享给需要的小伙伴～记得收藏哦，以后用得上！",
                "version": "seeding",
                "style_label": "种草型",
            },
        ]

    @staticmethod
    def _parse_structured_output(raw_text: str) -> dict:
        """尝试将LLM输出解析为结构化字段。

        解析失败时回退到将整个文本放入body字段。
        """
        result = {
            "success": False,
            "title": "",
            "opening_hook": "",
            "body": raw_text,
            "cta": "",
            "risk_points": "",
            "alternative_safe": "",
            "alternative_aggressive": "",
        }
        try:
            # 尝试提取JSON块
            json_match = re.search(r"\{[\s\S]*\}", raw_text)
            if json_match:
                data = json.loads(json_match.group())
                if "title" in data or "body" in data:
                    result["success"] = True
                    result["title"] = data.get("title", "")
                    result["opening_hook"] = data.get("opening_hook", "")
                    result["body"] = data.get("body", raw_text)
                    result["cta"] = data.get("cta", "")
                    result["risk_points"] = data.get("risk_points", "")
                    result["alternative_safe"] = data.get("alternative_safe", "")
                    result["alternative_aggressive"] = data.get("alternative_aggressive", "")
        except (json.JSONDecodeError, AttributeError):
            pass
        return result

    @staticmethod
    def _ensure_structured_output(version: dict) -> dict:
        """确保输出结构完整性，为空字段补充默认值。

        Args:
            version: 版本字典，包含 text, opening_hook, cta_section, risk_disclaimer, alternative_v1, alternative_v2 等字段

        Returns:
            补充完整字段后的版本字典
        """
        # 默认风险提示
        default_risk_disclaimer = "请注意：贷款需谨慎，具体利率以实际审批为准。"

        # 确保 risk_disclaimer 非空
        if not version.get("risk_disclaimer"):
            version["risk_disclaimer"] = default_risk_disclaimer

        # 确保 alternative_v1 有默认提示（如果为空）
        if not version.get("alternative_v1"):
            version["alternative_v1"] = ""

        # 确保 alternative_v2 有默认提示（如果为空）
        if not version.get("alternative_v2"):
            version["alternative_v2"] = ""

        # 确保 opening_hook 非空（尝试从text提取第一句）
        if not version.get("opening_hook") and version.get("text"):
            text = version["text"]
            # 尝试提取第一句作为钩子
            first_sentence = text.split("\n")[0] if "\n" in text else text.split("。")[0]
            version["opening_hook"] = first_sentence[:50] if first_sentence else ""

        # 确保 cta_section 非空（尝试从text提取最后一句）
        if not version.get("cta_section") and version.get("text"):
            text = version["text"]
            # 尝试提取最后一句作为CTA
            last_sentence = text.split("。")[-1].strip() if "。" in text else text.split("\n")[-1].strip()
            version["cta_section"] = last_sentence[:100] if last_sentence else ""

        return version

    async def generate_full_pipeline(self, request: FullPipelineRequest) -> dict:
        """
        完整生成6步链路：
        Step 1: 知识检索 - 调用 MvpKnowledgeService.search_for_generation
        Step 2: Prompt编排 - 将召回的知识结构化拼接为上下文
        Step 3: 知识库+大模型改写 - 基于上下文，调用大模型改写出一版高质量基础文案
        Step 4: 多风格版本生成 - 基于改写版，生成3个风格版本
        Step 5: 合规检查 - 对每个版本执行双引擎合规检查
        Step 6: 输出最终文案 - 经合规修正后的终稿

        Args:
            request: FullPipelineRequest 包含 platform, account_type, audience, topic, goal, model, extra_requirements
        """
        try:
            # 获取模型配置
            model = getattr(request, "model", "volcano") or "volcano"
            extra_requirements = getattr(request, "extra_requirements", None) or ""
            use_cloud = model == "volcano"

            logger.info(f"[Pipeline] 全链路生成开始: platform={request.platform}, model={model}")

            # ========== Step 1: 知识检索 (使用混合检索v2) ==========
            logger.info("[Pipeline] Step 1: 开始知识检索")
            from app.services.mvp_knowledge_service import MvpKnowledgeService

            knowledge_svc = MvpKnowledgeService(self.db)
            try:
                knowledge_data = await knowledge_svc.search_for_generation_v2(
                    platform=request.platform,
                    audience=request.audience,
                    topic=request.topic,
                    content_type="",
                    account_type=request.account_type,
                    goal=request.goal or "",
                    embedding_model=request.model,
                )
            except Exception as e:
                logger.error(f"[Pipeline] Step 1 failed: 混合检索v2失败，降级到v1: {e}")
                knowledge_data = knowledge_svc.search_for_generation(
                    platform=request.platform,
                    audience=request.audience,
                    topic=request.topic,
                    account_type=request.account_type,
                    goal=request.goal or "",
                )
            logger.info(f"[Pipeline] Step 1 完成: 召回{len(knowledge_data.get('hot_content', []))}条爆款内容")

            # ========== Step 2: Prompt编排 ==========
            logger.info("[Pipeline] Step 2: 开始Prompt编排")
            context_str = self._build_knowledge_context(knowledge_data)
            has_knowledge = bool(context_str.strip())
            logger.info(f"[Pipeline] Step 2 完成: has_knowledge={has_knowledge}, context_len={len(context_str)}")

            # ========== Step 3: 基础改写 ==========
            logger.info("[Pipeline] Step 3: 开始基础改写")
            # 导入改写服务进行基础改写
            from app.services.mvp_rewrite_service import MvpRewriteService

            rewrite_svc = MvpRewriteService(self.db)
            rewrite_base = await rewrite_svc._generate_rewrite_base(
                request=request, context_str=context_str, extra_requirements=extra_requirements, use_cloud=use_cloud
            )
            logger.info(f"[Pipeline] Step 3 完成: len={len(rewrite_base)}")

            # ========== Step 4: 多风格版本生成 ==========
            logger.info("[Pipeline] Step 4: 开始多风格版本生成")
            versions = await rewrite_svc._generate_style_versions(
                request=request, rewrite_base=rewrite_base, context_str=context_str, use_cloud=use_cloud
            )
            logger.info(f"[Pipeline] Step 4 完成: 生成{len(versions)}个版本")

            # ========== Step 5: 合规检查(双引擎) ==========
            logger.info("[Pipeline] Step 5: 开始合规检查")
            from app.services.mvp_compliance_service import MvpComplianceService

            compliance_svc = MvpComplianceService(self.db)

            # 使用 asyncio.gather 并发执行合规检查
            async def check_single_version(v):
                comp_result = await compliance_svc.check_async(text=v.text, enable_llm=False, model=model)
                return {"version": v, "compliance": comp_result}

            version_compliance_results = await asyncio.gather(*[check_single_version(v) for v in versions])
            version_compliance_results = list(version_compliance_results)
            logger.info(f"[Pipeline] Step 5 完成: 检查了{len(version_compliance_results)}个版本")

            # 取风险最高的作为整体 compliance 结果
            risk_order = {"high": 3, "medium": 2, "low": 1}
            max_risk_item = max(
                version_compliance_results, key=lambda x: risk_order.get(x["compliance"].get("risk_level", "low"), 0)
            )
            overall_compliance = max_risk_item["compliance"]

            # ========== Step 6: 输出最终文案 ==========
            logger.info("[Pipeline] Step 6: 开始选择最终文案")
            final_text = self._select_final_text(version_compliance_results)
            logger.info(f"[Pipeline] Step 6 完成: len={len(final_text)}")

            # 构建响应
            compliance_result = ComplianceResult(
                risk_level=overall_compliance.get("risk_level", "low"),
                risk_score=overall_compliance.get("risk_score", 0),
                risk_points=[
                    RiskPoint(
                        keyword=rp.get("keyword", ""),
                        reason=rp.get("reason", ""),
                        suggestion=rp.get("suggestion", ""),
                        source=rp.get("source", "rule"),
                    )
                    for rp in overall_compliance.get("risk_points", [])
                ],
                suggestions=overall_compliance.get("suggestions", []),
                rewritten_text=overall_compliance.get("rewritten_text", ""),
                llm_analysis=overall_compliance.get("llm_analysis"),
                auto_fixed_text=overall_compliance.get("auto_fixed_text")
                or overall_compliance.get("rewritten_text", ""),
            )

            # 将逐版本的合规结果附加到每个版本上
            versions_with_compliance = []
            for i, v in enumerate(versions):
                v_dict = v.model_dump() if hasattr(v, "model_dump") else v
                if i < len(version_compliance_results):
                    v_dict["compliance"] = (
                        version_compliance_results[i]["compliance"] if version_compliance_results else None
                    )
                versions_with_compliance.append(v_dict)

            # Step 5.5: 对基础改写版进行合规检查
            rewrite_base_compliance = await compliance_svc.check_async(text=rewrite_base, enable_llm=False, model=model)

            # 将基础改写版作为第一个版本加入列表
            rewrite_base_version = {
                "style": "rewrite_base",
                "title": "基础改写版",
                "text": rewrite_base,
                "compliance": rewrite_base_compliance,
            }
            versions_with_compliance.insert(0, rewrite_base_version)

            # Step 6.5: 确保每个版本输出结构完整
            for v in versions_with_compliance:
                self._ensure_structured_output(v)

            logger.info("[Pipeline] 全链路生成成功完成")

            # 后台异步 LLM 合规检测（不阻塞返回）
            asyncio.create_task(self._background_llm_compliance_check(versions, model))

            return {
                "versions": versions_with_compliance,
                "compliance": compliance_result.model_dump(),
                "final_text": final_text,
                "rewrite_base": rewrite_base,
                "knowledge_context_used": has_knowledge,
            }

        except Exception as e:
            logger.exception(f"[Pipeline] 全流程生成失败: {e}")
            # Fallback：返回默认内容
            fallback_versions = self._fallback_versions(request)
            return {
                "versions": fallback_versions,
                "compliance": {
                    "risk_level": "low",
                    "risk_score": 0,
                    "risk_points": [],
                    "suggestions": [],
                    "rewritten_text": "",
                    "llm_analysis": None,
                },
                "final_text": fallback_versions[0]["text"] if fallback_versions else "",
                "rewrite_base": "",
                "knowledge_context_used": False,
                "error": f"生成流程失败: {str(e)}",
            }

    def _build_knowledge_context(self, knowledge_data: dict) -> str:
        """将知识库召回结果拼接为结构化上下文字符串"""
        sections = []

        # 【案例参考】
        hot_content = knowledge_data.get("hot_content", [])
        if hot_content:
            hot_lines = []
            for item in hot_content[:3]:
                title = item.get("title", "")
                content = item.get("content", "")[:300]
                if title or content:
                    hot_lines.append(f"- {title}: {content}")
            if hot_lines:
                sections.append("【案例参考】\n" + "\n".join(hot_lines))

        # 【平台表达规则】
        platform_rules = knowledge_data.get("platform_rules", [])
        if platform_rules:
            rules_lines = [item.get("content", "")[:200] for item in platform_rules[:3] if item.get("content")]
            if rules_lines:
                sections.append("【平台表达规则】\n" + "\n".join(rules_lines))

        # 【人群洞察】
        audience_insight = knowledge_data.get("audience_insight", [])
        if audience_insight:
            insight_lines = [item.get("content", "")[:200] for item in audience_insight[:2] if item.get("content")]
            if insight_lines:
                sections.append("【人群洞察】\n" + "\n".join(insight_lines))

        # 【风险限制】
        risk_rules = knowledge_data.get("risk_rules", [])
        if risk_rules:
            risk_lines = [item.get("content", "")[:200] for item in risk_rules[:3] if item.get("content")]
            if risk_lines:
                sections.append("【风险限制】\n" + "\n".join(risk_lines))

        # 【语气模板】
        tone_template = knowledge_data.get("tone_template")
        if tone_template and tone_template.get("content"):
            sections.append("【语气模板】\n" + tone_template.get("content", "")[:300])

        # 【CTA参考】
        cta_templates = knowledge_data.get("cta_templates", [])
        if cta_templates:
            cta_lines = [item.get("content", "")[:150] for item in cta_templates[:3] if item.get("content")]
            if cta_lines:
                sections.append("【CTA参考】\n" + "\n".join(cta_lines))

        return "\n\n".join(sections)

    async def _generate_three_versions(self, request: FullPipelineRequest, context_str: str) -> List[VersionItem]:
        """生成3个版本（professional/casual/seeding）"""
        from app.services.ai_service import AIService

        ai_svc = AIService(self.db)

        versions = []
        version_configs = [
            ("professional", "专业型：专业、权威、数据支撑、逻辑清晰，像金融专家给建议"),
            ("casual", "口语型：口语化、亲切、接地气、像朋友聊天，短句为主"),
            ("seeding", "种草型：种草风、emoji丰富、吸引眼球、制造好奇，真实分享感"),
        ]

        for version_key, style_desc in version_configs:
            try:
                prompt = self._build_version_prompt(request, context_str, version_key, style_desc)
                system_prompt = self._build_system_prompt(request, version_key)

                raw_response = await ai_svc.call_llm(
                    prompt=prompt, system_prompt=system_prompt, use_cloud=True, scene=f"generate_{version_key}"
                )

                title, text = self._parse_title_text(raw_response)
                versions.append(VersionItem(style=version_key, title=title, text=text))

            except Exception as e:
                logger.warning(f"生成{version_key}版本失败: {e}")
                # Fallback for this version
                versions.append(self._fallback_single_version(request, version_key))

        return versions

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

    def _build_version_prompt(
        self, request: FullPipelineRequest, context_str: str, version_key: str, style_desc: str
    ) -> str:
        """构建版本生成提示词"""
        audience_desc = self.AUDIENCE_MAP.get(request.audience, request.audience)
        topic_desc = self.TOPIC_MAP.get(request.topic, request.topic)
        goal_desc = self.GOAL_MAP.get(request.goal, request.goal)

        prompt = f"""请为以下场景创作一篇{style_desc}的内容：

【目标人群】{audience_desc}
【内容主题】{topic_desc}
【内容目标】{goal_desc}
【目标平台】{request.platform}
"""

        if context_str:
            prompt += f"""\n【知识库参考（仅供学习风格和要点，不要照抄）】
{context_str}
"""

        prompt += """\n【输出要求】
请严格按以下格式输出：
【标题】（不超过20字的吸引人标题）
【正文】（正文内容，300-800字）

注意：
1. 标题要有吸引力，能让目标人群想点击
2. 正文要自然流畅，符合平台调性
3. 禁止使用"必过""包过""100%通过"等违规词
4. 结尾需有引导动作（私信/评论/收藏）"""

        return prompt

    def _parse_title_text(self, raw_response: str) -> tuple:
        """解析LLM返回的标题和正文"""
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

    def _select_final_text(self, version_compliance_results: list) -> str:
        """选出最终推荐文本：优先选风险最低版本的合规修正文本"""
        risk_order = {"low": 1, "medium": 2, "high": 3}

        # 按风险等级排序，优先低风险
        sorted_results = sorted(
            version_compliance_results, key=lambda x: risk_order.get(x["compliance"].get("risk_level", "medium"), 2)
        )

        # 如果都是同一风险等级，优先 professional
        same_risk_level = all(
            r["compliance"].get("risk_level") == sorted_results[0]["compliance"].get("risk_level")
            for r in sorted_results
        )

        if same_risk_level:
            for r in sorted_results:
                if r["version"].style == "professional":
                    rewritten = r["compliance"].get("rewritten_text", "")
                    return rewritten if rewritten else r["version"].text

        # 取风险最低的
        best = sorted_results[0]
        rewritten = best["compliance"].get("rewritten_text", "")
        return rewritten if rewritten else best["version"].text

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

    def _fallback_versions(self, request: FullPipelineRequest) -> list:
        """全部版本的fallback"""
        versions = []
        for version_key in ["professional", "casual", "seeding"]:
            v = self._fallback_single_version(request, version_key)
            versions.append(v.model_dump())
        return versions

    async def _background_llm_compliance_check(self, versions: List[VersionItem], model: str):
        """后台异步执行LLM语义合规检测，不阻塞生成流程"""
        try:
            logger.info("[合规后台] 开始LLM语义合规检测，共%d个版本", len(versions))

            from app.services.mvp_compliance_service import MvpComplianceService

            compliance_svc = MvpComplianceService(self.db)

            # 并发检测所有版本
            tasks = []
            for i, v in enumerate(versions):
                text = v.text if hasattr(v, "text") else v.get("text", "")
                tasks.append(compliance_svc.check_async(text=text, enable_llm=True, model=model))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning("[合规后台] 版本%d LLM检测异常: %s", i, str(result))
                else:
                    risk_level = result.get("risk_level", "unknown") if isinstance(result, dict) else "unknown"
                    risk_points = result.get("risk_points", []) if isinstance(result, dict) else []
                    logger.info(
                        "[合规后台] 版本%d LLM检测完成: risk_level=%s, risk_points=%d个",
                        i,
                        risk_level,
                        len(risk_points),
                    )
                    if risk_points:
                        for rp in risk_points:
                            logger.warning("[合规后台] 版本%d 风险点: %s", i, rp)

            logger.info("[合规后台] 全部LLM语义合规检测完成")
        except Exception as e:
            logger.error("[合规后台] LLM合规检测任务异常: %s", str(e))

    def get_generation_history(self, material_id: int = None, page=1, size=20):
        """获取生成历史"""
        try:
            q = self.db.query(MvpGenerationResult)
            if material_id:
                q = q.filter(MvpGenerationResult.source_material_id == material_id)
            total = q.count()
            items = q.order_by(MvpGenerationResult.created_at.desc()).offset((page - 1) * size).limit(size).all()
            return {"items": items, "total": total, "page": page, "size": size}
        except Exception:
            return {"items": [], "total": 0, "page": page, "size": size}

    def mark_final(self, generation_id: int):
        """标记为最终版本"""
        try:
            item = self.db.query(MvpGenerationResult).filter(MvpGenerationResult.id == generation_id).first()
            if not item:
                raise ValueError("生成结果不存在")
            item.is_final = True
            self.db.commit()
            return item
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"标记失败: {str(e)}")

    # =========================================================================
    # 强约束生成方法
    # =========================================================================

    async def constrained_generate(self, request: ConstrainedGenerateRequest) -> ConstrainedGenerateResponse:
        """
        强约束生成 - 基于细粒度约束条件生成结构化内容

        主要步骤：
        1. 约束校验 - 验证所有必填字段
        2. 知识库检索 - 基于 platform + audience + product_type 组合检索相关知识
        3. Prompt 组装 - 将所有约束字段注入 prompt
        4. 多版本生成 - 按 version_count 生成多个版本
        5. 结构化解析 - 将 AI 输出解析为 title/hook/body/call_to_action 结构
        6. 合规预检 - 每个版本调用合规检查，标记 compliance_level

        Args:
            request: ConstrainedGenerateRequest 强约束生成请求

        Returns:
            ConstrainedGenerateResponse 结构化生成响应
        """
        start_time = time.time()
        generation_metadata = {
            "start_time": start_time,
            "model": request.model,
            "version_count_requested": request.version_count,
        }

        try:
            # Step 1: 约束校验
            logger.info("[ConstrainedGenerate] Step 1: 约束校验")
            self._validate_constraints(request)

            # Step 2: 知识库检索
            logger.info("[ConstrainedGenerate] Step 2: 知识库检索")
            knowledge_context = await self._retrieve_knowledge_for_constrained(request)

            # Step 3: 构建约束增强的 Prompt
            logger.info("[ConstrainedGenerate] Step 3: Prompt 组装")
            prompt = self._build_constrained_prompt(request, knowledge_context)

            # Step 4: 多版本生成
            logger.info("[ConstrainedGenerate] Step 4: 多版本生成")
            versions_raw = await self._generate_constrained_versions(request, prompt)

            # Step 5: 结构化解析
            logger.info("[ConstrainedGenerate] Step 5: 结构化解析")
            structured_versions = self._parse_structured_versions(versions_raw)

            # Step 6: 合规预检
            logger.info("[ConstrainedGenerate] Step 6: 合规预检")
            versions_with_compliance = await self._check_versions_compliance(structured_versions, request.model)

            # 选择推荐版本（优先选择合规等级最高的）
            recommended_idx = self._select_recommended_version(versions_with_compliance)

            # 构建响应
            generation_metadata.update(
                {
                    "duration_seconds": round(time.time() - start_time, 2),
                    "knowledge_used": bool(knowledge_context),
                    "versions_generated": len(versions_with_compliance),
                }
            )

            input_constraints_applied = {
                "platform": request.platform,
                "audience": request.audience,
                "product_type": request.product_type,
                "business_scenario": request.business_scenario,
                "target_action": request.target_action,
                "risk_level": request.risk_level,
                "style": request.style,
                "content_intent": request.content_intent,
                "guidance_method": request.guidance_method,
                "forbidden_count": len(request.forbidden_expressions) if request.forbidden_expressions else 0,
            }

            logger.info(
                "[ConstrainedGenerate] 生成完成: %d个版本, 推荐版本=%d, 耗时=%.2fs",
                len(versions_with_compliance),
                recommended_idx,
                generation_metadata["duration_seconds"],
            )

            return ConstrainedGenerateResponse(
                versions=versions_with_compliance,
                recommended_version=recommended_idx,
                input_constraints_applied=input_constraints_applied,
                generation_metadata=generation_metadata,
            )

        except Exception as e:
            logger.exception("[ConstrainedGenerate] 强约束生成失败: %s", str(e))
            # Fallback: 返回默认内容
            fallback_versions = self._fallback_structured_versions(request)
            generation_metadata.update(
                {
                    "duration_seconds": round(time.time() - start_time, 2),
                    "error": str(e),
                }
            )
            return ConstrainedGenerateResponse(
                versions=fallback_versions,
                recommended_version=0,
                input_constraints_applied={"error": "使用fallback内容"},
                generation_metadata=generation_metadata,
            )

    def _validate_constraints(self, request: ConstrainedGenerateRequest) -> None:
        """验证约束条件"""
        # platform 已在 Pydantic 中验证
        # product_type 已在 Pydantic 中验证
        # risk_level 已在 Pydantic 中验证

        if not request.audience or not request.audience.strip():
            raise ValueError("audience 参数必填")

        # 验证 style 如果提供
        if request.style:
            allowed_styles = ["口播", "图文", "问答", "经验帖"]
            if request.style not in allowed_styles:
                raise ValueError(f"style 必须是以下之一: {allowed_styles}")

        # 验证 content_intent 如果提供
        if request.content_intent:
            allowed_intents = ["科普", "避坑", "案例", "引流", "转化"]
            if request.content_intent not in allowed_intents:
                raise ValueError(f"content_intent 必须是以下之一: {allowed_intents}")

    async def _retrieve_knowledge_for_constrained(self, request: ConstrainedGenerateRequest) -> str:
        """基于约束条件检索知识库"""
        try:
            from app.services.mvp_knowledge_service import MvpKnowledgeService

            knowledge_svc = MvpKnowledgeService(self.db)

            # 构建检索查询
            query_parts = [request.product_type, request.audience]
            if request.business_scenario:
                query_parts.append(request.business_scenario)
            query = " ".join(query_parts)

            # 使用混合检索v2
            knowledge_data = await knowledge_svc.search_for_generation_v2(
                platform=request.platform,
                audience=request.audience,
                topic=request.product_type,
                content_type=request.style or "",
                account_type="loan_advisor",  # 默认助贷顾问
                goal=request.target_action or "",
                embedding_model=request.model,
            )

            return self._build_knowledge_context(knowledge_data)
        except Exception as e:
            logger.warning("[ConstrainedGenerate] 知识库检索失败: %s", str(e))
            return ""

    def _build_constrained_prompt(self, request: ConstrainedGenerateRequest, knowledge_context: str) -> str:
        """构建强约束生成 Prompt"""

        # 平台风格映射
        platform_style_map = {
            "xiaohongshu": "小红书风格：口语化、emoji丰富、种草感、真实分享调调",
            "douyin": "抖音风格：短句为主、节奏感强、开头3秒必须抓人、口播化",
            "zhihu": "知乎风格：专业理性、逻辑清晰、有分析过程、数据支撑",
        }
        platform_style = platform_style_map.get(request.platform, "通用风格")

        # 内容意图映射
        intent_guidance = {
            "科普": "以知识普及为主，客观介绍产品特点和适用人群",
            "避坑": "重点提醒常见误区和风险，帮助用户避免踩坑",
            "案例": "通过真实案例说明问题，增强可信度和代入感",
            "引流": "注重引导用户进行下一步互动，如私信咨询",
            "转化": "强调产品优势和办理便捷性，促进转化",
        }

        prompt_parts = [
            f"【任务】为{request.platform}平台创作获客内容",
            f"",
            f"【目标人群】{request.audience}",
            f"【产品类型】{request.product_type}",
            f"【平台风格】{platform_style}",
        ]

        if request.business_scenario:
            prompt_parts.append(f"【业务场景】{request.business_scenario}")

        if request.target_action:
            prompt_parts.append(f"【目标动作】{request.target_action}")

        if request.content_intent:
            prompt_parts.append(f"【内容意图】{intent_guidance.get(request.content_intent, request.content_intent)}")

        if request.style:
            prompt_parts.append(f"【内容形式】{request.style}")

        if request.guidance_method:
            prompt_parts.append(f"【引导方式】通过{request.guidance_method}引导用户")

        # 风险等级约束
        if request.risk_level == "low":
            prompt_parts.append("【风险约束】必须严格合规，避免任何夸大或承诺性表述")
        elif request.risk_level == "high":
            prompt_parts.append("【风险约束】可适当增强转化力度，但仍需合规")

        # 禁用表达
        if request.forbidden_expressions:
            forbidden_str = "、".join(request.forbidden_expressions)
            prompt_parts.append(f"【禁用表达】严禁使用: {forbidden_str}")

        # 合规说明
        if request.compliance_notes:
            prompt_parts.append(f"【合规说明】必须包含: {request.compliance_notes}")

        # 知识库上下文
        if knowledge_context:
            prompt_parts.extend(
                [
                    f"",
                    f"【参考知识】",
                    knowledge_context,
                ]
            )

        # 结构化输出要求
        prompt_parts.extend(
            [
                f"",
                f"【输出要求】",
                f"请生成JSON格式内容，包含以下字段:",
                f"{{",
                f'  "title": "吸引人的标题（不超过20字）",',
                f'  "hook": "开头钩子（吸引注意力的第一句话，50字以内）",',
                f'  "body": "正文主体（300-800字，符合平台风格）",',
                f'  "call_to_action": "行动引导（引导用户下一步操作）",',
                f'  "risk_notes": "风险点说明（必要的合规提示）"',
                f"}}",
                f"",
                f"注意事项:",
                f"1. 标题要有吸引力，能让目标人群想点击",
                f"2. 正文要自然流畅，符合平台调性",
                f"3. 禁止使用'必过''包过''100%通过'等违规词",
                f"4. 确保内容符合金融广告合规要求",
            ]
        )

        if request.extra_requirements:
            prompt_parts.append(f"\n【额外要求】{request.extra_requirements}")

        return "\n".join(prompt_parts)

    async def _generate_constrained_versions(self, request: ConstrainedGenerateRequest, prompt: str) -> List[Dict]:
        """生成多版本内容"""
        from app.services.ai_service import AIService

        ai_svc = AIService(self.db)
        versions = []

        # 定义版本风格
        version_styles = [
            ("professional", "专业型", "专业、权威、逻辑清晰"),
            ("casual", "口语型", "口语化、亲切、接地气"),
            ("seeding", "种草型", "种草风、emoji丰富、真实分享感"),
        ]

        # 根据 version_count 选择风格
        styles_to_generate = version_styles[: min(request.version_count, len(version_styles))]

        for style_key, style_name, style_desc in styles_to_generate:
            try:
                version_prompt = prompt + f"\n\n【本版本风格】{style_desc}"

                system_prompt = f"""你是专业的贷款行业内容创作助手。
请生成符合以下风格的JSON格式内容：{style_desc}
确保输出是有效的JSON格式。"""

                raw_response = await ai_svc.call_llm(
                    prompt=version_prompt,
                    system_prompt=system_prompt,
                    use_cloud=(request.model == "volcano"),
                    scene=f"constrained_generate_{style_key}",
                )

                versions.append(
                    {
                        "style": style_key,
                        "style_name": style_name,
                        "raw_text": raw_response,
                    }
                )

            except Exception as e:
                logger.warning("[ConstrainedGenerate] 版本 %s 生成失败: %s", style_key, str(e))
                # 继续生成其他版本

        # 如果所有版本都失败，返回 mock 数据
        if not versions:
            versions = self._mock_constrained_versions(request)

        return versions

    def _mock_constrained_versions(self, request: ConstrainedGenerateRequest) -> List[Dict]:
        """生成 mock 版本数据"""
        return [
            {
                "style": "professional",
                "style_name": "专业型",
                "raw_text": json.dumps(
                    {
                        "title": f"【专业解读】{request.product_type}申请指南",
                        "hook": f"关于{request.product_type}，很多{request.audience}都有疑问。",
                        "body": f"针对{request.audience}群体，{request.product_type}是一种常见的融资方式。申请时需要注意以下几点：首先，准备好相关资料；其次，了解产品特点；最后，评估自身还款能力。",
                        "call_to_action": "如有疑问，欢迎私信咨询。",
                        "risk_notes": "贷款需谨慎，具体利率以实际审批为准。",
                    },
                    ensure_ascii=False,
                ),
            },
            {
                "style": "casual",
                "style_name": "口语型",
                "raw_text": json.dumps(
                    {
                        "title": f"聊聊{request.product_type}那些事儿",
                        "hook": f"家人们！今天聊聊{request.product_type}～",
                        "body": f"很多{request.audience}朋友都问过我这个问题。说真的，{request.product_type}确实能帮上忙，但也要注意方法。记住这几点就够了：别盲目申请、先看清条件、量力而行。",
                        "call_to_action": "有问题评论区聊！",
                        "risk_notes": "贷款有风险，申请需谨慎。",
                    },
                    ensure_ascii=False,
                ),
            },
            {
                "style": "seeding",
                "style_name": "种草型",
                "raw_text": json.dumps(
                    {
                        "title": f"姐妹们！{request.product_type}攻略来了",
                        "hook": f"姐妹们看过来！关于{request.product_type}的干货～",
                        "body": f"身边好多{request.audience}的朋友都在问{request.product_type}。今天整理了避坑指南分享给大家～真的不是我夸张，这个方法太实用了！",
                        "call_to_action": "记得收藏！有用的话给我点个赞呀~",
                        "risk_notes": "具体产品以实际审批为准。",
                    },
                    ensure_ascii=False,
                ),
            },
        ][: request.version_count]

    def _parse_structured_versions(self, versions_raw: List[Dict]) -> List[StructuredGenerateOutput]:
        """解析结构化版本输出"""
        structured_versions = []

        for v in versions_raw:
            try:
                raw_text = v.get("raw_text", "")
                parsed = self._parse_structured_output_v2(raw_text)

                structured_versions.append(
                    StructuredGenerateOutput(
                        title=parsed.get("title", ""),
                        hook=parsed.get("hook", ""),
                        body=parsed.get("body", ""),
                        call_to_action=parsed.get("call_to_action", ""),
                        risk_notes=parsed.get("risk_notes"),
                        compliance_level="green",  # 默认绿色，后续会更新
                    )
                )
            except Exception as e:
                logger.warning("[ConstrainedGenerate] 解析版本失败: %s", str(e))
                # Fallback: 使用原始文本作为 body
                structured_versions.append(
                    StructuredGenerateOutput(
                        title="生成中...",
                        hook="",
                        body=v.get("raw_text", "")[:500],
                        call_to_action="",
                        compliance_level="yellow",
                    )
                )

        return structured_versions

    def _parse_structured_output_v2(self, raw_text: str) -> Dict[str, str]:
        """解析结构化输出（增强版）"""
        result = {
            "title": "",
            "hook": "",
            "body": "",
            "call_to_action": "",
            "risk_notes": "",
        }

        try:
            # 尝试提取 JSON 块
            json_match = re.search(r"\{[\s\S]*?\}", raw_text)
            if json_match:
                data = json.loads(json_match.group())
                result["title"] = data.get("title", "")
                result["hook"] = data.get("hook", data.get("opening_hook", ""))
                result["body"] = data.get("body", data.get("text", raw_text))
                result["call_to_action"] = data.get("call_to_action", data.get("cta", ""))
                result["risk_notes"] = data.get("risk_notes", data.get("risk_points", ""))
                return result
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: 尝试正则提取
        try:
            title_match = re.search(r"[【\[]?标题[】\]]?[：:]?\s*(.+?)(?=\n|【|［|$)", raw_text)
            if title_match:
                result["title"] = title_match.group(1).strip()

            hook_match = re.search(r"[【\[]?开头钩子[】\]]?[：:]?\s*(.+?)(?=\n|【|［|$)", raw_text)
            if hook_match:
                result["hook"] = hook_match.group(1).strip()

            body_match = re.search(r"[【\[]?正文[】\]]?[：:]?\s*(.+?)(?=\n|【|［|$)", raw_text, re.DOTALL)
            if body_match:
                result["body"] = body_match.group(1).strip()

            cta_match = re.search(r"[【\[]?行动引导[】\]]?[：:]?\s*(.+?)(?=\n|【|［|$)", raw_text)
            if cta_match:
                result["call_to_action"] = cta_match.group(1).strip()
        except Exception:
            pass

        # 如果 body 仍为空，使用原始文本
        if not result["body"]:
            result["body"] = raw_text

        return result

    async def _check_versions_compliance(
        self, versions: List[StructuredGenerateOutput], model: str
    ) -> List[StructuredGenerateOutput]:
        """检查版本合规性"""
        try:
            from app.services.mvp_compliance_service import MvpComplianceService

            compliance_svc = MvpComplianceService(self.db)

            for v in versions:
                try:
                    # 合并文本进行检查
                    full_text = f"{v.title}\n{v.hook}\n{v.body}\n{v.call_to_action}"
                    result = await compliance_svc.check_async(text=full_text, enable_llm=False, model=model)

                    risk_level = result.get("risk_level", "low")
                    # 映射 risk_level 到 compliance_level
                    compliance_map = {
                        "low": "green",
                        "medium": "yellow",
                        "high": "red",
                    }
                    v.compliance_level = compliance_map.get(risk_level, "yellow")

                    # 如果有风险说明，添加到 risk_notes
                    risk_points = result.get("risk_points", [])
                    if risk_points:
                        risk_summary = "; ".join([rp.get("reason", "") for rp in risk_points[:3]])
                        if v.risk_notes:
                            v.risk_notes = f"{v.risk_notes}; {risk_summary}"
                        else:
                            v.risk_notes = risk_summary

                except Exception as e:
                    logger.warning("[ConstrainedGenerate] 版本合规检查失败: %s", str(e))
                    v.compliance_level = "yellow"

        except Exception as e:
            logger.warning("[ConstrainedGenerate] 合规服务调用失败: %s", str(e))
            # 所有版本标记为黄色（未知）
            for v in versions:
                v.compliance_level = "yellow"

        return versions

    def _select_recommended_version(self, versions: List[StructuredGenerateOutput]) -> int:
        """选择推荐版本（优先选择合规等级最高的）"""
        if not versions:
            return 0

        compliance_priority = {"green": 0, "yellow": 1, "red": 2}

        best_idx = 0
        best_priority = compliance_priority.get(versions[0].compliance_level, 1)

        for i, v in enumerate(versions[1:], 1):
            priority = compliance_priority.get(v.compliance_level, 1)
            if priority < best_priority:
                best_priority = priority
                best_idx = i

        return best_idx

    def _fallback_structured_versions(self, request: ConstrainedGenerateRequest) -> List[StructuredGenerateOutput]:
        """生成 fallback 结构化版本"""
        return [
            StructuredGenerateOutput(
                title=f"【{request.product_type}】{request.audience}专属方案",
                hook=f"针对{request.audience}的{request.product_type}解决方案",
                body=f"我们为{request.audience}群体提供专业的{request.product_type}服务。申请流程简单，审批快速。请根据自身情况合理申请，注意评估还款能力。",
                call_to_action="如需了解详情，请私信咨询。",
                risk_notes="贷款需谨慎，具体利率以实际审批为准。",
                compliance_level="green",
            )
        ]
