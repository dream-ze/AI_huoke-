export type DashboardSummary = {
  today_new_customers: number;
  today_wechat_adds: number;
  today_leads: number;
  today_valid_leads: number;
  today_conversions: number;
  pending_follow_count: number;
  pending_review_count: number;
};

export type TrendItem = {
  date: string;
  publish_count: number;
  total_views: number;
  total_private_messages: number;
  total_wechat_adds: number;
  total_leads: number;
  total_valid_leads: number;
  total_conversions: number;
};

export type AICallStatItem = {
  date: string;
  user_id?: number;
  username?: string;
  call_count: number;
  failed_count: number;
  failure_rate: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  avg_latency_ms: number;
};

export type AICallStatsResponse = {
  period_days: number;
  scope: "me" | "all";
  data: AICallStatItem[];
};

export type UserSummary = {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
};

export type ContentAsset = {
  id: number;
  platform: string;
  content_type: string;
  title: string;
  content?: string;
  tags: string[];
  created_at: string;
};

// ── 素材中台 ──────────────────────────────────────────
export type CollectItem = {
  id: number;
  platform: string;
  source_url?: string;
  title: string;
  content_text: string;
  author_name?: string;
  source_channel: string;
  keyword?: string;
  hot_level: string;
  lead_level: string;
  quality_score: number;
  relevance_score: number;
  lead_score: number;
  risk_status: string;
  status: string;
  filter_reason?: string;
  remark?: string;
  review_note?: string;
  generation_count: number;
  knowledge?: {
    document_id?: number | null;
    account_type?: string | null;
    target_audience?: string | null;
    content_type?: string | null;
    topic?: string | null;
    summary?: string | null;
    chunk_count: number;
  };
  created_at: string;
};

export type CollectKnowledgeDocument = {
  document_id: number;
  platform: string;
  account_type: string;
  target_audience: string;
  content_type: string;
  topic?: string | null;
  title?: string | null;
  summary?: string | null;
  content_text?: string | null;
  chunks: string[];
  chunk_keywords: string[][];
};

export type CollectGenerationTask = {
  generation_task_id: number;
  platform: string;
  account_type: string;
  target_audience: string;
  task_type: string;
  output_text: string;
  reference_document_ids: number[];
  tags?: Record<string, any>;
  copies?: Array<{
    variant_name: string;
    title: string;
    content: string;
    hashtags: string[];
    compliance?: {
      corrected?: boolean;
      is_compliant?: boolean;
      risk_level?: string;
      risk_score?: number;
      publish_blocked?: boolean;
      suggestions?: string[];
    };
  }>;
  compliance?: {
    corrected?: boolean;
    is_compliant?: boolean;
    risk_level?: string;
    risk_score?: number;
    publish_blocked?: boolean;
    block_threshold?: number;
  };
  selected_variant?: string | null;
  selected_variant_index?: number | null;
  adoption_status?: string;
  adopted_at?: string | null;
  adopted_by_user_id?: number | null;
  created_at?: string | null;
};

export type CollectDetail = {
  id: number;
  platform: string;
  source_channel: string;
  source_url?: string;
  source_id?: string;
  keyword?: string;
  title: string;
  content_text: string;
  author_name?: string;
  cover_url?: string;
  publish_time?: string;
  hot_level: string;
  lead_level: string;
  lead_reason?: string;
  quality_score: number;
  relevance_score: number;
  lead_score: number;
  parse_status: string;
  risk_status: string;
  status: string;
  filter_reason?: string;
  remark?: string;
  review_note?: string;
  raw_data: Record<string, any>;
  generation_count: number;
  knowledge?: CollectItem["knowledge"];
  knowledge_documents: CollectKnowledgeDocument[];
  generation_tasks: CollectGenerationTask[];
  generation_variant_stats?: Array<{
    variant_name: string;
    total: number;
    adopted: number;
    adoption_rate: number;
  }>;
  created_at?: string;
  updated_at?: string;
};

export type SpiderXHSBatchRow = {
  note_id: string;
  content_id?: number;
  dedupe_hit?: boolean;
  status: "ok" | "failed";
  error?: string;
};

export type SpiderXHSBatchResult = {
  total: number;
  ok: number;
  dedupe: number;
  failed: number;
  rows: SpiderXHSBatchRow[];
};

export type ParsedLinkMeta = {
  platform: string;
  platform_label: string;
  source_url: string;
  detected_title: string;
  detected_content: string;
  detected_author: string;
  fetch_success: boolean;
  message: string;
};

export type CollectAnalysis = {
  content_id: number;
  tags: string[];
  category: string;
  heat_score: number;
  is_viral: boolean;
  viral_reasons: string[];
  key_selling_points: string[];
  rewrite_hints: string;
};

export type CollectStats = {
  total: number;
  viral_count: number;
  by_platform: Record<string, number>;
  by_category: Record<string, number>;
};

export type InboxItem = {
  id: number;
  platform: string;
  source_url?: string;
  content_type: string;
  title: string;
  content: string;
  author?: string;
  tags: string[];
  metrics: Record<string, number>;
  source_type?: string;
  category?: string;
  manual_note?: string;
  heat_score: number;
  is_viral: boolean;
  status: "pending" | "analyzed" | "imported" | "discarded" | string;
  promoted_content_id?: number;
  promoted_insight_item_id?: number;
  review_note?: string;
  created_at: string;
};

