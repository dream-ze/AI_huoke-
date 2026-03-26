from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/content", tags=["content-deprecated"])

_DEPRECATION_DETAIL = {
    "message": "旧内容接口已下线，请迁移到 /api/v2/materials 与 /api/v2/collect/ingest-page",
    "replacement": {
        "list": "/api/v2/materials",
        "detail": "/api/v2/materials/{id}",
        "create": "/api/v2/collect/ingest-page",
    },
}


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def deprecated_content_routes(path: str):
    raise HTTPException(status_code=410, detail=_DEPRECATION_DETAIL)
