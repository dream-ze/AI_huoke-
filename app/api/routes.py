from fastapi import APIRouter
from app.schemas.request import CollectRequest
from app.schemas.result import CollectResponse
from app.services.collect_service import CollectService

router = APIRouter()


@router.get("/health")
def health():
    return {"success": True, "message": "ok"}


@router.post("/api/collect/run", response_model=CollectResponse)
def run_collect(data: CollectRequest):
    return CollectService.run_collect(data)
