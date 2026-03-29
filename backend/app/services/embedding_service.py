"""向量化服务 - 支持火山方舟和Ollama两种Embedding模式

改造说明 (Task #4):
- 统一使用 Ollama embedding 作为默认引擎（保留火山方舟作为备选）
- 不再做维度填充（返回原生维度向量）
- 新增 batch_embed 方法
- 返回类型为 List[float]，可直接写入 pgvector Vector 列
"""
import logging
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding向量化服务 - 优先使用 Ollama，保留火山方舟作为备选"""

    def __init__(self):
        from app.core.config import settings

        # Ollama 配置（默认引擎）
        self.ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_model = getattr(settings, 'OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')

        # 火山方舟配置（备选）
        self.use_cloud = getattr(settings, 'USE_CLOUD_MODEL', False)
        self.ark_api_key = getattr(settings, 'ARK_API_KEY', '')
        self.ark_model = getattr(settings, 'ARK_EMBEDDING_MODEL', 'doubao-embedding-large-text-240915')
        self.ark_base_url = getattr(settings, 'ARK_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3')

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成向量，优先使用 Ollama

        Args:
            text: 输入文本
        Returns:
            向量列表，失败返回 None
        """
        if self.use_cloud and self.ark_api_key:
            return await self._embed_volcano(text)
        return await self._embed_ollama(text)

    async def batch_embed(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量向量化

        Args:
            texts: 文本列表
        Returns:
            向量列表（元素可能为 None 表示失败）
        """
        results = []
        for text in texts:
            emb = await self.generate_embedding(text)
            results.append(emb)
        return results

    async def _embed_ollama(self, text: str) -> Optional[List[float]]:
        """Ollama embedding - 默认引擎"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.ollama_model, "prompt": text}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding")
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            return None

    async def _embed_volcano(self, text: str) -> Optional[List[float]]:
        """火山方舟 embedding - 备选引擎"""
        if not self.ark_api_key:
            logger.warning("ARK_API_KEY not configured, skipping volcano embedding")
            return None

        url = f"{self.ark_base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.ark_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.ark_model,
            "input": [text],
            "encoding_format": "float"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                if data.get("data") and len(data["data"]) > 0:
                    return data["data"][0].get("embedding")
        except Exception as e:
            logger.error(f"Volcano embedding failed: {e}")
        return None


# 全局单例
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
