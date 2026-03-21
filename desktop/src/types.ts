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

export type ContentAsset = {
  id: number;
  platform: string;
  content_type: string;
  title: string;
  content?: string;
  tags: string[];
  created_at: string;
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