export type InboxStats = {
  total: number;
  pending: number;
  analyzed: number;
  imported: number;
  discarded: number;
  by_platform: Record<string, number>;
};

export type PublishTask = {
  id: number;
  owner_id: number;
  rewritten_content_id?: number;
  publish_record_id?: number;
  platform: string;
  account_name: string;
  task_title: string;
  content_text: string;
  status: string;
  assigned_to?: number;
  due_time?: string;
  claimed_at?: string;
  posted_at?: string;
  closed_at?: string;
  post_url?: string;
  reject_reason?: string;
  close_reason?: string;
  views: number;
  likes: number;
  comments: number;
  favorites: number;
  shares: number;
  private_messages: number;
  wechat_adds: number;
  leads: number;
  valid_leads: number;
  conversions: number;
  created_at: string;
  updated_at: string;
};

export type PublishTaskStats = {
  total: number;
  pending: number;
  claimed: number;
  submitted: number;
  rejected: number;
  closed: number;
};

export type Customer = {
  id: number;
  nickname: string;
  wechat_id?: string;
  source_platform: string;
  tags: string[];
  intention_level: string;
  customer_status: string;
  created_at: string;
};

export type LeadItem = {
  id: number;
  owner_id: number;
  publish_task_id?: number;
  customer_id?: number;
  platform: string;
  source: string;
  title: string;
  post_url?: string;
  wechat_adds: number;
  leads: number;
  valid_leads: number;
  conversions: number;
  status: string;
  intention_level: string;
  note?: string;
  created_at: string;
};

// ═══════════ MVP 核心类型 ═══════════

export interface KnowledgeLibraryStat {
  library_type: string;
  label: string;
  count: number;
}

export interface KnowledgeChunk {
  id: number;
  knowledge_id: number;
  chunk_type: string;
  chunk_index: number;
  content: string;
  metadata_json?: string;
  has_embedding: boolean;
  token_count: number;
  created_at?: string;
}

export type MvpInboxItem = {
  id: number;
  platform: string;
  title: string;
  content: string;
  author?: string;
  source_url?: string;
  source_type: string;
  keyword?: string;
  risk_level: string;
  duplicate_status: string;
  score: number;
  tech_status: string;
  biz_status: string;
  created_at: string;
};

export type MvpMaterialItem = {
  id: number;
  platform: string;
  title: string;
  content: string;
  source_url?: string;
  like_count: number;
  comment_count: number;
  author?: string;
  is_hot: boolean;
  risk_level: string;
  use_count: number;
  source_inbox_id?: number;
  tags: MvpTag[];
  created_at: string;
};

export type MvpTag = {
  id: number;
  name: string;
  type: string;  // platform / audience / style / topic / scenario / content_type
  created_at: string;
};

export type MvpKnowledgeItem = {
  id: number;
  title: string;
  content: string;
  category?: string;
  platform?: string;
  audience?: string;
  style?: string;
  source_material_id?: number;
  use_count: number;
  created_at: string;
};

export type MvpGenerateRequest = {
  source_type: string;  // inbox / material / manual
  source_id?: number;
  manual_text?: string;
  target_platform: string;
  audience: string;
  style: string;
  enable_knowledge: boolean;
  enable_rewrite: boolean;
  version_count: number;
  extra_requirements?: string;
};

export type MvpGenerationVersion = {
  title: string;
  text: string;
  version: string;
  style_label: string;
};

export type MvpGenerateResult = {
  versions: MvpGenerationVersion[];
  tags: {
    platform: string;
    audience: string;
    style: string;
    scenario: string;
    content_type: string;
  };
};

export type MvpComplianceResult = {
  risk_level: string;
  risk_points: Array<{
    keyword: string;
    reason: string;
    suggestion: string;
  }>;
  suggestions: string[];
  rewritten_text: string;
};

export type MvpFinalGenerateResult = {
  versions: MvpGenerationVersion[];
  selected_version?: MvpGenerationVersion;
  compliance?: MvpComplianceResult;
  final_text?: string;
  tags: {
    platform: string;
    audience: string;
    style: string;
    scenario: string;
    content_type: string;
  };
};

export type MvpStatsOverview = {
  inbox_pending: number;
  material_count: number;
  knowledge_count: number;
  today_generation_count: number;
  risk_content_count: number;
  recent_generations: Array<{
    id: number;
    title: string;
    version: string;
    created_at: string;
  }>;
  recent_materials: Array<{
    id: number;
    title: string;
    platform: string;
    created_at: string;
  }>;
};

export type MvpHotRewriteResult = {
  structure_analysis: {
    hook: string;
    pain_point: string;
    scenario: string;
    solution: string;
    cta: string;
  };
  versions: MvpGenerationVersion[];
};

export type MvpPaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
};

