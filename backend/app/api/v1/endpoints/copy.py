from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.schemas import (
    CopyGenerateRequest,
    CopyGenerateResponse,
    MaterialTagRequest,
    TagResponse,
)
from app.services.copywriter import generate_copies
from app.services.tagger import tag_material

v1_copy_router = APIRouter(prefix="/copy", tags=["copy"])


@v1_copy_router.post("/tag", response_model=TagResponse)
def api_tag_material(
    payload: MaterialTagRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> TagResponse:
    tags = tag_material(payload.title, payload.content_text)
    return TagResponse(success=True, data=tags)


@v1_copy_router.post("/generate", response_model=CopyGenerateResponse)
def api_generate_copy(
    payload: CopyGenerateRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> CopyGenerateResponse:
    tags = tag_material(payload.title, payload.content_text)
    copies = generate_copies(payload, tags)
    return CopyGenerateResponse(success=True, tags=tags, copies=copies)
