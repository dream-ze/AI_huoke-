"""MVP AI生成/改写路由模块"""

from app.core.database import get_db
from app.schemas.generate_schema import FullPipelineRequest
from app.schemas.mvp_schemas import GenerateRequest
from app.services.mvp_generate_service import MvpGenerateService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/generate")
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    """多版本内容生成"""
    try:
        svc = MvpGenerateService(db)
        result = svc.generate_multi_version(
            source_type=req.source_type,
            source_id=req.source_id,
            manual_text=req.manual_text,
            target_platform=req.target_platform,
            audience=req.audience,
            style=req.style,
            enable_knowledge=req.enable_knowledge,
            enable_rewrite=req.enable_rewrite,
            version_count=req.version_count,
            extra_requirements=req.extra_requirements,
        )
        if result.get("error"):
            raise HTTPException(500, result["error"])
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/generate/final")
def generate_final(req: GenerateRequest, db: Session = Depends(get_db)):
    """完整主链路生成（标签识别→知识检索→多版本生成→合规审核）"""
    try:
        svc = MvpGenerateService(db)
        result = svc.generate_final(
            source_type=req.source_type,
            source_id=req.source_id,
            manual_text=req.manual_text,
            target_platform=req.target_platform,
            audience=req.audience,
            style=req.style,
            enable_knowledge=req.enable_knowledge,
            enable_rewrite=req.enable_rewrite,
            version_count=req.version_count,
            extra_requirements=req.extra_requirements,
        )
        if result.get("error"):
            raise HTTPException(500, result["error"])
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/generate/full-pipeline")
async def generate_pipeline(req: FullPipelineRequest, db: Session = Depends(get_db)):
    """
    全流程内容生成接口（知识库检索 -> 上下文编排 -> 多版本生成 -> 合规审核 -> 最终输出）

    请求参数：
    - platform: 目标平台 (xiaohongshu / douyin / zhihu)
    - account_type: 账号类型 (loan_advisor / agent / knowledge_account)
    - audience: 目标人群 (bad_credit / high_debt / office_worker / self_employed)
    - topic: 内容主题 (loan / credit / online_loan / housing_fund)
    - goal: 内容目标 (private_message / consultation / conversion)

    响应：
    - versions: 3个版本的生成结果 (professional/casual/seeding)
    - compliance: 合规审核结果
    - final_text: 最终推荐文本
    - knowledge_context_used: 是否使用了知识库上下文
    """
    try:
        svc = MvpGenerateService(db)
        result = await svc.generate_full_pipeline(req)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"内容生成失败: {str(e)}")
