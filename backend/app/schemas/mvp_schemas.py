"""MVP Pydantic Schemas - 请求和响应模型"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── 收件箱 ──
class InboxItemResponse(BaseModel):
    id: int
    platform: str
    source_id: Optional[str] = None           # 平台内容ID
    title: str
    content: str
    content_preview: Optional[str] = None     # 内容摘要
    author: Optional[str] = None
    author_name: Optional[str] = None         # 作者
    publish_time: Optional[str] = None        # 发布时间
    source_url: Optional[str] = None
    url: Optional[str] = None                 # 原始链接
    source_type: str
    keyword: Optional[str] = None
    risk_level: str
    duplicate_status: str
    score: float
    quality_score: float = 0.0                # 质量评分
    risk_score: float = 0.0                   # 风险评分
    tech_status: str
    biz_status: str
    clean_status: str = 'pending'             # pending/cleaned/failed
    quality_status: str = 'pending'           # pending/good/normal/low
    risk_status: str = 'normal'               # normal/low_risk/high_risk
    material_status: str = 'not_in'           # not_in/in_material/ignored
    like_count: int = 0
    comment_count: int = 0
    favorite_count: int = 0
    cleaned_at: Optional[str] = None
    screened_at: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InboxListResponse(BaseModel):
    items: List[InboxItemResponse]
    total: int
    page: int
    size: int


# ── 标签 ──
class TagResponse(BaseModel):
    id: int
    name: str
    type: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TagCreateRequest(BaseModel):
    name: str
    type: str


# ── 素材库 ──
class MaterialItemResponse(BaseModel):
    id: int
    platform: str
    title: str
    content: str
    source_url: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    author: Optional[str] = None
    is_hot: bool = False
    risk_level: str = "low"
    use_count: int = 0
    source_inbox_id: Optional[int] = None
    inbox_item_id: Optional[int] = None      # 关联收件箱条目
    quality_score: Optional[float] = None    # 质量评分
    risk_score: Optional[float] = None       # 风险评分
    tags_json: Optional[str] = None          # JSON格式标签
    topic: Optional[str] = None              # 主题
    persona: Optional[str] = None            # 人设/受众画像
    tags: List[TagResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaterialDetailResponse(MaterialItemResponse):
    knowledge_items: List[Any] = []
    generation_history: List[Any] = []


class MaterialListResponse(BaseModel):
    items: List[Any]  # 包含tags的dict
    total: int
    page: int
    size: int


class MaterialCreateRequest(BaseModel):
    platform: str = "xiaohongshu"
    title: str
    content: str
    source_url: Optional[str] = None
    author: Optional[str] = None


class UpdateTagsRequest(BaseModel):
    tag_ids: List[int]


class BatchIdsRequest(BaseModel):
    """批量ID请求"""
    ids: List[int]


# ── 知识库 ──
class KnowledgeItemResponse(BaseModel):
    id: int
    title: str
    content: str
    category: Optional[str] = None
    platform: Optional[str] = None
    audience: Optional[str] = None
    style: Optional[str] = None
    source_material_id: Optional[int] = None
    use_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeListResponse(BaseModel):
    items: List[KnowledgeItemResponse]
    total: int
    page: int
    size: int


class KnowledgeBuildRequest(BaseModel):
    material_id: int


class KnowledgeSearchRequest(BaseModel):
    query: str
    platform: Optional[str] = None
    audience: Optional[str] = None


# ── AI生成 ──
class GenerateRequest(BaseModel):
    source_type: str  # inbox / material / manual
    source_id: Optional[int] = None
    manual_text: Optional[str] = None
    target_platform: str = "xiaohongshu"
    audience: str = ""
    style: str = ""
    enable_knowledge: bool = False
    enable_rewrite: bool = False
    version_count: int = 3
    extra_requirements: str = ""


class GenerationVersionResponse(BaseModel):
    title: str
    text: str
    version: str
    style_label: str


class GenerateResponse(BaseModel):
    versions: List[GenerationVersionResponse]


class FinalGenerateResponse(BaseModel):
    versions: List[GenerationVersionResponse]
    tags: Any = {}
    compliance: Any = None
    final_text: str = ""


# ── 合规 ──
class ComplianceCheckRequest(BaseModel):
    text: str


class RiskPointResponse(BaseModel):
    keyword: str
    reason: str
    suggestion: str


class ComplianceCheckResponse(BaseModel):
    risk_level: str
    risk_score: int = 0
    risk_points: List[RiskPointResponse] = []
    suggestions: List[str] = []
    rewritten_text: str = ""


# ── 自动入库Pipeline ──
class AutoPipelineRequest(BaseModel):
    """自动入库Pipeline请求"""
    title: str
    content: str
    platform: str = "unknown"
    source_url: Optional[str] = None
    author: Optional[str] = None


class AutoPipelineResponse(BaseModel):
    """自动入库Pipeline响应"""
    success: bool
    knowledge_id: Optional[int] = None
    message: str
    extracted_fields: Optional[dict] = None


class AutoPipelineBatchRequest(BaseModel):
    """批量自动入库Pipeline请求"""
    items: List[AutoPipelineRequest]


class AutoPipelineBatchResponse(BaseModel):
    """批量自动入库Pipeline响应"""
    total: int
    success_count: int
    failed_count: int
    results: List[AutoPipelineResponse]


# ── 统计 ──
class StatsOverviewResponse(BaseModel):
    inbox_pending: int = 0
    material_count: int = 0
    knowledge_count: int = 0
    today_generation_count: int = 0
    risk_content_count: int = 0
    recent_generations: List[Any] = []
    recent_materials: List[Any] = []


class DashboardStatsResponse(BaseModel):
    """AI中枢Dashboard统计响应"""
    today_collected: int = 0          # 今日采集量（mvp_inbox_items 今日创建的数量）
    today_knowledge_ingested: int = 0 # 今日入知识库量（mvp_knowledge_items 今日创建的数量）
    today_generated: int = 0          # 今日生成量（mvp_generation_results 今日创建的数量）
    risk_content_count: int = 0       # 风险文案数（risk_level 为 medium 或 high 的数量）
    total_knowledge: int = 0          # 知识库总量
    total_materials: int = 0          # 素材库总量
    date: str                         # 日期


# ── 知识库分库统计 ──
class KnowledgeLibraryStats(BaseModel):
    """单个分库统计"""
    library_type: str
    label: str
    count: int


class KnowledgeLibrariesResponse(BaseModel):
    """知识库分库统计响应"""
    libraries: List[dict]  # List[KnowledgeLibraryStats]
    total: int


# ── 切块响应 ──
class ChunkResponse(BaseModel):
    """知识切块响应"""
    id: int
    knowledge_id: int
    chunk_type: str
    chunk_index: int
    content: str
    metadata_json: Optional[str] = None
    has_embedding: bool = False
    token_count: int = 0
    created_at: Optional[str] = None


class ChunkListResponse(BaseModel):
    """切块列表响应"""
    chunks: List[dict]  # List[ChunkResponse]
    total: int


# ── Reindex请求/响应 ──
class ReindexRequest(BaseModel):
    """重建索引请求"""
    knowledge_ids: Optional[List[int]] = None  # 不传则全量重建
    embedding_model: str = "volcano"


class ReindexResponse(BaseModel):
    """重建索引响应"""
    total_processed: int
    success_count: int
    failed_count: int
    message: str


class IngestRequest(BaseModel):
    """采集入库请求"""
    platform: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    author_name: Optional[str] = None
    publish_time: Optional[str] = None
    url: Optional[str] = None
    source_id: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    favorite_count: int = 0


# ── 合规规则管理 ──
class ComplianceRuleRequest(BaseModel):
    """合规规则创建/更新请求"""
    rule_type: str  # keyword / regex / semantic
    keyword: str
    risk_level: str = "medium"  # low / medium / high
    pattern: Optional[str] = None
    description: Optional[str] = None
    suggestion: Optional[str] = None


class ComplianceRuleResponse(BaseModel):
    """合规规则响应"""
    id: int
    rule_type: str
    keyword: str
    pattern: Optional[str] = None
    risk_level: str
    description: Optional[str] = None
    suggestion: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class ComplianceRuleListResponse(BaseModel):
    """合规规则列表响应"""
    items: List[ComplianceRuleResponse]
    total: int
    page: int
    size: int


class ComplianceTestRequest(BaseModel):
    """合规规则测试请求"""
    text: str


# ── 反馈闭环 ──
class FeedbackSubmitRequest(BaseModel):
    """提交反馈请求"""
    generation_id: str = Field(..., description="生成任务ID")
    query: str = Field(..., description="原始查询/请求参数")
    generated_text: str = Field(..., description="生成的文本")
    feedback_type: str = Field(..., description="反馈类型: adopted/modified/rejected")
    modified_text: Optional[str] = Field(None, description="用户修改后的文本")
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5评分")
    feedback_tags: Optional[List[str]] = Field(None, description="反馈标签列表")
    knowledge_ids_used: Optional[List[int]] = Field(None, description="引用的知识库条目IDs")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    feedback_id: int
    message: str
    quality_scores_updated: int = 0


class FeedbackStatsResponse(BaseModel):
    """反馈统计响应"""
    total_feedback: int = 0
    adopted_count: int = 0
    modified_count: int = 0
    rejected_count: int = 0
    adoption_rate: float = 0.0
    modification_rate: float = 0.0
    rejection_rate: float = 0.0
    avg_rating: Optional[float] = None
    recent_feedback_count: int = 0


class KnowledgeQualityRankingItem(BaseModel):
    """知识库质量排行条目"""
    knowledge_id: int
    title: str
    quality_score: float
    reference_count: int
    positive_feedback: int
    negative_feedback: int
    weight_boost: float
    last_referenced_at: Optional[str] = None


class KnowledgeQualityRankingResponse(BaseModel):
    """知识库质量排行响应"""
    items: List[KnowledgeQualityRankingItem]
    total: int


class LearningSuggestionItem(BaseModel):
    """学习建议条目"""
    type: str  # boost/downgrade/remove/adjust
    knowledge_id: int
    title: str
    current_score: float
    suggestion: str
    priority: str  # high/medium/low
    reason: str


class LearningSuggestionsResponse(BaseModel):
    """学习建议响应"""
    suggestions: List[LearningSuggestionItem]
    boost_candidates: int
    downgrade_candidates: int
    remove_candidates: int


class WeightAdjustmentResult(BaseModel):
    """权重调整结果"""
    boosted_count: int = 0
    downgraded_count: int = 0
    cold_marked_count: int = 0
    message: str
    details: List[dict] = []


# ── 知识图谱 ──
class KnowledgeGraphNode(BaseModel):
    """知识图谱节点"""
    id: int
    title: str
    platform: Optional[str] = None
    audience: Optional[str] = None
    topic: Optional[str] = None
    library_type: Optional[str] = None
    use_count: int = 0
    is_hot: bool = False


class KnowledgeGraphEdge(BaseModel):
    """知识图谱边"""
    source: int
    target: int
    type: str
    weight: float


class KnowledgeGraphResponse(BaseModel):
    """知识图谱响应"""
    nodes: List[KnowledgeGraphNode]
    edges: List[KnowledgeGraphEdge]
    stats: dict


class RelatedItemResponse(BaseModel):
    """关联条目响应"""
    id: int
    title: str
    platform: Optional[str] = None
    audience: Optional[str] = None
    topic: Optional[str] = None
    library_type: Optional[str] = None
    relation_type: str
    weight: float
    direction: str


class GraphStatsResponse(BaseModel):
    """图谱统计响应"""
    node_count: int = 0
    edge_count: int = 0
    avg_degree: float = 0.0
    nodes_with_relations: int = 0
    nodes_with_embedding: int = 0
    relation_type_stats: dict = {}
    connectivity_ratio: float = 0.0


class TopicClusterItem(BaseModel):
    """主题聚类条目"""
    id: int
    title: str
    topic: Optional[str] = None


class TopicClusterResponse(BaseModel):
    """主题聚类响应"""
    topic: str
    item_ids: List[int]
    items: List[TopicClusterItem]
    count: int


class EnhancedSearchResult(BaseModel):
    """图增强检索结果"""
    id: int
    title: str
    content: str
    score: float
    source: str
    chunk_id: Optional[int] = None
    relation_weight: Optional[float] = None


class BuildRelationsResponse(BaseModel):
    """构建关系响应"""
    success: bool
    knowledge_id: int
    relations_created: int = 0
    message: str


class BatchBuildRelationsResponse(BaseModel):
    """批量构建关系响应"""
    total_items: int = 0
    processed: int = 0
    relations_created: int = 0
    errors: int = 0
    message: str


# ── 批量入知识库 ──
class BatchBuildKnowledgeRequest(BaseModel):
    """批量从素材构建知识请求"""
    material_ids: List[int] = Field(..., description="素材ID列表")


class BatchBuildKnowledgeDetailItem(BaseModel):
    """批量构建知识详情条目"""
    material_id: int
    success: bool
    knowledge_id: Optional[int] = None
    error: Optional[str] = None


class BatchBuildKnowledgeResponse(BaseModel):
    """批量从素材构建知识响应"""
    total: int
    success_count: int
    failed_count: int
    details: List[BatchBuildKnowledgeDetailItem]
