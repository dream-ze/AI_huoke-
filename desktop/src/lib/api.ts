import axios from "axios";
import { clearToken, getToken } from "./auth";

function resolveApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const runtimeBase = localStorage.getItem("zhk_api_base_url");
    if (runtimeBase) return runtimeBase;
  }
  return import.meta.env.VITE_API_BASE_URL || "";
}

// When served by the backend on the same origin, baseURL can be empty.
// During local dev (Vite on 5173), set VITE_API_BASE_URL=http://localhost:8000
const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 20000
});

api.interceptors.request.use((config) => {
  config.baseURL = resolveApiBaseUrl();
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
      clearToken("expired");
    }
    return Promise.reject(error);
  }
);

export async function login(username: string, password: string) {
  const { data } = await api.post("/api/auth/login", { username, password });
  return data;
}

export async function getCurrentUser() {
  const { data } = await api.get("/api/auth/me");
  return data as {
    id: number;
    username: string;
    email: string;
    role: string;
    is_active: boolean;
    created_at: string;
  };
}

export async function listActiveUsers() {
  const { data } = await api.get("/api/auth/users/active");
  return data as Array<{
    id: number;
    username: string;
    role: string;
    is_active: boolean;
  }>;
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
    xiaohongshu: "/api/v1/ai/rewrite/xiaohongshu",
    douyin: "/api/v1/ai/rewrite/douyin",
    zhihu: "/api/v1/ai/rewrite/zhihu"
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
  const { data } = await api.post("/api/v1/collect/parse-link", { url });
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
  const { data } = await api.post("/api/v1/collect/save", {
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
    `/api/v1/collect/analyze/${contentId}?force_cloud=${forceCloud}`
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
  const { data } = await api.get("/api/v1/collect/list", { params });
  return data;
}

export async function collectStats() {
  const { data } = await api.get("/api/v1/collect/stats");
  return data;
}

export async function updateCollect(
  id: number,
  payload: { tags?: string[]; manual_note?: string; category?: string; title?: string; content?: string }
) {
  const { data } = await api.put(`/api/v1/collect/${id}`, payload);
  return data;
}

export async function deleteCollect(id: number) {
  const { data } = await api.delete(`/api/v1/collect/${id}`);
  return data;
}

export async function collectMetaOptions() {
  const { data } = await api.get("/api/v1/collect/meta/options");
  return data;
}

export async function createInboxItem(payload: {
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
  const { data } = await api.post("/api/v1/inbox/create", {
    content_type: "post",
    tags: [],
    metrics: {},
    source_type: "paste",
    ...payload,
  });
  return data;
}

export async function listInboxItems(params?: {
  status?: string;
  platform?: string;
  search?: string;
  skip?: number;
  limit?: number;
}) {
  const { data } = await api.get("/api/v1/inbox/list", { params });
  return data;
}

export async function getInboxStats() {
  const { data } = await api.get("/api/v1/inbox/stats");
  return data;
}

export async function analyzeInboxItem(inboxId: number, forceCloud = false) {
  const { data } = await api.post(`/api/v1/inbox/${inboxId}/analyze?force_cloud=${forceCloud}`);
  return data;
}

export async function promoteInboxItem(inboxId: number) {
  const { data } = await api.post(`/api/v1/inbox/${inboxId}/promote`);
  return data;
}

export async function discardInboxItem(inboxId: number, reviewNote?: string) {
  const { data } = await api.post(`/api/v1/inbox/${inboxId}/discard`, null, {
    params: reviewNote ? { review_note: reviewNote } : undefined,
  });
  return data;
}

export async function analyzeArkVision(payload: {
  image_url: string;
  text: string;
  model?: string;
}) {
  const { data } = await api.post("/api/v1/ai/ark/vision", payload);
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

export async function exportCustomersCsv(status?: string) {
  const { data, headers } = await api.get("/api/customer/export/csv", {
    params: status ? { status } : undefined,
    responseType: "blob",
  });
  return { blob: data as Blob, headers };
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

export async function listLeads(params?: {
  status?: string;
  owner_id?: number;
  skip?: number;
  limit?: number;
}) {
  const { data } = await api.get("/api/lead/list", { params });
  return data;
}

export async function updateLeadStatus(leadId: number, status: string) {
  const { data } = await api.put(`/api/lead/${leadId}/status`, { status });
  return data;
}

export async function assignLeadOwner(leadId: number, ownerId?: number) {
  const { data } = await api.post(`/api/lead/${leadId}/assign`, {
    owner_id: ownerId,
  });
  return data;
}

export async function convertLeadToCustomer(
  leadId: number,
  payload?: {
    nickname?: string;
    wechat_id?: string;
    phone?: string;
    intention_level?: string;
    tags?: string[];
    inquiry_content?: string;
  },
) {
  const { data } = await api.post(`/api/lead/${leadId}/convert-customer`, payload || {});
  return data;
}

export async function getPublishTaskTrace(taskId: number) {
  const { data } = await api.get(`/api/publish/tasks/${taskId}/trace`);
  return data as {
    task_id: number;
    publish_record_id?: number;
    lead_id?: number;
    customer_id?: number;
  };
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

export async function listPublishTasks(params?: {
  status?: string;
  platform?: string;
  assigned_to?: number;
  skip?: number;
  limit?: number;
}) {
  const { data } = await api.get("/api/publish/tasks/list", { params });
  return data;
}

export async function exportPublishTasksCsv(params?: {
  status?: string;
  platform?: string;
}) {
  const { data, headers } = await api.get("/api/publish/tasks/export/csv", {
    params,
    responseType: "blob",
  });
  return { blob: data as Blob, headers };
}

export async function createPublishTask(payload: {
  rewritten_content_id?: number;
  platform: string;
  account_name: string;
  task_title: string;
  content_text: string;
  assigned_to?: number;
  due_time?: string;
}) {
  const { data } = await api.post("/api/publish/tasks/create", payload);
  return data;
}

export async function getPublishTaskStats() {
  const { data } = await api.get("/api/publish/tasks/stats");
  return data;
}

export async function claimPublishTask(taskId: number, note?: string) {
  const { data } = await api.post(`/api/publish/tasks/${taskId}/claim`, {
    note,
  });
  return data;
}

export async function assignPublishTask(taskId: number, payload: {
  assigned_to: number;
  note?: string;
}) {
  const { data } = await api.post(`/api/publish/tasks/${taskId}/assign`, payload);
  return data;
}

export async function submitPublishTask(
  taskId: number,
  payload: {
    post_url?: string;
    posted_at?: string;
    views?: number;
    likes?: number;
    comments?: number;
    favorites?: number;
    shares?: number;
    private_messages?: number;
    wechat_adds?: number;
    leads?: number;
    valid_leads?: number;
    conversions?: number;
    note?: string;
  },
) {
  const { data } = await api.post(`/api/publish/tasks/${taskId}/submit`, payload);
  return data;
}

export async function rejectPublishTask(taskId: number, note?: string) {
  const { data } = await api.post(`/api/publish/tasks/${taskId}/reject`, {
    note,
  });
  return data;
}

export async function closePublishTask(taskId: number, note?: string) {
  const { data } = await api.post(`/api/publish/tasks/${taskId}/close`, {
    note,
  });
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

export async function listInsightAnalyzeTasks(params?: {
  skip?: number;
  limit?: number;
}) {
  const { data } = await api.get("/api/insight/analyze/tasks", { params });
  return data;
}

export async function getSystemVersion() {
  const { data } = await api.get("/api/system/version");
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
