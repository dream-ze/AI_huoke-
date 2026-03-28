"""向量化服务 - 支持火山方舟和Ollama两种Embedding模式"""
import os
import json
import logging
import aiohttp
from typing import List, Optional

logger = logging.getLogger(__name__)

VECTOR_DIM = 1024  # 向量维度


class EmbeddingService:
    """Embedding向量化服务"""

    def __init__(self):
        # 火山方舟配置
        self.ark_api_key = os.getenv("ARK_API_KEY", "")
        self.ark_base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        self.ark_embedding_model = os.getenv("ARK_EMBEDDING_MODEL", "doubao-embedding-large-text-240915")

        # Ollama配置
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    async def generate_embedding(self, text: str, model: str = "volcano") -> Optional[List[float]]:
        """生成单条文本的embedding向量
        Args:
            text: 输入文本
            model: "volcano" 或 "local"
        Returns:
            向量列表，失败返回None
        """
        try:
            if model == "volcano":
                return await self._volcano_embedding(text)
            else:
                return await self._ollama_embedding(text)
        except Exception as e:
            logger.error(f"Embedding生成失败: {e}")
            return None

    async def generate_embeddings_batch(self, texts: List[str], model: str = "volcano") -> List[Optional[List[float]]]:
        """批量生成embedding
        Args:
            texts: 文本列表
            model: "volcano" 或 "local"
        Returns:
            向量列表
        """
        results = []
        for text in texts:
            emb = await self.generate_embedding(text, model)
            results.append(emb)
        return results

    async def _volcano_embedding(self, text: str) -> Optional[List[float]]:
        """调用火山方舟Embedding API"""
        if not self.ark_api_key:
            logger.warning("ARK_API_KEY未配置，跳过向量化")
            return None

        url = f"{self.ark_base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.ark_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.ark_embedding_model,
            "input": [text],
            "encoding_format": "float"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("data") and len(data["data"]) > 0:
                        embedding = data["data"][0].get("embedding", [])
                        # 如果维度不匹配，截断或填充
                        if len(embedding) > VECTOR_DIM:
                            embedding = embedding[:VECTOR_DIM]
                        elif len(embedding) < VECTOR_DIM:
                            embedding.extend([0.0] * (VECTOR_DIM - len(embedding)))
                        return embedding
                else:
                    error_text = await resp.text()
                    logger.error(f"火山Embedding API错误 {resp.status}: {error_text}")
        return None

    async def _ollama_embedding(self, text: str) -> Optional[List[float]]:
        """调用Ollama本地Embedding"""
        url = f"{self.ollama_base_url}/api/embeddings"
        payload = {
            "model": self.ollama_embedding_model,
            "prompt": text
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embedding = data.get("embedding", [])
                    if embedding:
                        if len(embedding) > VECTOR_DIM:
                            embedding = embedding[:VECTOR_DIM]
                        elif len(embedding) < VECTOR_DIM:
                            embedding.extend([0.0] * (VECTOR_DIM - len(embedding)))
                        return embedding
                else:
                    error_text = await resp.text()
                    logger.error(f"Ollama Embedding错误 {resp.status}: {error_text}")
        return None


# 全局单例
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
