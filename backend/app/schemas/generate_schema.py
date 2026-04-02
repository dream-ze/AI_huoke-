"""全流程内容生成 Schema - POST /generate 接口"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


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
    product_type: Optional[str] = Field(default=None, description="产品类型")
    risk_tolerance: Optional[str] = Field(default="medium", description="风险容忍度: low / medium / high")
    required_disclaimers: Optional[List[str]] = Field(default=None, description="必须包含的免责声明列表")


class VersionItem(BaseModel):
    """单个版本生成结果"""

    style: str = Field(..., description="版本风格: professional / casual / seeding")
    title: str = Field(default="", description="版本标题")
    text: str = Field(..., description="生成文案")
    compliance: Optional[dict] = Field(default=None, description="该版本的合规检查结果")
    # 结构化输出字段
    opening_hook: str = Field(default="", description="开头钩子")
    cta_section: str = Field(default="", description="行动引导段")
    risk_disclaimer: str = Field(default="请注意：贷款需谨慎，具体利率以实际审批为准", description="风险点说明")
    alternative_v1: str = Field(default="", description="低风险替代版本")
    alternative_v2: str = Field(default="", description="高转化替代版本")
    output_structure: Optional[dict] = Field(default=None, description="完整结构化输出JSON")


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


# =============================================================================
# 强约束生成 Schema
# =============================================================================


class ConstrainedGenerateRequest(BaseModel):
    """强约束生成请求 - 提供更细粒度的生成控制"""

    # 基础必填
    platform: str = Field(..., description="目标平台: xiaohongshu / douyin / zhihu")
    audience: str = Field(..., description="目标人群（如：公积金用户/个体户/企业主/征信花用户）")
    product_type: str = Field(..., description="产品类型（信贷/抵押贷/企业贷/经营贷/消费贷）")

    # 业务约束
    business_scenario: Optional[str] = Field(default=None, description="业务场景（如：征信花如何贷款）")
    target_action: Optional[str] = Field(default=None, description="目标动作（如：加微信/留电话/点击链接）")
    risk_level: str = Field(default="medium", description="风险等级: low / medium / high")

    # 内容约束
    reference_material_ids: Optional[List[int]] = Field(default=None, description="参考素材ID列表")
    forbidden_expressions: Optional[List[str]] = Field(default=None, description="禁用表达列表")
    compliance_notes: Optional[str] = Field(default=None, description="必须保留的合规说明")
    guidance_method: Optional[str] = Field(default=None, description="引导方式（私信/评论/表单）")

    # 生成参数
    version_count: int = Field(default=3, ge=1, le=5, description="生成版本数(1-5)")
    style: Optional[str] = Field(default=None, description="内容形式: 口播/图文/问答/经验帖")
    content_intent: Optional[str] = Field(default=None, description="内容意图: 科普/避坑/案例/引流/转化")

    # 模型配置
    model: str = Field(default="volcano", description="模型选择: volcano(火山方舟) / local(本地Ollama)")
    extra_requirements: Optional[str] = Field(default=None, description="额外要求")

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = ["xiaohongshu", "douyin", "zhihu"]
        if v not in allowed:
            raise ValueError(f"platform 必须是以下之一: {allowed}")
        return v

    @field_validator("product_type")
    @classmethod
    def validate_product_type(cls, v: str) -> str:
        allowed = ["信贷", "抵押贷", "企业贷", "经营贷", "消费贷"]
        if v not in allowed:
            raise ValueError(f"product_type 必须是以下之一: {allowed}")
        return v

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        allowed = ["low", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"risk_level 必须是以下之一: {allowed}")
        return v


class StructuredGenerateOutput(BaseModel):
    """结构化生成输出（单版本）"""

    title: str = Field(..., description="标题")
    hook: str = Field(..., description="开头钩子")
    body: str = Field(..., description="正文")
    call_to_action: str = Field(..., description="行动引导")
    risk_notes: Optional[str] = Field(default=None, description="风险点说明")
    compliance_level: str = Field(default="green", description="合规等级: green / yellow / red")


class ConstrainedGenerateResponse(BaseModel):
    """强约束生成响应"""

    versions: List[StructuredGenerateOutput] = Field(..., description="多版本输出")
    recommended_version: int = Field(default=0, ge=0, description="推荐版本索引")
    input_constraints_applied: dict = Field(default_factory=dict, description="实际应用的约束摘要")
    generation_metadata: dict = Field(default_factory=dict, description="生成元数据（耗时、模型等）")
