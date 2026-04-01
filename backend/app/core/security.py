import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.redis import get_redis_client
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# Token blacklist key prefix for Redis
TOKEN_BLACKLIST_PREFIX = "token_blacklist:"

# Password hashing
# Use pbkdf2_sha256 as default to avoid bcrypt backend issues in some Windows environments.
# Keep bcrypt in the context for backward compatibility when verifying historical hashes.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# Bearer scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def _hash_token(token: str) -> str:
    """Generate SHA256 hash of token for blacklist key."""
    return hashlib.sha256(token.encode()).hexdigest()


def blacklist_token(token: str, expires_delta: int) -> bool:
    """
    Add token to blacklist with TTL equal to token's remaining lifetime.
    Returns True if successful, False if Redis is unavailable.
    """
    try:
        redis = get_redis_client()
        if redis:
            token_hash = _hash_token(token)
            redis.setex(f"{TOKEN_BLACKLIST_PREFIX}{token_hash}", expires_delta, "1")
            return True
    except Exception:
        # Graceful degradation: if Redis is unavailable, skip blacklisting
        pass
    return False


def is_token_blacklisted(token: str) -> bool:
    """
    Check if token is in blacklist.
    Returns False if Redis is unavailable (graceful degradation).
    """
    try:
        redis = get_redis_client()
        if redis:
            token_hash = _hash_token(token)
            return redis.exists(f"{TOKEN_BLACKLIST_PREFIX}{token_hash}") > 0
    except Exception:
        # Graceful degradation: if Redis is unavailable, assume not blacklisted
        pass
    return False


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        # Check if token is blacklisted
        if is_token_blacklisted(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token已失效，请重新登录")

        return {"user_id": user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
