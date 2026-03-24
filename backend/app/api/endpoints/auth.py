from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from threading import Lock
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.security import create_access_token, verify_token
from app.core.config import settings
from app.models import User
from app.schemas import (
    MobileH5TicketCreateRequest,
    MobileH5TicketResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserSummaryResponse,
    WecomBindRequest,
    WecomOAuthConfigResponse,
)
from app.services import UserService

router = APIRouter(prefix="/api/auth", tags=["auth"])
MOBILE_H5_TICKET_PURPOSE = "mobile_h5_ticket"

# ---------------------------------------------------------------------------
# 企业微信 corp access_token 内存缓存（有效期 7200s，每日限 2000 次；此处缓存以减少无效消耗）
# ---------------------------------------------------------------------------
_wecom_token_cache: dict = {"access_token": "", "expires_at": 0.0}
_wecom_token_lock = Lock()

WECOM_TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
WECOM_USER_INFO_URL = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo"


def _wecom_oauth_enabled() -> bool:
    return bool(settings.WECOM_CORP_ID and settings.WECOM_AGENT_SECRET)


def _get_wecom_access_token() -> str:
    """同步获取/刷新企业微信 corp access_token（带本地内存缓存）。"""
    now = datetime.now(tz=timezone.utc).timestamp()
    with _wecom_token_lock:
        if _wecom_token_cache["access_token"] and _wecom_token_cache["expires_at"] > now + 60:
            return _wecom_token_cache["access_token"]

        try:
            resp = httpx.get(
                WECOM_TOKEN_URL,
                params={"corpid": settings.WECOM_CORP_ID, "corpsecret": settings.WECOM_AGENT_SECRET},
                timeout=10,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"企业微信 gettoken 请求失败：{exc}",
            ) from exc

        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"企业微信 gettoken 返回错误：{data.get('errmsg', data)}",
            )

        _wecom_token_cache["access_token"] = data["access_token"]
        _wecom_token_cache["expires_at"] = now + int(data.get("expires_in", 7200))
        return _wecom_token_cache["access_token"]


def _build_token_response(user: User) -> dict:
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
        },
    }


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    user = UserService.create_user(
        db, 
        username=user_data.username,
        email=user_data.email,
        password=user_data.password
    )
    return user


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = UserService.authenticate_user(db, credentials.username, credentials.password)
    return _build_token_response(user)


@router.get("/me", response_model=UserResponse)
def get_current_user(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """Get current user info"""
    user = UserService.get_user(db, current_user["user_id"])
    return user


@router.get("/users/active", response_model=list[UserSummaryResponse])
def list_active_users(current_user: dict = Depends(verify_token), db: Session = Depends(get_db)):
    """List active users for task assignment options."""
    _ = current_user
    users = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .order_by(User.username.asc())
        .all()
    )
    return users


@router.post("/mobile-h5/ticket", response_model=MobileH5TicketResponse)
def create_mobile_h5_ticket(
    payload: MobileH5TicketCreateRequest,
    current_user: dict = Depends(verify_token),
):
    """Issue a short-lived signed ticket for mobile-h5 bootstrap auth."""
    expires_in = max(60, int(settings.MOBILE_H5_TICKET_EXPIRE_MINUTES) * 60)
    ticket = create_access_token(
        data={
            "sub": str(current_user["user_id"]),
            "purpose": MOBILE_H5_TICKET_PURPOSE,
        },
        expires_delta=timedelta(seconds=expires_in),
    )

    auth_url = None
    redirect_path = (payload.redirect_path or "").strip()
    if redirect_path:
        query = {"ticket": ticket}
        if payload.api_base_url:
            query["api_base_url"] = payload.api_base_url.strip()
        separator = "&" if "?" in redirect_path else "?"
        auth_url = f"{redirect_path}{separator}{urlencode(query)}"

    return {
        "ticket": ticket,
        "expires_in": expires_in,
        "auth_url": auth_url,
    }


@router.get("/mobile-h5/exchange", response_model=TokenResponse)
def exchange_mobile_h5_ticket(ticket: str, db: Session = Depends(get_db)):
    """Exchange a short-lived mobile-h5 ticket into a normal bearer token."""
    try:
        payload = jwt.decode(ticket, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("purpose") != MOBILE_H5_TICKET_PURPOSE:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid mobile-h5 ticket")
        subject = payload.get("sub")
        user_id = int(subject)
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired mobile-h5 ticket")

    user = UserService.get_user(db, user_id)
    return _build_token_response(user)


# ---------------------------------------------------------------------------
# 企业微信 OAuth 相关接口
# ---------------------------------------------------------------------------

@router.get("/wecom/config", response_model=WecomOAuthConfigResponse)
def get_wecom_oauth_config():
    """返回企业微信 OAuth 公开配置（不含 secret），供前端判断是否开启 OAuth 登录入口。"""
    return {
        "corp_id": settings.WECOM_CORP_ID,
        "agent_id": settings.WECOM_AGENT_ID,
        "oauth_enabled": _wecom_oauth_enabled(),
    }


@router.get("/wecom/callback", response_model=TokenResponse)
def wecom_oauth_callback(code: str, db: Session = Depends(get_db)):
    """
    企业微信 OAuth 换码接口（公开，无需 Bearer Token）。

    流程：
    1. 企业微信 OAuth 回调带 ?code=... 到 H5 页面
    2. H5 页面将 code 转发给此接口
    3. 本接口用 code 向企业微信获取 userid
    4. 在 users 中按 wecom_userid 查找对应账号
    5. 签发 JWT 并返回（与 /login 格式相同）

    若企业微信未配置，或 code 对应的 userid 在系统中无绑定账号，返回 401/502。
    """
    if not _wecom_oauth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="企业微信 OAuth 未配置，请联系管理员",
        )

    # 1. 获取 corp access_token（带内存缓存）
    corp_token = _get_wecom_access_token()

    # 2. 用 code 换 userid
    try:
        resp = httpx.get(
            WECOM_USER_INFO_URL,
            params={"access_token": corp_token, "code": code},
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"企业微信 getuserinfo 请求失败：{exc}",
        ) from exc

    data = resp.json()
    if data.get("errcode", 0) != 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"企业微信 code 无效或已过期：{data.get('errmsg', data)}",
        )

    wecom_userid: str = data.get("userid", "").strip()
    if not wecom_userid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="企业微信未返回 userid，请确认成员在企业内",
        )

    # 3. 按 wecom_userid 查找本系统账号
    user = db.query(User).filter(User.wecom_userid == wecom_userid, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"企业微信账号 {wecom_userid} 尚未绑定本系统用户，请联系管理员绑定",
        )

    return _build_token_response(user)


@router.post("/wecom/bind")
def wecom_bind(
    payload: WecomBindRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    为当前登录用户绑定企业微信 userid（需已登录；管理员操作）。
    若该 wecom_userid 已被其他账号绑定，返回 409。
    """
    wecom_userid = payload.wecom_userid.strip()

    existing = db.query(User).filter(User.wecom_userid == wecom_userid).first()
    if existing and existing.id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"企业微信 userid '{wecom_userid}' 已绑定到其他账号",
        )

    user = UserService.get_user(db, current_user["user_id"])
    user.wecom_userid = wecom_userid
    db.commit()
    return {"ok": True, "wecom_userid": wecom_userid}
