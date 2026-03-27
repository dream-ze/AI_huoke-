from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/collect", tags=["collect"])

_COLLECT_DEPRECATION_DETAIL = {
    "message": "旧 collect 接口已下线，请迁移到新素材管道。",
    "replacement": {
        "manual_create": "/api/v1/material/inbox/manual",
        "keyword_task": "/api/v1/collector/tasks/keyword",
        "materials": "/api/v2/materials",
        "extract": "/api/v2/collect/extract-from-url",
    },
}


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def deprecated_collect_routes(path: str):
    _ = path
    raise HTTPException(status_code=410, detail=_COLLECT_DEPRECATION_DETAIL)
