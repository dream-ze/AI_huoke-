"""MVP AI生成服务 - 多版本生成+完整主链路"""
import json
import os
import re
import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import MvpMaterialItem, MvpInboxItem, MvpGenerationResult, MvpKnowledgeItem
from app.schemas.generate_schema import FullPipelineRequest, VersionItem, ComplianceResult, RiskPoint

logger = logging.getLogger(__name__)


class MvpGenerateService:
    def __init__(self, db: Session):
        self.db = db
        self._prompts_dir = os.path.join(os.path.dirname(__file__), "..", "ai", "prompts")

    def generate_multi_version(self, source_type, source_id=None, manual_text=None,
                                target_platform="xiaohongshu", audience="", style="",
                                enable_knowledge=False, enable_rewrite=False,
                                version_count=3, extra_requirements=""):
        """多版本生成"""
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
                    knowledge_context = "\n---\n".join([
                        f"参考知识: {r.title}\n{r.content[:300]}" 
                        for r in results[:3]
                    ])
            
            # 构建Prompt
            prompt = self._build_prompt(input_text, target_platform, audience, style, knowledge_context, extra_requirements)
            
            # 调用LLM（带Mock兜底）
            versions = self._call_llm_sync(prompt)
            
            # 保存生成结果
            material_id = source_id if source_type == "material" else None
            for v in versions:
                result = MvpGenerationResult(
                    source_material_id=material_id,
                    input_text=input_text[:500],
                    output_title=v["title"],
                    output_text=v["text"],
                    version=v["version"],
                    platform=target_platform,
                    audience=audience,
                    style=style
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
                "error": str(e)
            }

    def generate_final(self, **kwargs):
        """完整主链路：标签识别→知识检索→多版本生成→合规审核"""
        try:
            # 自动标签识别
            from app.services.mvp_tag_service import MvpTagService
            input_text = self._get_input_text(
                kwargs.get("source_type"), 
                kwargs.get("source_id"), 
                kwargs.get("manual_text")
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
                "final_text": result["versions"][0]["text"] if result["versions"] else ""
            }
        except Exception as e:
            logger.exception("完整生成失败")
            return {
                "versions": self._mock_versions("生成失败", "通用"),
                "tags": {},
                "compliance": None,
                "final_text": "",
                "error": str(e)
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
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                template = f.read()
            return template.replace("{original_text}", text[:1000])\
                          .replace("{platform}", platform)\
                          .replace("{audience}", audience or "通用")\
                          .replace("{style}", style or "通用")\
                          .replace("{knowledge_context}", knowledge or "无")\
                          .replace("{extra_requirements}", extra or "无")
        except Exception:
            return f"请将以下内容改写为3个版本（专业型、口语型、种草型），目标平台：{platform}\n\n原文：{text[:1000]}"

    def _call_llm_sync(self, prompt: str) -> list:
        """同步调用LLM，失败时使用Mock"""
        try:
            from app.services.ai_service import AIService
            ai_svc = AIService(self.db)
            # 使用asyncio运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                raw = loop.run_until_complete(
                    ai_svc.call_llm(
                        prompt=prompt, 
                        system_prompt="你是专业的贷款行业内容创作助手。请生成JSON格式的多版本内容。",
                        use_cloud=True
                    )
                )
                return self._parse_versions(raw)
            finally:
                loop.close()
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
                            "style_label": v.get("style_label", "")
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
                "style_label": "专业型"
            },
            {
                "title": f"[口语版] {preview}...",
                "text": f"家人们！今天聊聊这个话题～{text[:150] if text else ''}...\n\n说真的，很多人都遇到过这种情况。我身边就有朋友也是这样，后来找到了正确的方法。大家有什么想法评论区聊聊！",
                "version": "casual",
                "style_label": "口语型"
            },
            {
                "title": f"[种草版] {preview}...",
                "text": f"姐妹们看过来！{text[:150] if text else ''}...\n\n真的不是我夸张，这个方法太实用了！亲测有效，分享给需要的小伙伴～记得收藏哦，以后用得上！",
                "version": "seeding",
                "style_label": "种草型"
            },
        ]

    # ========== 全流程生成 ==========
    
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
            model = getattr(request, 'model', 'volcano') or 'volcano'
            extra_requirements = getattr(request, 'extra_requirements', None) or ''
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
            rewrite_base = await self._generate_rewrite_base(
                request=request,
                context_str=context_str,
                extra_requirements=extra_requirements,
                use_cloud=use_cloud
            )
            logger.info(f"[Pipeline] Step 3 完成: len={len(rewrite_base)}")
            
            # ========== Step 4: 多风格版本生成 ==========
            logger.info("[Pipeline] Step 4: 开始多风格版本生成")
            versions = await self._generate_style_versions(
                request=request,
                rewrite_base=rewrite_base,
                context_str=context_str,
                use_cloud=use_cloud
            )
            logger.info(f"[Pipeline] Step 4 完成: 生成{len(versions)}个版本")
            
            # ========== Step 5: 合规检查(双引擎) ==========
            logger.info("[Pipeline] Step 5: 开始合规检查")
            from app.services.mvp_compliance_service import MvpComplianceService
            compliance_svc = MvpComplianceService(self.db)
            
            # 使用 asyncio.gather 并发执行合规检查
            async def check_single_version(v):
                comp_result = await compliance_svc.check_async(
                    text=v.text,
                    enable_llm=False,
                    model=model
                )
                return {"version": v, "compliance": comp_result}
            
            version_compliance_results = await asyncio.gather(
                *[check_single_version(v) for v in versions]
            )
            version_compliance_results = list(version_compliance_results)
            logger.info(f"[Pipeline] Step 5 完成: 检查了{len(version_compliance_results)}个版本")
            
            # 取风险最高的作为整体 compliance 结果
            risk_order = {"high": 3, "medium": 2, "low": 1}
            max_risk_item = max(
                version_compliance_results,
                key=lambda x: risk_order.get(x["compliance"].get("risk_level", "low"), 0)
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
                        source=rp.get("source", "rule")
                    )
                    for rp in overall_compliance.get("risk_points", [])
                ],
                suggestions=overall_compliance.get("suggestions", []),
                rewritten_text=overall_compliance.get("rewritten_text", ""),
                llm_analysis=overall_compliance.get("llm_analysis"),
                auto_fixed_text=overall_compliance.get("auto_fixed_text") or overall_compliance.get("rewritten_text", "")
            )
            
            # 将逐版本的合规结果附加到每个版本上
            versions_with_compliance = []
            for i, v in enumerate(versions):
                v_dict = v.model_dump() if hasattr(v, 'model_dump') else v
                if i < len(version_compliance_results):
                    v_dict["compliance"] = version_compliance_results[i]["compliance"] if version_compliance_results else None
                versions_with_compliance.append(v_dict)
                        
            # Step 5.5: 对基础改写版进行合规检查
            rewrite_base_compliance = await compliance_svc.check_async(
                text=rewrite_base,
                enable_llm=False,
                model=model
            )
                        
            # 将基础改写版作为第一个版本加入列表
            rewrite_base_version = {
                "style": "rewrite_base",
                "title": "基础改写版",
                "text": rewrite_base,
                "compliance": rewrite_base_compliance
            }
            versions_with_compliance.insert(0, rewrite_base_version)
            
            logger.info("[Pipeline] 全链路生成成功完成")
                        
            # 后台异步 LLM 合规检测（不阻塞返回）
            asyncio.create_task(
                self._background_llm_compliance_check(versions, model)
            )
                        
            return {
                "versions": versions_with_compliance,
                "compliance": compliance_result.model_dump(),
                "final_text": final_text,
                "rewrite_base": rewrite_base,
                "knowledge_context_used": has_knowledge
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
                    "llm_analysis": None
                },
                "final_text": fallback_versions[0]["text"] if fallback_versions else "",
                "rewrite_base": "",
                "knowledge_context_used": False,
                "error": f"生成流程失败: {str(e)}"
            }

    # 语气风格映射表
    TONE_MAP = {
        "professional": "专业严谨、逻辑清晰",
        "friendly": "亲切友好、平易近人",
        "humorous": "幽默风趣、轻松活泼",
        "empathetic": "共情走心、温暖感人",
        "urgent": "紧迫感强、催促行动",
    }



    async def _generate_rewrite_base(self, request: FullPipelineRequest, context_str: str, 
                                      extra_requirements: str, use_cloud: bool) -> str:
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
            if hasattr(request, 'tone') and request.tone:
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
5. 禁止使用“必过”“包过”“100%通过”等违规词"""
            
            raw_response = await ai_svc.call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                use_cloud=use_cloud,
                scene="generate_rewrite_base"
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
        self, 
        request: FullPipelineRequest, 
        rewrite_base: str,
        context_str: str,
        use_cloud: bool
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
        tasks = [
            self._generate_single_style(request, rewrite_base, version_key, style_desc, use_cloud)
            for version_key, style_desc in version_configs
        ]
        versions = await asyncio.gather(*tasks)
        return list(versions)

    async def _generate_single_style(
        self,
        request: FullPipelineRequest,
        rewrite_base: str,
        version_key: str,
        style_desc: str,
        use_cloud: bool
    ) -> VersionItem:
        """生成单个风格版本（供并发调用）"""
        from app.services.ai_service import AIService
        ai_svc = AIService(self.db)

        try:
            prompt = self._build_style_version_prompt(
                request=request,
                rewrite_base=rewrite_base,
                version_key=version_key,
                style_desc=style_desc
            )
            system_prompt = self._build_system_prompt(request, version_key)

            raw_response = await ai_svc.call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                use_cloud=use_cloud,
                scene=f"generate_{version_key}"
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
        self, 
        request: FullPipelineRequest, 
        rewrite_base: str, 
        version_key: str, 
        style_desc: str
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
4. 禁止使用“必过”“包过”“100%通过”等违规词"""
        
        return prompt

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
                    prompt=prompt,
                    system_prompt=system_prompt,
                    use_cloud=True,
                    scene=f"generate_{version_key}"
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

    def _build_version_prompt(self, request: FullPipelineRequest, context_str: str, version_key: str, style_desc: str) -> str:
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
        title_match = re.search(r'【标题】[：:]?\s*(.+?)(?=\n|【正文】|$)', raw_response, re.DOTALL)
        text_match = re.search(r'【正文】[：:]?\s*(.+)', raw_response, re.DOTALL)
        
        if title_match and text_match:
            title = title_match.group(1).strip()[:50]
            text = text_match.group(1).strip()
            if title and text:
                return title, text
        
        # Fallback：第一行作为标题，其余作为正文
        lines = raw_response.strip().split('\n')
        if len(lines) >= 2:
            title = lines[0].strip()[:50]
            text = '\n'.join(lines[1:]).strip()
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
            version_compliance_results,
            key=lambda x: risk_order.get(x["compliance"].get("risk_level", "medium"), 2)
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
            "professional": ("专业分析", f"关于{topic_desc}，针对{audience_desc}群体，建议先了解自身情况，再选择合适的方案。专业建议：1. 先查询征信报告；2. 评估自身还款能力；3. 对比多家产品。有任何疑问欢迎咨询。"),
            "casual": ("聊聊看", f"家人们！今天聊聊{topic_desc}这个话题～很多{audience_desc}朋友都问过我这个问题。说真的，方法很重要！记住这几点就够了：别盲目申请、先看清条件、量力而行。有问题评论区聊！"),
            "seeding": ("亲测分享", f"姐妹们看过来！关于{topic_desc}，我身边好多{audience_desc}的朋友都踩过坑。今天整理了避坑指南分享给大家～记得收藏！有用的话给我点个赞呀~"),
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
                text = v.text if hasattr(v, 'text') else v.get('text', '')
                tasks.append(compliance_svc.check_async(
                    text=text,
                    enable_llm=True,
                    model=model
                ))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning("[合规后台] 版本%d LLM检测异常: %s", i, str(result))
                else:
                    risk_level = result.get('risk_level', 'unknown') if isinstance(result, dict) else 'unknown'
                    risk_points = result.get('risk_points', []) if isinstance(result, dict) else []
                    logger.info("[合规后台] 版本%d LLM检测完成: risk_level=%s, risk_points=%d个", 
                               i, risk_level, len(risk_points))
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
