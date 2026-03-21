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
    ) -> str:
        """Call LLM (Ollama or Cloud)"""
        
        if use_cloud and settings.ARK_API_KEY:
            return await self._call_ark(prompt, system_prompt, user_id=user_id, scene=scene)
        else:
            return await self._call_ollama(prompt, system_prompt)
    
    async def _call_ollama(self, prompt: str, system_prompt: str = "") -> str:
        """Call Ollama local model"""
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "temperature": 0.7,
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
    ) -> str:
        """Call Volcano Engine (Fire Engine)"""
        if not settings.ARK_API_KEY:
            raise Exception("ARK_API_KEY is not configured")

        user_text = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
        payload = {
            "model": settings.ARK_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": user_text,
                        }
                    ],
                }
            ],
        }

        data = await self._post_ark_responses(payload, user_id=user_id, scene=scene)
        return self._extract_ark_text(data)

    async def analyze_image_with_ark(
        self,
        image_url: str,
        text: str,
        model: str | None = None,
        user_id: int | None = None,
    ) -> Dict[str, Any]:
        """Analyze image content with Ark multimodal responses API."""
        if not settings.ARK_API_KEY:
            raise Exception("ARK_API_KEY is not configured")

        payload = {
            "model": model or settings.ARK_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": image_url,
                        },
                        {
                            "type": "input_text",
                            "text": text,
                        },
                    ],
                }
            ],
        }

        data = await self._post_ark_responses(payload, user_id=user_id, scene="vision")
        answer = self._extract_ark_text(data)
        return {
            "model": payload["model"],
            "image_url": image_url,
            "text": text,
            "answer": answer,
        }

    async def _post_ark_responses(
        self,
        payload: Dict[str, Any],
        user_id: int | None = None,
        scene: str = "general",
    ) -> Dict[str, Any]:
        """Send request to Ark /responses endpoint."""
        base_url = settings.ARK_BASE_URL.rstrip("/")
        headers = {
            "Authorization": f"Bearer {settings.ARK_API_KEY}",
            "Content-Type": "application/json",
        }
        request_id = uuid4().hex[:12]
        started_at = time.perf_counter()
        model = payload.get("model", settings.ARK_MODEL)

        logger.info(
            "ark_request_start request_id=%s scene=%s user_id=%s model=%s",
            request_id,
            scene,
            user_id,
            model,
        )

        try:
            async with httpx.AsyncClient(timeout=settings.ARK_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{base_url}/responses",
                    json=payload,
                    headers=headers,
                )
            response.raise_for_status()
            data = response.json()
            usage = self._extract_ark_usage(data)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            self._save_ark_call_log(
                user_id=user_id,
                scene=scene,
                model=model,
                success=True,
                status_code=response.status_code,
                latency_ms=elapsed_ms,
                input_tokens=int(usage.get("input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                error_message=None,
            )
            logger.info(
                "ark_request_success request_id=%s scene=%s user_id=%s model=%s elapsed_ms=%s input_tokens=%s output_tokens=%s total_tokens=%s",
                request_id,
                scene,
                user_id,
                model,
                elapsed_ms,
                usage.get("input_tokens"),
                usage.get("output_tokens"),
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
                "ark_request_http_error request_id=%s scene=%s user_id=%s model=%s elapsed_ms=%s status=%s detail=%s",
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
                "ark_request_failed request_id=%s scene=%s user_id=%s model=%s elapsed_ms=%s",
                request_id,
                scene,
                user_id,
                model,
                elapsed_ms,
            )
            raise Exception(f"Failed to call Ark API: {str(e)}")

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
                endpoint="/responses",
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
    
    async def rewrite_xiaohongshu(self, content: str, style: str = "casual", user_id: int | None = None) -> str:
        """Rewrite for Little Red Book style"""
        system_prompt = """You are a content editor specialized in adapting content for Little Red Book (小红书) style.
        
Requirements:
- Write in casual, personal sharing tone
- Reduce marketing feel
- Add appropriate emojis
- Include engagement hooks
- Keep under 1000 characters
- Avoid absolute promises"""
        
        prompt = f"Please rewrite this content in Little Red Book style:\n\n{content}"
        return await self.call_llm(prompt, system_prompt, user_id=user_id, scene="rewrite_xiaohongshu")
    
    async def rewrite_douyin(self, content: str, user_id: int | None = None) -> str:
        """Rewrite for Douyin (TikTok) script"""
        system_prompt = """You are a professional short video script writer for Douyin.
        
Requirements:
- Write as a speaking script (45-60 seconds)
- Add a hook in the first 3 seconds
- Use short, punchy sentences
- Natural, conversational tone
- Add relevant keywords
- Include a clear call-to-action"""
        
        prompt = f"Create a speaking script based on this content:\n\n{content}"
        return await self.call_llm(prompt, system_prompt, user_id=user_id, scene="rewrite_douyin")
    
    async def rewrite_zhihu(self, content: str, user_id: int | None = None) -> str:
        """Rewrite for Zhihu answer style"""
        system_prompt = """You are a professional answer writer for Zhihu.
        
Requirements:
- Professional, logical tone
- Well-structured with clear points
- Include analysis and thinking process
- Not just results, but methodology
- Add rational reminders
- Support with evidence where possible"""
        
        prompt = f"Rewrite as a Zhihu answer:\n\n{content}"
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
