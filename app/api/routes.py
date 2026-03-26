from fastapi import APIRouter
from app.schemas.detail import CollectDetailRequest, CollectDetailResponse
from app.schemas.request import CollectRequest
from app.schemas.result import CollectResponse
from app.services.collect_service import CollectService
from app.services.detail_service import DetailService

router = APIRouter()


@router.get("/health")
def health():
    return {"success": True, "message": "ok"}


@router.post("/api/collect/run", response_model=CollectResponse)
def run_collect(data: CollectRequest):
    return CollectService.run_collect(data)


@router.post("/api/collect/detail", response_model=CollectDetailResponse)
def collect_detail(data: CollectDetailRequest):
    return DetailService.fetch_detail(data)
