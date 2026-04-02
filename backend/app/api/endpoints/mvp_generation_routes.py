"""MVP AI生成/改写路由模块"""

from app.core.database import get_db
from app.schemas.generate_schema import ConstrainedGenerateRequest, ConstrainedGenerateResponse, FullPipelineRequest
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


@router.post("/generate/constrained", response_model=ConstrainedGenerateResponse)
async def generate_constrained(req: ConstrainedGenerateRequest, db: Session = Depends(get_db)):
    """
    强约束内容生成接口 - 基于细粒度约束条件生成结构化内容

    请求参数：
    - platform: 目标平台 (xiaohongshu / douyin / zhihu) - 必填
    - audience: 目标人群（如：公积金用户/个体户/企业主） - 必填
    - product_type: 产品类型（信贷/抵押贷/企业贷/经营贷/消费贷） - 必填
    - business_scenario: 业务场景（如：征信花如何贷款） - 可选
    - target_action: 目标动作（如：加微信/留电话/点击链接） - 可选
    - risk_level: 风险等级 (low/medium/high) - 默认 medium
    - reference_material_ids: 参考素材ID列表 - 可选
    - forbidden_expressions: 禁用表达列表 - 可选
    - compliance_notes: 必须保留的合规说明 - 可选
    - guidance_method: 引导方式（私信/评论/表单） - 可选
    - version_count: 生成版本数 (1-5) - 默认 3
    - style: 内容形式（口播/图文/问答/经验帖） - 可选
    - content_intent: 内容意图（科普/避坑/案例/引流/转化） - 可选
    - model: 模型选择 (volcano/local) - 默认 volcano
    - extra_requirements: 额外要求 - 可选

    响应：
    - versions: 多版本结构化输出（包含 title/hook/body/call_to_action/risk_notes/compliance_level）
    - recommended_version: 推荐版本索引
    - input_constraints_applied: 实际应用的约束摘要
    - generation_metadata: 生成元数据（耗时、模型等）
    """
    try:
        svc = MvpGenerateService(db)
        result = await svc.constrained_generate(req)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"强约束生成失败: {str(e)}")
