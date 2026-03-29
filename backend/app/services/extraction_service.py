import json
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class ExtractionService:
    """使用 Ollama 结构化输出抽取内容维度信息"""
    
    EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "audience": {"type": "string", "description": "目标人群，如：年轻女性、职场新人、宝妈"},
            "scene": {"type": "string", "description": "使用场景，如：日常分享、产品测评、知识科普"},
            "style": {"type": "string", "description": "内容风格，如：轻松活泼、专业严谨、情感共鸣"},
            "content_type": {"type": "string", "description": "内容类型：案例/知识/规则/模板/测评/攻略"},
            "risk_points": {"type": "array", "items": {"type": "string"}, "description": "风险点列表，如违规词、敏感话题"},
            "hook_sentence": {"type": "string", "description": "标题或正文中的钩子句/爆点句"},
            "pain_point": {"type": "string", "description": "内容中提到的痛点"},
            "solution": {"type": "string", "description": "内容中提到的解决方案"},
            "topic": {"type": "string", "description": "主题分类：loan/credit/online_loan/housing_fund/insurance/investment/savings/other"},
            "summary": {"type": "string", "description": "50字以内的内容摘要"}
        },
        "required": ["audience", "scene", "style", "content_type", "topic", "summary"]
    }
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434", model: str = "qwen"):
        self.base_url = ollama_base_url
        self.model = model
    
    async def extract_structured(self, text: str, platform: str = "") -> dict:
        """调用 Ollama structured output 抽取结构化信息"""
        prompt = f"""你是一个内容分析专家。请分析以下{'来自' + platform + '的' if platform else ''}内容，提取结构化信息。

内容：
{text[:3000]}

请严格按照JSON格式返回分析结果。"""
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "format": self.EXTRACTION_SCHEMA,  # Ollama structured output
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("message", {}).get("content", "{}")
                return json.loads(content)
        except Exception as e:
            logger.error(f"Ollama extraction failed: {e}")
            # 返回默认空结构
            return {
                "audience": "", "scene": "", "style": "",
                "content_type": "other", "risk_points": [],
                "hook_sentence": "", "pain_point": "", "solution": "",
                "topic": "other", "summary": ""
            }
