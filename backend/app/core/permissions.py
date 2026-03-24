from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models import User


def require_roles(*allowed_roles: str):
    """Return dependency that checks user role against allowed roles."""

    def _checker(
        current_user: dict = Depends(verify_token),
        db: Session = Depends(get_db),
    ) -> dict:
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        role = (user.role or "operator").lower()
        if allowed_roles and role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")

        return {
            "user_id": user.id,
            "role": role,
        }

    return _checker
