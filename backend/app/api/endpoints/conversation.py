"""会话管理端点"""

from datetime import datetime
from typing import List, Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.models.models import Conversation, Message
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# --- Schemas ---


class ConversationResponse(BaseModel):
    id: int
    lead_id: Optional[int] = None
    customer_id: Optional[int] = None
    platform: str
    conversation_type: str
    status: str
    ai_handled: bool
    takeover_at: Optional[datetime] = None
    takeover_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    reply_suggestion: Optional[dict] = None
    is_sent: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReplyRequest(BaseModel):
    content: str
    is_sent: bool = False


class SuggestRequest(BaseModel):
    message: str
    platform: str = "xiaohongshu"


class SuggestResponse(BaseModel):
    intent: str
    confidence: float
    suggestions: List[str]
    should_takeover: bool
    takeover_reason: Optional[str] = None


# --- Endpoints ---


@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获取会话列表"""
    query = db.query(Conversation)

    if status:
        query = query.filter(Conversation.status == status)
    if platform:
        query = query.filter(Conversation.platform == platform)

    conversations = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
    return conversations


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def get_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获取会话消息历史"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return messages


@router.post("/{conversation_id}/reply", response_model=MessageResponse)
def reply_to_conversation(
    conversation_id: int,
    payload: ReplyRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """发送/确认回复"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=payload.content,
        is_sent=payload.is_sent,
    )
    db.add(message)

    # 更新会话时间
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(message)

    return message


@router.post("/{conversation_id}/takeover")
def takeover_conversation(
    conversation_id: int,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """人工接管会话"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    conversation.status = "takeover"
    conversation.ai_handled = False
    conversation.takeover_at = datetime.utcnow()
    conversation.takeover_by = current_user["user_id"]
    conversation.updated_at = datetime.utcnow()

    db.commit()

    return {"ok": True, "message": "已切换为人工接管模式"}


@router.post("/{conversation_id}/suggest", response_model=SuggestResponse)
async def get_suggestions(
    conversation_id: int,
    payload: SuggestRequest,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """获取AI回复建议"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 获取历史消息
    recent_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )

    history = [{"role": m.role, "content": m.content} for m in reversed(recent_messages)]

    # 调用 ReplySkill
    from app.skills import SkillRegistry
    from app.skills.base_skill import SkillContext

    skill = SkillRegistry.get("reply_suggestion")
    context = SkillContext(
        trace_id=f"suggest-{conversation_id}-{datetime.utcnow().timestamp()}",
        user_id=current_user["user_id"],
        workflow_task_id=0,
        input_data={
            "message": payload.message,
            "platform": payload.platform or conversation.platform,
            "history": history,
        },
    )

    result = await skill.run(context)

    if not result.success:
        raise HTTPException(status_code=500, detail=f"AI建议生成失败: {result.error}")

    # 记录用户消息
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=payload.message,
        intent=result.data.get("intent"),
        confidence=result.data.get("confidence"),
        reply_suggestion=result.data.get("suggestions"),
    )
    db.add(user_msg)
    conversation.updated_at = datetime.utcnow()
    db.commit()

    return SuggestResponse(
        intent=result.data.get("intent", "unknown"),
        confidence=result.data.get("confidence", 0),
        suggestions=result.data.get("suggestions", []),
        should_takeover=result.data.get("should_takeover", False),
        takeover_reason=result.data.get("takeover_reason"),
    )
