"""模型池管理服务 - 支持 Ollama 本地模型管理

功能：
- 列出 Ollama 已拉取的模型
- 拉取新的 Ollama 模型
- 检查模型状态
- 获取模型详细信息
- 模型性能对标
"""
import asyncio
import logging
import time
from typing import List, Optional, Dict, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelManagerService:
    """模型池管理服务"""

    def __init__(self):
        self.ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')

    async def list_ollama_models(self) -> List[Dict[str, Any]]:
        """列出 Ollama 已拉取的模型
        
        GET http://localhost:11434/api/tags
        
        Returns:
            模型列表
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                
                models = []
                for model in data.get("models", []):
                    models.append({
                        "name": model.get("name"),
                        "model": model.get("model"),
                        "modified_at": model.get("modified_at"),
                        "size": model.get("size"),
                        "digest": model.get("digest"),
                        "details": model.get("details", {})
                    })
                return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def pull_ollama_model(self, model_name: str) -> Dict[str, Any]:
        """拉取新的 Ollama 模型
        
        POST http://localhost:11434/api/pull
        
        Args:
            model_name: 模型名称（如 "qwen2.5", "nomic-embed-text"）
            
        Returns:
            拉取结果
        """
        if not model_name or not model_name.strip():
            return {
                "success": False,
                "error": "模型名称不能为空"
            }
        
        model_name = model_name.strip()
        
        try:
            logger.info(f"Starting to pull Ollama model: {model_name}")
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/pull",
                    json={"name": model_name, "stream": False}
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "success":
                    logger.info(f"Successfully pulled Ollama model: {model_name}")
                    return {
                        "success": True,
                        "model": model_name,
                        "status": "pulled",
                        "message": f"模型 {model_name} 拉取成功"
                    }
                else:
                    return {
                        "success": False,
                        "model": model_name,
                        "status": data.get("status"),
                        "error": data.get("error", "拉取失败")
                    }
        except httpx.TimeoutException:
            logger.error(f"Timeout while pulling Ollama model: {model_name}")
            return {
                "success": False,
                "model": model_name,
                "error": "拉取超时，模型可能较大，请稍后重试"
            }
        except Exception as e:
            logger.error(f"Failed to pull Ollama model {model_name}: {e}")
            return {
                "success": False,
                "model": model_name,
                "error": f"拉取失败: {str(e)}"
            }

    async def check_model_status(self, model_name: str) -> Dict[str, Any]:
        """检查模型是否可用
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型状态信息
        """
        if not model_name:
            return {
                "available": False,
                "error": "模型名称不能为空"
            }
        
        try:
            # 先检查模型是否在列表中
            models = await self.list_ollama_models()
            model_names = [m.get("name", "").split(":")[0] for m in models]
            
            # 尝试简单的嵌入测试来验证模型可用性
            test_text = "test"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": model_name, "prompt": test_text}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding")
                    if embedding and len(embedding) > 0:
                        return {
                            "available": True,
                            "model": model_name,
                            "dimension": len(embedding),
                            "message": "模型可用"
                        }
                
                return {
                    "available": False,
                    "model": model_name,
                    "status_code": response.status_code,
                    "message": "模型不可用或响应异常"
                }
                
        except Exception as e:
            logger.error(f"Failed to check model status for {model_name}: {e}")
            return {
                "available": False,
                "model": model_name,
                "error": str(e)
            }

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型详细信息（大小、参数量等）
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型详细信息
        """
        if not model_name:
            return {
                "success": False,
                "error": "模型名称不能为空"
            }
        
        try:
            models = await self.list_ollama_models()
            
            for model in models:
                if model.get("name", "").startswith(model_name):
                    details = model.get("details", {})
                    return {
                        "success": True,
                        "name": model.get("name"),
                        "size": model.get("size"),
                        "size_human": self._format_size(model.get("size", 0)),
                        "modified_at": model.get("modified_at"),
                        "digest": model.get("digest"),
                        "format": details.get("format"),
                        "family": details.get("family"),
                        "families": details.get("families"),
                        "parameter_size": details.get("parameter_size"),
                        "quantization_level": details.get("quantization_level")
                    }
            
            return {
                "success": False,
                "model": model_name,
                "error": "模型未找到"
            }
            
        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            return {
                "success": False,
                "model": model_name,
                "error": str(e)
            }

    async def benchmark_model(self, model_name: str, test_text: Optional[str] = None) -> Dict[str, Any]:
        """模型性能对标（延迟、质量评分）
        
        Args:
            model_name: 模型名称
            test_text: 测试文本，None 则使用默认文本
            
        Returns:
            性能测试结果
        """
        if not model_name:
            return {
                "success": False,
                "error": "模型名称不能为空"
            }
        
        # 默认测试文本
        if not test_text:
            test_text = (
                "这是一段用于测试模型性能的文本。"
                "贷款是银行或其他金融机构按一定利率借出货币资金的信用活动形式。"
                "广义的贷款指贷款、贴现、透支等出贷资金的总称。"
            )
        
        try:
            # 检查模型是否可用
            status = await self.check_model_status(model_name)
            if not status.get("available"):
                return {
                    "success": False,
                    "model": model_name,
                    "error": f"模型不可用: {status.get('message', '未知错误')}"
                }
            
            # 执行多次测试取平均
            latencies = []
            dimensions = []
            
            for i in range(3):
                start_time = time.time()
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.ollama_base_url}/api/embeddings",
                        json={"model": model_name, "prompt": test_text}
                    )
                    response.raise_for_status()
                    data = response.json()
                    embedding = data.get("embedding", [])
                    
                    if embedding:
                        dimensions.append(len(embedding))
                
                latency = (time.time() - start_time) * 1000  # 转换为毫秒
                latencies.append(latency)
                
                # 短暂间隔避免过载
                if i < 2:
                    await asyncio.sleep(0.1)
            
            avg_latency = sum(latencies) / len(latencies)
            dimension = dimensions[0] if dimensions else 0
            
            # 性能评级
            performance_rating = self._rate_performance(avg_latency)
            
            return {
                "success": True,
                "model": model_name,
                "dimension": dimension,
                "latency_ms": {
                    "avg": round(avg_latency, 2),
                    "min": round(min(latencies), 2),
                    "max": round(max(latencies), 2)
                },
                "performance_rating": performance_rating,
                "test_text_length": len(test_text),
                "message": "性能测试完成"
            }
            
        except Exception as e:
            logger.error(f"Failed to benchmark model {model_name}: {e}")
            return {
                "success": False,
                "model": model_name,
                "error": str(e)
            }

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小
        
        Args:
            size_bytes: 字节数
            
        Returns:
            格式化后的字符串
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"

    def _rate_performance(self, latency_ms: float) -> str:
        """根据延迟评级性能
        
        Args:
            latency_ms: 延迟（毫秒）
            
        Returns:
            性能评级
        """
        if latency_ms < 100:
            return "excellent"
        elif latency_ms < 300:
            return "good"
        elif latency_ms < 1000:
            return "fair"
        else:
            return "slow"

    def get_available_embedding_models(self) -> Dict[str, Any]:
        """获取配置的可用 embedding 模型列表
        
        Returns:
            可用模型信息
        """
        models = settings.EMBEDDING_MODELS
        result = {}
        for name, config in models.items():
            result[name] = {
                "name": name,
                "provider": config.get("provider"),
                "dimension": config.get("dimension"),
                "description": config.get("description"),
                "ollama_name": config.get("ollama_name")
            }
        return result

    def get_available_llm_models(self) -> Dict[str, Any]:
        """获取配置的可用 LLM 模型列表
        
        Returns:
            可用模型信息
        """
        models = settings.LLM_MODELS
        result = {}
        for name, config in models.items():
            result[name] = {
                "name": name,
                "provider": config.get("provider"),
                "description": config.get("description"),
                "ollama_name": config.get("ollama_name"),
                "ark_model": config.get("ark_model")
            }
        return result


# 全局单例
_model_manager_service = None


def get_model_manager_service() -> ModelManagerService:
    """获取模型管理服务单例"""
    global _model_manager_service
    if _model_manager_service is None:
        _model_manager_service = ModelManagerService()
    return _model_manager_service
