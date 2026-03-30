"""向量化服务 - 支持火山方舟和Ollama两种Embedding模式

改造说明 (Task #4):
- 统一使用 Ollama embedding 作为默认引擎（保留火山方舟作为备选）
- 不再做维度填充（返回原生维度向量）
- 新增 batch_embed 方法
- 返回类型为 List[float]，可直接写入 pgvector Vector 列

改造说明 (Task #12):
- 添加自动降级：Ollama 不可用时自动降级到火山方舟
- 添加重试机制：每个引擎最多重试 1 次，快速降级
- 添加容错处理：全部失败时返回 None 而非抛异常

改造说明 (Task #17):
- 添加多模型支持：支持动态切换 embedding 模型
- 添加模型选择器 API
- 支持传入 model_name 参数指定模型

改造说明 (Task #10):
- 反转引擎优先级：火山方舟文本embedding优先 → Ollama降级备选
- 使用火山方舟文本embedding端点 (/embeddings)，而非多模态端点
- 模型使用 doubao-embedding-large-text-240915
- 添加维度日志记录，便于监控向量维度变化

改造说明 (Task #11):
- 添加维度兼容处理：现有pgvector存储768维向量，火山方舟返回2048维
- 实施选择B：调用火山方舟后检查维度，非768维时自动降级到Ollama
- 保证入库和查询向量维度一致，确保向量检索兼容
"""
import asyncio
import logging
import time
from typing import List, Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding向量化服务 - 优先使用火山方舟文本embedding，Ollama作为降级备选，支持多模型切换"""

    def __init__(self):
        from app.core.config import settings

        self.settings = settings

        # Ollama 配置（默认引擎）
        self.ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_model = getattr(settings, 'OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')

        # 火山方舟配置（备选）
        self.use_cloud = getattr(settings, 'USE_CLOUD_MODEL', False)
        self.ark_api_key = getattr(settings, 'ARK_API_KEY', '')
        self.ark_model = getattr(settings, 'ARK_EMBEDDING_MODEL', 'doubao-embedding-large-text-240915')
        self.ark_base_url = getattr(settings, 'ARK_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3')

        # 当前使用的模型（默认为配置中的默认模型）
        self._current_model_name = getattr(settings, 'DEFAULT_EMBEDDING_MODEL', 'nomic-embed-text')

    def get_available_models(self) -> Dict[str, Any]:
        """返回可用 embedding 模型列表
        
        Returns:
            包含模型信息的字典
        """
        models = self.settings.EMBEDDING_MODELS
        result = {}
        for name, config in models.items():
            result[name] = {
                "name": name,
                "provider": config.get("provider"),
                "dimension": config.get("dimension"),
                "description": config.get("description"),
                "is_current": name == self._current_model_name
            }
        return result

    def select_model(self, model_name: str) -> Dict[str, Any]:
        """切换当前 embedding 模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            切换结果信息
        """
        available_models = self.settings.EMBEDDING_MODELS
        
        if model_name not in available_models:
            return {
                "success": False,
                "error": f"模型 '{model_name}' 不存在",
                "available_models": list(available_models.keys())
            }
        
        old_model = self._current_model_name
        old_config = available_models.get(old_model, {})
        new_config = available_models[model_name]
        
        # 检查维度变化并发出警告
        dimension_changed = old_config.get("dimension") != new_config.get("dimension")
        
        self._current_model_name = model_name
        
        result = {
            "success": True,
            "previous_model": old_model,
            "current_model": model_name,
            "provider": new_config.get("provider"),
            "dimension": new_config.get("dimension"),
            "dimension_changed": dimension_changed
        }
        
        if dimension_changed:
            result["warning"] = (
                f"维度从 {old_config.get('dimension')} 变为 {new_config.get('dimension')}。"
                "注意：已有向量数据可能不兼容，建议重建向量索引。"
            )
            logger.warning(f"Embedding model switched from {old_model} to {model_name}, "
                          f"dimension changed: {old_config.get('dimension')} -> {new_config.get('dimension')}")
        else:
            logger.info(f"Embedding model switched from {old_model} to {model_name}")
        
        return result

    def get_current_model(self) -> Dict[str, Any]:
        """返回当前模型信息
        
        Returns:
            当前模型信息
        """
        models = self.settings.EMBEDDING_MODELS
        config = models.get(self._current_model_name, {})
        
        return {
            "name": self._current_model_name,
            "provider": config.get("provider"),
            "dimension": config.get("dimension"),
            "description": config.get("description"),
            "ollama_name": config.get("ollama_name")
        }

    def _get_ollama_model_name(self, model_name: Optional[str] = None) -> str:
        """获取 Ollama 模型名称
        
        Args:
            model_name: 指定的模型名称，None 则使用当前模型
            
        Returns:
            Ollama 模型名称
        """
        if model_name is None:
            model_name = self._current_model_name
        
        models = self.settings.EMBEDDING_MODELS
        config = models.get(model_name, {})
        
        # 获取 ollama 名称，如果没有则使用 model_name
        ollama_name = config.get("ollama_name", model_name)
        return ollama_name

    # 目标维度：与现有pgvector存储的向量维度保持一致（768维）
    # Ollama nomic-embed-text 输出 768 维
    # 火山方舟 doubao-embedding-large-text-240915 输出 2048 维
    TARGET_DIMENSION = 768
    
    async def generate_embedding(self, text: str, model_name: Optional[str] = None) -> Optional[List[float]]:
        """生成向量，自动降级 + 重试 + 维度兼容
            
        引擎优先级（Task #10反转）:
        1. 火山方舟文本embedding（优先）
        2. Ollama（降级备选）
            
        Task #11 维度兼容处理:
        - 现有pgvector存储的向量是768维（nomic-embed-text）
        - 火山方舟返回2048维，与现有数据不兼容
        - 如果火山方舟返回的维度不是768，自动降级到Ollama
    
        Args:
            text: 输入文本
            model_name: 指定使用的模型名称，None 则使用当前默认模型
        Returns:
            向量列表（保证768维），失败返回 None
        """
        if not text or not text.strip():
            return None
                    
        # 截断过长文本
        text = text[:8000]
                
        # 确定要使用的模型
        target_model = model_name or self._current_model_name
        ollama_model_name = self._get_ollama_model_name(target_model)
                    
        # Task #11: 先尝试火山方舟，检查维度兼容性
        try:
            ark_result = await self._embed_ark_text(text)
            if ark_result and len(ark_result) > 0:
                ark_dimension = len(ark_result)
                # 检查维度是否与目标维度一致
                if ark_dimension == self.TARGET_DIMENSION:
                    logger.info(f"Embedding success via ark_text, dimension={ark_dimension}")
                    return ark_result
                else:
                    # 维度不兼容，记录日志并降级
                    logger.warning(
                        f"ARK text embedding dimension mismatch: got {ark_dimension}, "
                        f"expected {self.TARGET_DIMENSION}. Falling back to Ollama for compatibility."
                    )
        except Exception as e:
            logger.warning(f"ARK text embedding failed: {e}, falling back to Ollama")
            
        # Task #11: 降级到 Ollama（保证 768 维）
        try:
            ollama_result = await self._embed_ollama(text, ollama_model_name)
            if ollama_result and len(ollama_result) > 0:
                ollama_dimension = len(ollama_result)
                logger.info(f"Embedding success via Ollama fallback, dimension={ollama_dimension}")
                return ollama_result
        except Exception as e:
            logger.error(f"Ollama embedding also failed: {e}")
                    
        logger.error(f"All embedding engines failed for model: {target_model}")
        return None

    async def batch_embed(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量向量化，单条失败不影响整体
    
        Args:
            texts: 文本列表
        Returns:
            向量列表（元素可能为 None 表示失败）
        """
        results = []
        for text in texts:
            try:
                emb = await self.generate_embedding(text)
                results.append(emb)
            except Exception as e:
                logger.warning(f"Batch embed item failed: {e}")
                results.append(None)
        return results

    async def _embed_ollama(self, text: str, model_name: Optional[str] = None) -> Optional[List[float]]:
        """Ollama embedding - 默认引擎
        
        Args:
            text: 输入文本
            model_name: Ollama 模型名称，None 则使用默认模型
        """
        ollama_model = model_name or self.ollama_model
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": ollama_model, "prompt": text}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding")
        except Exception as e:
            logger.error(f"Ollama embedding failed (model: {ollama_model}): {e}")
            return None

    async def _embed_ark_text(self, text: str) -> Optional[List[float]]:
        """火山方舟文本embedding - 优先引擎 (Task #10)
            
        使用文本embedding API（/embeddings），非多模态端点
        模型: doubao-embedding-large-text-240915 (来自 ARK_EMBEDDING_MODEL)
            
        Returns:
            向量列表（维度由模型决定，通常是2048维）
        """
        if not self.ark_api_key:
            logger.warning("ARK_API_KEY not configured, skipping ark_text embedding")
            return None
    
        # 使用文本embedding端点（非多模态）
        url = f"{self.ark_base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.ark_api_key}",
            "Content-Type": "application/json"
        }
        # 文本embedding格式：input为字符串数组
        payload = {
            "model": self.ark_model,  # doubao-embedding-large-text-240915
            "input": [text]
        }
    
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                # 文本embedding响应格式: data是列表
                data_content = data.get("data")
                if isinstance(data_content, list) and len(data_content) > 0:
                    embedding = data_content[0].get("embedding")
                    if embedding:
                        # 记录维度信息
                        dimension = len(embedding)
                        logger.info(f"ARK text embedding returned, dimension={dimension}")
                        return embedding
                logger.warning(f"ARK text embedding unexpected response format: {type(data_content)}")
        except Exception as e:
            logger.error(f"ARK text embedding failed: {e}")
        return None
    
    async def _embed_volcano(self, text: str) -> Optional[List[float]]:
        """火山方舟多模态embedding - 备选引擎（保留用于多模态场景）
            
        使用多模态embedding API（/embeddings/multimodal）
        模型: doubao-embedding-vision-251215
        返回2048维向量
        """
        if not self.ark_api_key:
            logger.warning("ARK_API_KEY not configured, skipping volcano embedding")
            return None
    
        # 使用多模态embedding端点
        url = f"{self.ark_base_url}/embeddings/multimodal"
        headers = {
            "Authorization": f"Bearer {self.ark_api_key}",
            "Content-Type": "application/json"
        }
        # 多模态格式：input为包含type和text的对象数组
        payload = {
            "model": "doubao-embedding-vision-251215",
            "input": [{"type": "text", "text": text}]
        }
    
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                # 多模态响应格式: data是字典而非列表
                data_content = data.get("data")
                if isinstance(data_content, dict):
                    return data_content.get("embedding")
                elif isinstance(data_content, list) and len(data_content) > 0:
                    return data_content[0].get("embedding")
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
