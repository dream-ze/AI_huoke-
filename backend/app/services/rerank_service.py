"""
Rerank 语义重排序服务
使用 LLM 对检索召回的文档按语义相关性重新排序
"""
import logging
import json
from typing import List, Dict, Optional
import httpx

logger = logging.getLogger(__name__)


class RerankService:
    def __init__(self):
        from app.core.config import settings
        self.ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_model = getattr(settings, 'OLLAMA_MODEL', 'qwen')
        self.ark_api_key = getattr(settings, 'ARK_API_KEY', '')
        self.ark_model = getattr(settings, 'ARK_MODEL', '')
        self.use_cloud = getattr(settings, 'USE_CLOUD_MODEL', False)

    async def rerank(self, query: str, documents: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        对文档列表按与 query 的语义相关性重新排序

        Args:
            query: 用户查询
            documents: 文档列表，每个文档需包含 'content' 和 'title' 字段
            top_k: 返回前 k 个结果

        Returns:
            重排后的文档列表，每个文档增加 'rerank_score' 字段
        """
        if not documents or not query:
            return documents[:top_k]

        if len(documents) <= 1:
            return documents

        try:
            # 方法1: 使用 LLM 打分
            scored_docs = await self._llm_rerank(query, documents)
            # 按分数降序排列
            scored_docs.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
            return scored_docs[:top_k]
        except Exception as e:
            logger.warning(f"LLM rerank failed, falling back to embedding similarity: {e}")
            try:
                # 方法2: 降级到 embedding 相似度重排
                scored_docs = await self._embedding_rerank(query, documents)
                scored_docs.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
                return scored_docs[:top_k]
            except Exception as e2:
                logger.warning(f"Embedding rerank also failed: {e2}")
                # 方法3: 最终降级，保持原序
                return documents[:top_k]

    async def _llm_rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        """使用 LLM 对每个文档评估相关性分数"""
        # 构建批量评分 prompt
        doc_texts = []
        for i, doc in enumerate(documents):
            title = doc.get('title', '')
            content = doc.get('content', '')[:200]
            doc_texts.append(f"[文档{i+1}] {title}: {content}")

        prompt = f"""你是一个内容相关性评估专家。请评估以下文档与查询的相关性。

查询: {query}

文档列表:
{chr(10).join(doc_texts)}

请为每个文档打一个0-10的相关性分数，10表示最相关。
请严格按JSON格式返回: {{"scores": [分数1, 分数2, ...]}}"""

        try:
            if self.use_cloud and self.ark_api_key:
                scores = await self._call_ark_for_scores(prompt)
            else:
                scores = await self._call_ollama_for_scores(prompt)

            for i, doc in enumerate(documents):
                doc['rerank_score'] = scores[i] if i < len(scores) else 0
            return documents
        except Exception as e:
            raise e

    async def _call_ollama_for_scores(self, prompt: str) -> List[float]:
        """调用 Ollama 获取评分"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "format": {
                        "type": "object",
                        "properties": {
                            "scores": {"type": "array", "items": {"type": "number"}}
                        },
                        "required": ["scores"]
                    },
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
            )
            response.raise_for_status()
            result = response.json()
            content = json.loads(result["message"]["content"])
            return content.get("scores", [])

    async def _call_ark_for_scores(self, prompt: str) -> List[float]:
        """调用火山方舟获取评分"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.ark_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.ark_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                }
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("scores", [])

    async def _embedding_rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        """使用 embedding 余弦相似度重排"""
        from app.services.embedding_service import EmbeddingService
        emb_service = EmbeddingService()

        query_emb = await emb_service.generate_embedding(query)
        if not query_emb:
            return documents

        import math
        for doc in documents:
            doc_text = f"{doc.get('title', '')} {doc.get('content', '')[:300]}"
            doc_emb = await emb_service.generate_embedding(doc_text)
            if doc_emb:
                # 余弦相似度
                dot = sum(a * b for a, b in zip(query_emb, doc_emb))
                norm_q = math.sqrt(sum(a * a for a in query_emb))
                norm_d = math.sqrt(sum(a * a for a in doc_emb))
                similarity = dot / (norm_q * norm_d) if norm_q > 0 and norm_d > 0 else 0
                doc['rerank_score'] = similarity * 10  # 归一化到 0-10
            else:
                doc['rerank_score'] = 0

        return documents
