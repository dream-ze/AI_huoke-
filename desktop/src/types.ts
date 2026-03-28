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
