import axios from "axios";
import { clearToken, getToken } from "./auth";

// When served by the backend on the same origin, baseURL can be empty.
// During local dev (Vite on 5173), set VITE_API_BASE_URL=http://localhost:8000
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 20000
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearToken();
    }
    return Promise.reject(error);
  }
);

export async function login(username: string, password: string) {
  const { data } = await api.post("/api/auth/login", { username, password });
  return data;
}

export async function getDashboardSummary() {
  const { data } = await api.get("/api/dashboard/summary");
  return data;
}

export async function getTrend(days = 7) {
  const { data } = await api.get(`/api/dashboard/trend?days=${days}`);
  return data;
}

export async function getAICallStats(days = 7, scope: "me" | "all" = "me") {
  const { data } = await api.get(`/api/dashboard/ai-call-stats?days=${days}&scope=${scope}`);
  return data;
}

export async function listContent() {
  const { data } = await api.get("/api/content/list");
  return data;
}

export async function createContent(payload: {
  platform: string;
  content_type: string;
  title: string;
  content: string;
  tags: string[];
}) {
  const { data } = await api.post("/api/content/create", payload);
  return data;
}

export async function rewriteContent(payload: {
  content_id: number;
  target_platform: "xiaohongshu" | "douyin" | "zhihu";
  topic_name?: string;
  audience_tags?: string[];
}) {
  const endpointMap = {
    xiaohongshu: "/api/ai/rewrite/xiaohongshu",
    douyin: "/api/ai/rewrite/douyin",
    zhihu: "/api/ai/rewrite/zhihu"
  };
  const { data } = await api.post(endpointMap[payload.target_platform], {
    content_id: payload.content_id,
    target_platform: payload.target_platform,
    content_type: "post",
    topic_name: payload.topic_name || null,
    audience_tags: payload.audience_tags || []
  });
  return data;
}

// ── 素材中台 ──────────────────────────────────────────
export async function parseLink(url: string) {
  const { data } = await api.post("/api/collect/parse-link", { url });
  return data;
}

export async function saveCollect(payload: {
  platform: string;
  source_url?: string;
  content_type?: string;
  title: string;
  content: string;
  author?: string;
  tags?: string[];
  manual_note?: string;
  source_type?: string;
  category?: string;
  metrics?: Record<string, number>;
}) {
  const { data } = await api.post("/api/collect/save", {
    content_type: "post",
    tags: [],
    comments_keywords: [],
    metrics: {},
    source_type: "paste",
    ...payload,
  });
  return data;
}

export async function analyzeCollect(contentId: number, forceCloud = false) {
  const { data } = await api.post(
    `/api/collect/analyze/${contentId}?force_cloud=${forceCloud}`
  );
  return data;
}

export async function listCollect(params?: {
  platform?: string;
  category?: string;
  is_viral?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}) {
  const { data } = await api.get("/api/collect/list", { params });
  return data;
}

export async function collectStats() {
  const { data } = await api.get("/api/collect/stats");
  return data;
}

export async function updateCollect(
  id: number,
  payload: { tags?: string[]; manual_note?: string; category?: string; title?: string; content?: string }
) {
  const { data } = await api.put(`/api/collect/${id}`, payload);
  return data;
}

export async function deleteCollect(id: number) {
  const { data } = await api.delete(`/api/collect/${id}`);
  return data;
}

export async function collectMetaOptions() {
  const { data } = await api.get("/api/collect/meta/options");
  return data;
}

export async function analyzeArkVision(payload: {
  image_url: string;
  text: string;
  model?: string;
}) {
  const { data } = await api.post("/api/ai/ark/vision", payload);
  return data;
}

export async function checkCompliance(content: string) {
  const { data } = await api.post("/api/compliance/check", { content, content_type: "post" });
  return data;
}

export async function listCustomers() {
  const { data } = await api.get("/api/customer/list");
  return data;
}

export async function createCustomer(payload: {
  nickname: string;
  wechat_id?: string;
  source_platform: string;
  tags: string[];
  intention_level: string;
  inquiry_content?: string;
}) {
  const { data } = await api.post("/api/customer/create", payload);
  return data;
}

export async function listPublishRecords() {
  const { data } = await api.get("/api/publish/list");
  return data;
}

export async function createPublishRecord(payload: {
  rewritten_content_id: number;
  platform: string;
  account_name: string;
}) {
  const { data } = await api.post("/api/publish/create", payload);
  return data;
}

// ── 爆款内容采集分析中心 ──────────────────────────────

export async function listInsightTopics() {
  const { data } = await api.get("/api/insight/topics");
  return data;
}

export async function createInsightTopic(payload: {
  name: string;
  description?: string;
  platform_focus?: string[];
  audience_tags?: string[];
  risk_notes?: string;
}) {
  const { data } = await api.post("/api/insight/topics", payload);
  return data;
}

export async function importInsightItem(payload: {
  platform: string;
  title: string;
  body_text: string;
  source_url?: string;
  content_type?: string;
  author_name?: string;
  author_profile_url?: string;
  fans_count?: number;
  account_positioning?: string;
  like_count?: number;
  comment_count?: number;
  share_count?: number;
  collect_count?: number;
  view_count?: number;
  topic_name?: string;
  audience_tags?: string[];
  manual_note?: string;
  source_type?: string;
}) {
  const { data } = await api.post("/api/insight/import", {
    content_type: "post",
    source_type: "manual",
    like_count: 0,
    comment_count: 0,
    share_count: 0,
    collect_count: 0,
    view_count: 0,
    audience_tags: [],
    ...payload,
  });
  return data;
}

export async function listInsightItems(params?: {
  platform?: string;
  topic_id?: number;
  is_hot?: boolean;
  heat_tier?: string;
  ai_analyzed?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}) {
  const { data } = await api.get("/api/insight/list", { params });
  return data;
}

export async function analyzeInsightItem(itemId: number) {
  const { data } = await api.post(`/api/insight/analyze/${itemId}`);
  return data;
}

export async function deleteInsightItem(itemId: number) {
  const { data } = await api.delete(`/api/insight/${itemId}`);
  return data;
}

export async function getInsightStats() {
  const { data } = await api.get("/api/insight/stats");
  return data;
}

export async function retrieveInsightContext(payload: {
  platform: string;
  topic_name?: string;
  audience_tags?: string[];
  limit?: number;
}) {
  const { data } = await api.post("/api/insight/retrieve", {
    audience_tags: [],
    limit: 5,
    ...payload,
  });
  return data;
}
