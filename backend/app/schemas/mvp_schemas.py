"""MVP Pydantic Schemas - 请求和响应模型"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── 收件箱 ──
class InboxItemResponse(BaseModel):
    id: int
    platform: str
    title: str
    content: str
    author: Optional[str] = None
    source_url: Optional[str] = None
    source_type: str
    keyword: Optional[str] = None
    risk_level: str
    duplicate_status: str
    score: float
    tech_status: str
    biz_status: str
    created_at: Optional[datetime] = None

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
    tags: List[TagResponse] = []
    created_at: Optional[datetime] = None

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
