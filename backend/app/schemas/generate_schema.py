"""全流程内容生成 Schema - POST /generate 接口"""
from pydantic import BaseModel, Field
from typing import List, Optional


class FullPipelineRequest(BaseModel):
    """全流程生成请求"""
    platform: str = Field(..., description="目标平台: xiaohongshu / douyin / zhihu")
    account_type: str = Field(..., description="账号类型: loan_advisor / agent / knowledge_account")
    audience: str = Field(..., description="目标人群: bad_credit / high_debt / office_worker / self_employed")
    topic: str = Field(..., description="内容主题: loan / credit / online_loan / housing_fund")
    goal: Optional[str] = Field(default=None, description="内容目标: private_message / consultation / conversion")
    model: str = Field(default="volcano", description="模型选择: volcano(火山方舟) / local(本地Ollama)")
    extra_requirements: Optional[str] = Field(default=None, description="额外要求")
    tone: Optional[str] = Field(default=None, description="语气风格: professional/friendly/humorous/empathetic/urgent")


class VersionItem(BaseModel):
    """单个版本生成结果"""
    style: str = Field(..., description="版本风格: professional / casual / seeding")
    title: str = Field(default="", description="版本标题")
    text: str = Field(..., description="生成文案")
    compliance: Optional[dict] = Field(default=None, description="该版本的合规检查结果")


class RiskPoint(BaseModel):
    """风险点"""
    keyword: str = ""
    reason: str = ""
    suggestion: str = ""
    source: str = Field(default="rule", description="来源: rule(规则匹配) / llm(大模型语义检测)")


class ComplianceResult(BaseModel):
    """合规检查结果"""
    risk_level: str = Field(..., description="风险等级: low / medium / high")
    risk_score: int = Field(default=0, description="风险分数")
    risk_points: List[RiskPoint] = Field(default_factory=list, description="风险点列表")
    suggestions: List[str] = Field(default_factory=list, description="修改建议")
    rewritten_text: str = Field(default="", description="合规修正后的文本")
    llm_analysis: Optional[str] = Field(default=None, description="大模型语义分析结果")
    auto_fixed_text: Optional[str] = Field(default=None, description="自动修正版文案")


class FullPipelineResponse(BaseModel):
    """全流程生成响应"""
    versions: List[VersionItem] = Field(..., description="3个版本的生成结果")
    compliance: ComplianceResult = Field(..., description="合规审核结果")
    final_text: str = Field(..., description="最终推荐文本")
    rewrite_base: str = Field(default="", description="改写基础版(知识库增强后的初稿)")
    knowledge_context_used: bool = Field(default=False, description="是否使用了知识库上下文")
