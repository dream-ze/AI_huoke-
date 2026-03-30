import httpx
import json
import logging
import time
from uuid import uuid4
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import ArkCallLog
from app.services.compliance_service import ComplianceService

logger = logging.getLogger(__name__)


class AIService:
    """LLM service for content rewriting"""
    
    def __init__(self, db: Session | None = None):
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL
        self.use_cloud = settings.USE_CLOUD_MODEL
        self.db = db
    
    async def call_llm(
        self,
        prompt: str,
        system_prompt: str = "",
        use_cloud: bool = False,
        user_id: int | None = None,
        scene: str = "general",
        max_tokens: int | None = None,
    ) -> str:
        """Call LLM (Ollama or Cloud)"""

        if use_cloud and settings.ARK_API_KEY:
            return await self._call_ark(prompt, system_prompt, user_id=user_id, scene=scene, max_tokens=max_tokens)
        else:
            return await self._call_ollama(prompt, system_prompt, max_tokens=max_tokens)

    async def _call_ollama(self, prompt: str, system_prompt: str = "", max_tokens: int | None = None) -> str:
        """Call Ollama local model"""
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "temperature": 0.7,
                        "num_predict": max_tokens or 800,  # 限制生成长度，加速响应
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    raise Exception(f"Ollama error: {response.text}")
        except Exception as e:
            raise Exception(f"Failed to call Ollama: {str(e)}")

    async def _call_ark(
        self,
        prompt: str,
        system_prompt: str = "",
        user_id: int | None = None,
        scene: str = "general",
        max_tokens: int | None = None,
    ) -> str:
        """Call Volcano Engine (Fire Engine) using OpenAI-compatible chat/completions API"""
        if not settings.ARK_API_KEY:
            raise Exception("ARK_API_KEY is not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.ARK_MODEL,
            "messages": messages,
            "max_tokens": max_tokens or 800,  # 限制生成长度，加速响应
        }

        data = await self._post_ark_chat_completions(payload, user_id=user_id, scene=scene)
        return self._extract_chat_completions_text(data)

    async def analyze_image_with_ark(
        self,
        image_url: str,
        text: str,
        model: str | None = None,
        user_id: int | None = None,
    ) -> Dict[str, Any]:
        """Analyze image content with Ark multimodal chat/completions API."""
        if not settings.ARK_API_KEY:
            raise Exception("ARK_API_KEY is not configured")

        payload = {
            "model": model or settings.ARK_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                        {
                            "type": "text",
                            "text": text,
                        },
                    ],
                }
            ],
        }

        data = await self._post_ark_chat_completions(payload, user_id=user_id, scene="vision")
        answer = self._extract_chat_completions_text(data)
        return {
            "model": payload["model"],
            "image_url": image_url,
            "text": text,
            "answer": answer,
        }

    async def _post_ark_chat_completions(
        self,
        payload: Dict[str, Any],
        user_id: int | None = None,
        scene: str = "general",
    ) -> Dict[str, Any]:
        """Send request to Ark /chat/completions endpoint (OpenAI-compatible)."""
        base_url = settings.ARK_BASE_URL.rstrip("/")
        headers = {
            "Authorization": f"Bearer {settings.ARK_API_KEY}",
            "Content-Type": "application/json",
        }
        request_id = uuid4().hex[:12]
        started_at = time.perf_counter()
        model = payload.get("model", settings.ARK_MODEL)

        logger.info(
            "ark_chat_request_start request_id=%s scene=%s user_id=%s model=%s",
            request_id,
            scene,
            user_id,
            model,
        )

        try:
            async with httpx.AsyncClient(timeout=settings.ARK_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
            response.raise_for_status()
            data = response.json()
            usage = self._extract_chat_completions_usage(data)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            self._save_ark_call_log(
                user_id=user_id,
                scene=scene,
                model=model,
                success=True,
                status_code=response.status_code,
                latency_ms=elapsed_ms,
                input_tokens=int(usage.get("prompt_tokens") or 0),
                output_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                error_message=None,
            )
            logger.info(
                "ark_chat_request_success request_id=%s scene=%s user_id=%s model=%s elapsed_ms=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                request_id,
                scene,
                user_id,
                model,
                elapsed_ms,
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            )
            return data
        except httpx.HTTPStatusError as e:
            detail = e.response.text if e.response is not None else str(e)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            self._save_ark_call_log(
                user_id=user_id,
                scene=scene,
                model=model,
                success=False,
                status_code=e.response.status_code if e.response is not None else None,
                latency_ms=elapsed_ms,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                error_message=detail[:2000],
            )
            logger.warning(
                "ark_chat_request_http_error request_id=%s scene=%s user_id=%s model=%s elapsed_ms=%s status=%s detail=%s",
                request_id,
                scene,
                user_id,
                model,
                elapsed_ms,
                e.response.status_code if e.response is not None else None,
                detail,
            )
            raise Exception(f"Ark API error: {detail}")
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            self._save_ark_call_log(
                user_id=user_id,
                scene=scene,
                model=model,
                success=False,
                status_code=None,
                latency_ms=elapsed_ms,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                error_message=str(e)[:2000],
            )
            logger.exception(
                "ark_chat_request_failed request_id=%s scene=%s user_id=%s model=%s elapsed_ms=%s",
                request_id,
                scene,
                user_id,
                model,
                elapsed_ms,
            )
            raise Exception(f"Failed to call Ark API: {str(e)}")

    def _extract_chat_completions_text(self, data: Dict[str, Any]) -> str:
        """Extract text from OpenAI-compatible chat/completions response.
        
        Expected format:
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "..."
                    }
                }
            ]
        }
        """
        try:
            choices = data.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if content:
                    return content
        except Exception as e:
            logger.warning("Failed to extract text from chat/completions response: %s", e)

        # Fallback: return raw data as JSON string
        return json.dumps(data, ensure_ascii=False)

    def _extract_chat_completions_usage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage from OpenAI-compatible chat/completions response.
        
        Expected format:
        {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        """
        usage = data.get("usage") or {}
        return {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

    def _extract_ark_text(self, data: Dict[str, Any]) -> str:
        """Extract text from Ark responses payload with compatible fallback parsing."""
        if isinstance(data.get("output_text"), str) and data.get("output_text"):
            return data["output_text"]

        texts = []
        for output_item in data.get("output", []):
            for content_item in output_item.get("content", []):
                text = content_item.get("text")
                if text:
                    texts.append(text)
                nested_text = content_item.get("output_text")
                if nested_text:
                    texts.append(nested_text)

        if texts:
            return "\n".join(texts).strip()

        return json.dumps(data, ensure_ascii=False)

    def _extract_ark_usage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        usage = data.get("usage") or {}
        return {
            "input_tokens": usage.get("input_tokens") or usage.get("prompt_tokens"),
            "output_tokens": usage.get("output_tokens") or usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

    def _save_ark_call_log(
        self,
        user_id: int | None,
        scene: str,
        model: str,
        success: bool,
        status_code: int | None,
        latency_ms: int,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        error_message: str | None,
    ) -> None:
        if self.db is None:
            return
        try:
            record = ArkCallLog(
                user_id=user_id,
                scene=scene,
                provider="ark",
                model=model,
                endpoint="/chat/completions",
                success=success,
                status_code=status_code,
                latency_ms=max(int(latency_ms), 0),
                input_tokens=max(int(input_tokens), 0),
                output_tokens=max(int(output_tokens), 0),
                total_tokens=max(int(total_tokens), 0),
                error_message=error_message,
            )
            self.db.add(record)
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Failed to persist ark call log")
    
    async def rewrite_xiaohongshu(
        self,
        content: str,
        style: str = "casual",
        user_id: int | None = None,
        insight_ctx: dict | None = None,
    ) -> str:
        """Rewrite for Little Red Book style, optionally guided by insight context"""
        system_prompt = "你是小红书专业运营创作者，擅长贷款/金融业务内容创作。用中文回复。"

        ctx_block = ""
        if insight_ctx and insight_ctx.get("reference_count", 0) > 0:
            parts = []
            if insight_ctx.get("title_examples"):
                parts.append("《高互动标题参考》: " + " / ".join(insight_ctx["title_examples"][:3]))
            if insight_ctx.get("structure_examples"):
                parts.append("《常用结构》: " + "、".join(insight_ctx["structure_examples"][:3]))
            if insight_ctx.get("hook_examples"):
                parts.append("《开头钉子类型》: " + "、".join(insight_ctx["hook_examples"][:3]))
            if insight_ctx.get("pain_point_examples"):
                parts.append("《目标群体直击痛点》: " + "、".join(insight_ctx["pain_point_examples"][:5]))
            if insight_ctx.get("style_summary"):
                parts.append("《参考风格》: " + insight_ctx["style_summary"])
            if insight_ctx.get("risk_reminder"):
                parts.append("《风险提醒》: " + insight_ctx["risk_reminder"])
            if parts:
                ctx_block = "\n\n【洞察库参考特征（仅供学习风格，不要复制原文）】\n" + "\n".join(parts)

        prompt = f"""请将以下内容改写为小红书风格笔记：

【原始内容】
{content}
{ctx_block}

【改写要求】
- 口语化、个人分享调调
- 适当加入 emoji 增加可读性
- 开头必须吸引眼球，让人想继续看
- 结尾带引导动作（评论/收藏/点赞）
- 不超过 1000 字
- 禁止使用【一定放款】【100%下款】等违规词语"""
        return await self.call_llm(prompt, system_prompt, user_id=user_id, scene="rewrite_xiaohongshu")
    
    async def rewrite_douyin(
        self,
        content: str,
        user_id: int | None = None,
        insight_ctx: dict | None = None,
    ) -> str:
        """Rewrite for Douyin short video script, optionally guided by insight context"""
        system_prompt = "你是抗音短视频剧本専家，擅长金融获客类内容。用中文回复。"

        ctx_block = ""
        if insight_ctx and insight_ctx.get("reference_count", 0) > 0:
            parts = []
            if insight_ctx.get("hook_examples"):
                parts.append("《开头钉子类型》: " + "、".join(insight_ctx["hook_examples"][:3]))
            if insight_ctx.get("pain_point_examples"):
                parts.append("《小音同类目标痛点》: " + "、".join(insight_ctx["pain_point_examples"][:5]))
            if insight_ctx.get("structure_examples"):
                parts.append("《内容结构参考》: " + "、".join(insight_ctx["structure_examples"][:3]))
            if insight_ctx.get("risk_reminder"):
                parts.append("《风险提醒》: " + insight_ctx["risk_reminder"])
            if parts:
                ctx_block = "\n\n【洞察库参考特征（仅供学习风格，不要复制原文）】\n" + "\n".join(parts)

        prompt = f"""根据以下内容创作抗音口播剧本：

【原始内容】
{content}
{ctx_block}

【剧本要求】
- 口播化，按不超过 60 秒的语速写
- 准头 3 秒内必须有钉子，让观众继续看
- 句子短冲，节奏感强
- 结尾带明确引导动作
- 不超过 300 字
- 禁用违规承诺词语"""
        return await self.call_llm(prompt, system_prompt, user_id=user_id, scene="rewrite_douyin")
    
    async def rewrite_zhihu(
        self,
        content: str,
        user_id: int | None = None,
        insight_ctx: dict | None = None,
    ) -> str:
        """Rewrite for Zhihu answer style, optionally guided by insight context"""
        system_prompt = "你是知乎专业回答作者，擅长金融信贷误区遇坑、个人信贷策略类回答。用中文回复。"

        ctx_block = ""
        if insight_ctx and insight_ctx.get("reference_count", 0) > 0:
            parts = []
            if insight_ctx.get("pain_point_examples"):
                parts.append("《目标群体痛点》: " + "、".join(insight_ctx["pain_point_examples"][:6]))
            if insight_ctx.get("structure_examples"):
                parts.append("《内容结构参考》: " + "、".join(insight_ctx["structure_examples"][:3]))
            if insight_ctx.get("style_summary"):
                parts.append("《同类内容风格》: " + insight_ctx["style_summary"])
            if insight_ctx.get("risk_reminder"):
                parts.append("《风险提醒》: " + insight_ctx["risk_reminder"])
            if parts:
                ctx_block = "\n\n【洞察库参考特征（仅供学习风格，不要复制原文）】\n" + "\n".join(parts)

        prompt = f"""将以下内容改写为知乎专业回答：

【原始内容】
{content}
{ctx_block}

【回答要求】
- 专业、逻辑清晰，结构化表达
- 要有分析过程，不只给结论
- 加入理性提醒和风险说明
- 禁用担保、承诺类违规词语"""
        return await self.call_llm(prompt, system_prompt, user_id=user_id, scene="rewrite_zhihu")
    
    async def generate_comment_reply(self, original_content: str, comment: str) -> str:
        """Generate reply to comments"""
        system_prompt = """You are a social media engagement expert.
        
Generate 3 reply options:
1. Rational and helpful
2. Warm and friendly
3. Brief and direct

Requirements:
- Natural tone, not salesy
- Answer the question first
- Avoid contact requests
- No spam or pressure"""
        
        prompt = f"Original content: {original_content}\n\nComment: {comment}\n\nGenerate 3 reply options."
        return await self.call_llm(prompt, system_prompt)
    
    async def extract_structure(self, content: str) -> Dict[str, Any]:
        """Extract content structure and key elements"""
        system_prompt = """Analyze this content and extract:
- Main topic
- Target audience
- Key pain points
- Content structure (opening/middle/ending)
- Strong hooks
- Potential objections
- Reusable angles

Return as JSON."""
        
        prompt = f"Analyze and extract structure:\n\n{content}"
        response = await self.call_llm(prompt, system_prompt)
        
        try:
            return json.loads(response)
        except:
            return {"raw_response": response}