// ===== 全流程生成接口类型 =====
export interface FullPipelineRequest {
  platform: string;
  account_type: string;
  audience: string;
  topic: string;
  goal?: string;
  model?: string;  // "volcano" | "local"
  extra_requirements?: string;
  tone?: string;  // 新增
}

export interface FullPipelineVersion {
  style: string;  // professional | casual | seeding
  text: string;
  compliance?: {
    risk_level: string;
    risk_points: Array<{ keyword: string; reason: string; source: string }>;
    suggestions: string[];
    auto_fixed_text?: string;
  };
}

export interface FullPipelineRiskPoint {
  keyword: string;
  reason: string;
  source: string;
}

export interface FullPipelineCompliance {
  risk_level: string;
  risk_points: FullPipelineRiskPoint[];
  suggestions: string[];
  auto_fixed_text?: string;
  llm_analysis?: string;
}

export interface FullPipelineResponse {
  versions: FullPipelineVersion[];
  compliance: FullPipelineCompliance;
  final_text: string;
  rewrite_base?: string;
  knowledge_context_used: boolean;
}

// ── 采集中心类型 ──────────────────────────────────────────

export interface CollectorSearchRequest {
  platform: string;
  keyword: string;
  count: number;
  fetch_detail?: boolean;
  fetch_comments?: boolean;
  source_type?: string;
}

export interface CollectorResult {
  id: number;
  title: string;
  platform: string;
  author?: string;
  content?: string;
  summary?: string;
  tags?: string[];
  risk_level?: string;  // low / medium / high
  ingest_status: string;  // pending / processing / completed
  source_url?: string;
  created_at: string;
}

export interface DashboardStats {
  today_collected: number;
  today_knowledge_ingested: number;
  today_generated: number;
  risk_content_count: number;
  total_knowledge: number;
  total_materials: number;
  date: string;
}

// ========== 原始内容池（收件箱）类型 ==========

/** 原始内容池条目 - 收件箱核心数据结构 */
export interface RawContentInboxItem {
  id: number;
  platform: string;
  source_id?: string;
  title: string;
  content?: string;           // 全文（展开时用）
  content_preview?: string;   // 摘要
  author_name?: string;
  publish_time?: string;
  url?: string;
  like_count: number;
  comment_count: number;
  favorite_count: number;
  clean_status: 'pending' | 'cleaned' | 'failed';
  quality_status: 'pending' | 'good' | 'normal' | 'low';
  risk_status: 'normal' | 'low_risk' | 'high_risk';
  quality_score: number;
  risk_score: number;
  material_status: 'not_in' | 'in_material' | 'ignored';
  score?: number;
  tech_status?: string;
  biz_status?: string;
  risk_level?: string;
  cleaned_at?: string;
  screened_at?: string;
  created_at: string;
  updated_at?: string;
}

/** 收件箱列表查询参数 */
export interface InboxListParams {
  page?: number;
  size?: number;
  platform?: string;
  clean_status?: string;
  quality_status?: string;
  risk_status?: string;
  material_status?: string;
  keyword?: string;
}

/** 收件箱列表响应 */
export interface InboxListResponse {
  items: RawContentInboxItem[];
  total: number;
  page: number;
  size: number;
}

// ========== 反馈闭环类型 ==========

/** 反馈提交请求 */
export interface FeedbackSubmitRequest {
  generation_id: string;
  query: string;
  generated_text: string;
  feedback_type: 'adopted' | 'modified' | 'rejected';
  modified_text?: string;
  rating?: number;
  feedback_tags?: string[];
  knowledge_ids_used?: number[];
}

/** 反馈提交响应 */
export interface FeedbackSubmitResponse {
  success: boolean;
  feedback_id: number;
  message: string;
  quality_scores_updated: number;
}

/** 反馈统计 */
export interface FeedbackStats {
  total_feedback: number;
  adopted_count: number;
  modified_count: number;
  rejected_count: number;
  adoption_rate: number;
  modification_rate: number;
  rejection_rate: number;
  avg_rating: number | null;
  recent_feedback_count: number;
}

/** 知识库质量排行条目 */
export interface KnowledgeQualityRankingItem {
  knowledge_id: number;
  title: string;
  quality_score: number;
  reference_count: number;
  positive_feedback: number;
  negative_feedback: number;
  weight_boost: number;
  last_referenced_at: string | null;
}

/** 知识库质量排行响应 */
export interface KnowledgeQualityRankingResponse {
  items: KnowledgeQualityRankingItem[];
  total: number;
}

/** 学习建议条目 */
export interface LearningSuggestionItem {
  type: string;  // boost / downgrade / remove / adjust
  knowledge_id: number;
  title: string;
  current_score: number;
  suggestion: string;
  priority: string;  // high / medium / low
  reason: string;
}

/** 学习建议响应 */
export interface LearningSuggestionsResponse {
  suggestions: LearningSuggestionItem[];
  boost_candidates: number;
  downgrade_candidates: number;
  remove_candidates: number;
}

/** 权重调整结果 */
export interface WeightAdjustmentResult {
  boosted_count: number;
  downgraded_count: number;
  cold_marked_count: number;
  message: string;
  details: Array<{
    knowledge_id: number;
    action: string;
    old_value: number;
    new_value: number;
  }>;
}
