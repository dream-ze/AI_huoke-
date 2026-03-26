from fastapi import APIRouter
from pathlib import Path

from app.schemas.detail import CollectDetailRequest, CollectDetailResponse
from app.schemas.request import CollectRequest
from app.schemas.result import CollectResponse
from app.services.collect_service import CollectService
from app.services.detail_service import DetailService

router = APIRouter()


@router.get("/health")
def health():
    state_path = Path(__file__).resolve().parents[2] / "xiaohongshu_state.json"
    return {
        "success": True,
        "message": "ok",
        "browser_ready": True,
        "login_state_ready": state_path.exists(),
        "storage_state_exists": state_path.exists(),
    }


@router.get("/api/platforms")
def platforms():
    return [
        {
            "platform": "xiaohongshu",
            "enabled": True,
            "capabilities": ["search", "detail"],
            "need_login": True,
        }
    ]


@router.post("/api/collect/run", response_model=CollectResponse)
def run_collect(data: CollectRequest):
    return CollectService.run_collect(data)


@router.post("/api/collect/detail", response_model=CollectDetailResponse)
def collect_detail(data: CollectDetailRequest):
    return DetailService.fetch_detail(data)
