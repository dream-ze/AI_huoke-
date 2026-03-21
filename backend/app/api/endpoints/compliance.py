from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.schemas import ComplianceCheckRequest, ComplianceCheckResponse
from app.services import ComplianceService

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.post("/check", response_model=ComplianceCheckResponse)
def check_compliance(
    request: ComplianceCheckRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Check content compliance"""
    result = ComplianceService.check_compliance(request.content)
    return result
