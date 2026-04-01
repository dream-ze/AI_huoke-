"""MVP模型管理路由模块"""

from app.core.config import settings
from app.core.permissions import require_roles
from app.services.embedding_service import get_embedding_service
from app.services.model_manager_service import get_model_manager_service
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


@router.get("/models/embedding")
async def list_embedding_models():
    """列出可用 embedding 模型"""
    model_service = get_model_manager_service()
    embedding_service = get_embedding_service()

    # 获取配置中的模型列表
    config_models = model_service.get_available_embedding_models()

    # 获取当前选中的模型
    current_model = embedding_service.get_current_model()

    return {
        "models": config_models,
        "current_model": current_model,
        "default_model": getattr(settings, "DEFAULT_EMBEDDING_MODEL", "nomic-embed-text"),
    }


@router.get("/models/llm")
async def list_llm_models():
    """列出可用 LLM 模型"""
    model_service = get_model_manager_service()

    # 获取配置中的模型列表
    config_models = model_service.get_available_llm_models()

    return {"models": config_models, "default_model": getattr(settings, "DEFAULT_LLM_MODEL", "qwen2.5")}


@router.post("/models/embedding/select")
async def select_embedding_model(request: dict, _user=Depends(require_roles("admin"))):
    """
    切换当前 embedding 模型 - 仅管理员

    请求体：
    - model_name: 模型名称（如 "nomic-embed-text", "qwen3-embedding"）
    """
    model_name = request.get("model_name")
    if not model_name:
        raise HTTPException(status_code=400, detail="缺少 model_name 参数")

    embedding_service = get_embedding_service()
    result = embedding_service.select_model(model_name)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/models/ollama/status")
async def get_ollama_status():
    """获取 Ollama 服务状态及已安装模型"""
    model_service = get_model_manager_service()

    models = await model_service.list_ollama_models()

    return {"status": "running" if models else "unavailable", "models": models, "count": len(models)}


@router.post("/models/ollama/pull")
async def pull_ollama_model(request: dict, _user=Depends(require_roles("admin"))):
    """
    拉取 Ollama 模型 - 仅管理员

    请求体：
    - model_name: 模型名称（如 "qwen2.5", "nomic-embed-text:latest"）
    """
    model_name = request.get("model_name")
    if not model_name:
        raise HTTPException(status_code=400, detail="缺少 model_name 参数")

    model_service = get_model_manager_service()
    result = await model_service.pull_ollama_model(model_name)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/models/ollama/{model_name}/info")
async def get_ollama_model_info(model_name: str):
    """获取 Ollama 模型详细信息"""
    model_service = get_model_manager_service()
    result = await model_service.get_model_info(model_name)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result


@router.get("/models/ollama/{model_name}/check")
async def check_ollama_model(model_name: str):
    """检查 Ollama 模型是否可用"""
    model_service = get_model_manager_service()
    result = await model_service.check_model_status(model_name)

    return result


@router.post("/models/benchmark")
async def benchmark_model(request: dict):
    """模型性能对标

    请求体：
    - model_name: 模型名称（必需）
    - test_text: 测试文本（可选，默认使用内置测试文本）
    """
    model_name = request.get("model_name")
    test_text = request.get("test_text")

    if not model_name:
        raise HTTPException(status_code=400, detail="缺少 model_name 参数")

    model_service = get_model_manager_service()
    result = await model_service.benchmark_model(model_name, test_text)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result
