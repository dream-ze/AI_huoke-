from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sqlalchemy.exc import IntegrityError


class UserIntegrityErrorType(str, Enum):
    USERNAME_OR_EMAIL_CONFLICT = "username_or_email_conflict"
    USERS_PKEY_CONFLICT = "users_pkey_conflict"
    OTHER = "other"


@dataclass(frozen=True)
class UserIntegrityErrorClassification:
    error_type: UserIntegrityErrorType
    detail: str
    constraint_name: Optional[str] = None


def classify_user_create_integrity_error(exc: IntegrityError) -> UserIntegrityErrorClassification:
    """Classify user create integrity errors by SQLSTATE/constraint hints.

    Works with PostgreSQL (psycopg2) and falls back to detail text matching.
    """
    orig = getattr(exc, "orig", None)
    detail = str(orig) if orig is not None else str(exc)

    constraint_name = getattr(getattr(orig, "diag", None), "constraint_name", None)
    pgcode = getattr(orig, "pgcode", None)

    if constraint_name in {"users_username_key", "users_email_key"}:
        return UserIntegrityErrorClassification(
            error_type=UserIntegrityErrorType.USERNAME_OR_EMAIL_CONFLICT,
            detail=detail,
            constraint_name=constraint_name,
        )

    if constraint_name == "users_pkey":
        return UserIntegrityErrorClassification(
            error_type=UserIntegrityErrorType.USERS_PKEY_CONFLICT,
            detail=detail,
            constraint_name=constraint_name,
        )

    detail_lower = detail.lower()

    if "users_pkey" in detail_lower:
        return UserIntegrityErrorClassification(
            error_type=UserIntegrityErrorType.USERS_PKEY_CONFLICT,
            detail=detail,
            constraint_name=constraint_name,
        )

    if "users_username_key" in detail_lower or "users_email_key" in detail_lower:
        return UserIntegrityErrorClassification(
            error_type=UserIntegrityErrorType.USERNAME_OR_EMAIL_CONFLICT,
            detail=detail,
            constraint_name=constraint_name,
        )

    # PostgreSQL unique violation SQLSTATE
    if pgcode == "23505":
        if "users_pkey" in detail_lower:
            return UserIntegrityErrorClassification(
                error_type=UserIntegrityErrorType.USERS_PKEY_CONFLICT,
                detail=detail,
                constraint_name=constraint_name,
            )
        if "users_username_key" in detail_lower or "users_email_key" in detail_lower:
            return UserIntegrityErrorClassification(
                error_type=UserIntegrityErrorType.USERNAME_OR_EMAIL_CONFLICT,
                detail=detail,
                constraint_name=constraint_name,
            )

    # SQLite fallback pattern for local/unit tests
    if "unique constraint failed" in detail_lower and (
        "users.username" in detail_lower or "users.email" in detail_lower
    ):
        return UserIntegrityErrorClassification(
            error_type=UserIntegrityErrorType.USERNAME_OR_EMAIL_CONFLICT,
            detail=detail,
            constraint_name=constraint_name,
        )

    return UserIntegrityErrorClassification(
        error_type=UserIntegrityErrorType.OTHER,
        detail=detail,
        constraint_name=constraint_name,
    )
