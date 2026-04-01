from typing import List, Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.models import SocialAccount
from app.schemas import SocialAccountCreate, SocialAccountPlatform, SocialAccountResponse, SocialAccountUpdate
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/social", tags=["social_account"])


# 支持的平台列表
SUPPORTED_PLATFORMS = [
    SocialAccountPlatform(value="xiaohongshu", label="小红书"),
    SocialAccountPlatform(value="douyin", label="抖音"),
    SocialAccountPlatform(value="zhihu", label="知乎"),
    SocialAccountPlatform(value="weixin", label="微信"),
    SocialAccountPlatform(value="xianyu", label="咸鱼"),
    SocialAccountPlatform(value="other", label="其他"),
]


@router.post("/create", response_model=SocialAccountResponse)
def create_social_account(
    account_data: SocialAccountCreate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """创建/绑定社交账号"""
    account = SocialAccount(
        owner_id=current_user["user_id"],
        platform=account_data.platform,
        account_name=account_data.account_name,
        account_id=account_data.account_id,
        avatar_url=account_data.avatar_url,
        notes=account_data.notes,
        status="active",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/list", response_model=List[SocialAccountResponse])
def list_social_accounts(
    platform: Optional[str] = Query(None),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获取当前用户的账号列表（支持 platform 筛选）"""
    query = db.query(SocialAccount).filter(SocialAccount.owner_id == current_user["user_id"])
    if platform:
        query = query.filter(SocialAccount.platform == platform)
    accounts = query.order_by(SocialAccount.created_at.desc()).all()
    return accounts


@router.get("/{account_id}", response_model=SocialAccountResponse)
def get_social_account(
    account_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获取账号详情"""
    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.id == account_id,
            SocialAccount.owner_id == current_user["user_id"],
        )
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account


@router.put("/{account_id}", response_model=SocialAccountResponse)
def update_social_account(
    account_id: int,
    account_data: SocialAccountUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """更新账号信息"""
    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.id == account_id,
            SocialAccount.owner_id == current_user["user_id"],
        )
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    update_data = account_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def delete_social_account(
    account_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """删除/解绑账号"""
    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.id == account_id,
            SocialAccount.owner_id == current_user["user_id"],
        )
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    db.delete(account)
    db.commit()
    return {"message": "账号已删除"}


@router.get("/platforms", response_model=List[SocialAccountPlatform])
def get_social_platforms(
    current_user: dict = Depends(verify_token),
):
    """获取支持的平台列表"""
    return SUPPORTED_PLATFORMS
