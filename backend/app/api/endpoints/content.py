from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/content", tags=["content-deprecated"])

_DEPRECATION_DETAIL = {
    "message": "旧内容接口已下线，请迁移到 /api/v2/materials、/api/v1/material/inbox/manual 和 /api/v1/collector/tasks/keyword",
    "replacement": {
        "list": "/api/v2/materials",
        "detail": "/api/v2/materials/{id}",
        "manual_create": "/api/v1/material/inbox/manual",
        "collect_task": "/api/v1/collector/tasks/keyword",
    },
}


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def deprecated_content_routes(path: str):
    raise HTTPException(status_code=410, detail=_DEPRECATION_DETAIL)
