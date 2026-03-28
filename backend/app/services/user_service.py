import logging

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.models import User
from app.core.security import hash_password, verify_password
from app.core.db_error_classifier import (
    UserIntegrityErrorType,
    classify_user_create_integrity_error,
)
from app.core.metrics import (
    inc_user_sequence_repair_attempt,
    inc_user_sequence_repair_failure,
    inc_user_sequence_repair_success,
    inc_user_sequence_startup_align,
)
from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    def _sync_user_id_sequence(db: Session) -> bool:
        """Align PostgreSQL users.id sequence with current max(id)."""
        try:
            db.execute(
                text(
                    """
                    SELECT setval(
                        pg_get_serial_sequence('users', 'id'),
                        COALESCE((SELECT MAX(id) FROM users), 0) + 1,
                        false
                    )
                    """
                )
            )
            db.commit()
            return True
        except Exception:
            db.rollback()
            logger.exception("users.id sequence alignment failed")
            return False

    @staticmethod
    def ensure_user_id_sequence_health(db: Session) -> bool:
        """Best-effort startup health check for PostgreSQL users.id sequence."""
        bind = db.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return False

        if UserService._sync_user_id_sequence(db):
            inc_user_sequence_startup_align()
            logger.info("users.id sequence aligned during startup health check")
            return True
        return False

    @staticmethod
    def create_user(db: Session, username: str, email: str, password: str) -> User:
        """Create new user"""
        # Check if user exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        
        # Create new user
        hashed_password = hash_password(password)

        def _build_user() -> User:
            return User(
                username=username,
                email=email,
                hashed_password=hashed_password,
            )

        user = _build_user()
        db.add(user)

        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError as exc:
            db.rollback()
            classification = classify_user_create_integrity_error(exc)

            if classification.error_type == UserIntegrityErrorType.USERNAME_OR_EMAIL_CONFLICT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username or email already exists",
                )

            # Heal broken serial sequence in imported/new environments, then retry once.
            if classification.error_type == UserIntegrityErrorType.USERS_PKEY_CONFLICT:
                inc_user_sequence_repair_attempt()
                logger.warning(
                    "users_pkey conflict detected during register, trying sequence recovery",
                    extra={
                        "event": "user_register_sequence_repair",
                        "constraint": classification.constraint_name or "users_pkey",
                    },
                )

                synced = UserService._sync_user_id_sequence(db)
                if not synced:
                    inc_user_sequence_repair_failure()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Create user failed after sequence recovery",
                    )

                retry_user = _build_user()
                db.add(retry_user)
                try:
                    db.commit()
                    db.refresh(retry_user)
                    inc_user_sequence_repair_success()
                    logger.info(
                        "user registration retry succeeded after sequence recovery",
                        extra={"event": "user_register_sequence_repair_success"},
                    )
                    return retry_user
                except IntegrityError as retry_exc:
                    db.rollback()
                    retry_classification = classify_user_create_integrity_error(retry_exc)
                    if retry_classification.error_type == UserIntegrityErrorType.USERNAME_OR_EMAIL_CONFLICT:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username or email already exists",
                        )
                    inc_user_sequence_repair_failure()
                    logger.error(
                        "user registration retry failed after sequence recovery",
                        extra={
                            "event": "user_register_sequence_repair_failed",
                            "constraint": retry_classification.constraint_name,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Create user failed after sequence recovery",
                    )

            raise

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> User:
        """Authenticate user"""
        user = db.query(User).filter(User.username == username).first()
        
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        return user

    @staticmethod
    def get_user(db: Session, user_id: int) -> User:
        """Get user by id"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
