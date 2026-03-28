import axios from "axios";
import { clearToken, getToken } from "./auth";

function resolveApiBaseUrl(): string {
  const isElectron = typeof window !== "undefined" && !!(window as any).desktop?.isElectron;
  if (typeof window !== "undefined") {
    const runtimeBase = localStorage.getItem("zhk_api_base_url");
    // Only Electron desktop should honor runtime localhost overrides.
    if (isElectron && runtimeBase) return runtimeBase;
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

export async function getDashboardStats() {
  const { data } = await api.get("/api/mvp/dashboard/stats");
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
  const { data } = await api.get("/api/v2/materials");
  return data;
}

export async function submitManualToInbox(payload: {
  platform: string;
  title: string;
  content: string;
  tags?: string[];
  note?: string;
}) {
  const { data } = await api.post("/api/v1/material/inbox/manual", {
    platform: payload.platform,
    title: payload.title,
    content: payload.content,
    tags: payload.tags || [],
    note: payload.note,
  });
  return data as { inbox_id: number; status: string };
}

export async function rewriteContent(payload: {
  content_id: number;
  target_platform: "xiaohongshu" | "douyin" | "zhihu";
  topic_name?: string;
  audience_tags?: string[];
}) {
  const { data } = await api.post(`/api/v2/materials/${payload.content_id}/rewrite`, {
    target_platform: payload.target_platform,
    task_type: "rewrite",
  });
  return {
    ...data,
    rewritten: data?.output_text || "",
    insight_reference_count: Array.isArray(data?.references) ? data.references.length : 0,
  };
}

// ── 素材中台 ──────────────────────────────────────────
export async function analyzeCollect(contentId: number, forceCloud = false) {
  const { data } = await api.post(`/api/v2/materials/${contentId}/analyze?force_cloud=${forceCloud}`);
  return data;
}

export async function listCollect(params?: {
  platform?: string;
  search?: string;
  status?: string;
  risk_status?: string;
  source_channel?: string;
  skip?: number;
  limit?: number;
}) {
  const { data } = await api.get("/api/v2/materials", { params });
  return data || [];
}

export async function getCollectDetail(id: number) {
  const { data } = await api.get(`/api/v2/materials/${id}`);
  return data;
}

export async function rewriteCollect(id: number, targetPlatform: "xiaohongshu" | "douyin" | "zhihu") {
  const { data } = await api.post(`/api/v2/materials/${id}/rewrite`, {
    target_platform: targetPlatform,
  });
  return {
    ...data,
    rewritten: data?.output_text || "",
    llm_output: data?.llm_output || "",
    tags: data?.tags || null,
    copies: Array.isArray(data?.copies) ? data.copies : [],
    selected_variant: data?.selected_variant || null,
    compliance: data?.compliance || null,
  };
}

export async function adoptGenerationVersion(materialId: number, generationTaskId: number, reason?: string) {
  const { data } = await api.post(`/api/v2/materials/${materialId}/generation/${generationTaskId}/adopt`, {
    adopt: true,
    reason,
  });
  return data as {
    material_id: number;
    generation_task_id: number;
    adoption_status: string;
    message: string;
  };
}

export async function updateCollect(
  id: number,
  payload: { review_note?: string; remark?: string; status?: string; title?: string; content?: string }
) {
  const { data } = await api.patch(`/api/v2/materials/${id}`, {
    title: payload.title,
    content_text: payload.content,
    review_note: payload.review_note,
    remark: payload.remark,
    status: payload.status,
  });
  return data;
}

export async function deleteCollect(id: number) {
  const { data } = await api.delete(`/api/v2/materials/${id}`);
  return data;
}

export async function collectMetaOptions() {
  return {
    platforms: [
      ["xiaohongshu", "小红书"],
      ["douyin", "抖音"],
      ["zhihu", "知乎"],
      ["xianyu", "咸鱼"],
      ["wechat", "微信"],
      ["other", "其他"],
    ],
    categories: ["额度提升", "征信修复", "负债优化", "职业认证", "房贷公积金", "车贷", "企业贷款", "引流获客", "客户话术", "爆款参考", "其他"],
  };
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

export async function getSystemHealth() {
  const { data } = await api.get("/api/system/ops/health");
  return data as {
    status: string;
    database: string;
    redis: string;
    timestamp: string;
    version?: string;
  };
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

// ── 新采集链路（v1 pipeline）────────────────────────────────────

export async function createKeywordCollectTask(payload: {
  platform: string;
  keyword: string;
  max_items?: number;
}) {
  const { data } = await api.post("/api/v1/collector/tasks/keyword", {
    platform: payload.platform,
    keyword: payload.keyword,
    max_items: payload.max_items ?? 20,
  });
  return data as {
    task_id: number;
    status: string;
    result_count: number;
    inserted: number;
    review: number;
    discard: number;
    duplicate: number;
    failed: number;
  };
}

export async function submitEmployeeLink(payload: { url: string; note?: string }) {
  const { data } = await api.post("/api/v1/employee-submissions/link", {
    url: payload.url,
    note: payload.note,
  });
  return data as { submission_id: number; status: string };
}

export async function listMaterialInbox(params?: {
  status?: string;
  platform?: string;
  source_channel?: string;
  keyword?: string;
  risk_status?: string;
  is_duplicate?: boolean;
  skip?: number;
  limit?: number;
}) {
  const { data } = await api.get("/api/v1/material/inbox", { params });
  return data as Array<{
    id: number;
    source_channel: string;
    source_task_id?: number | null;
    source_submission_id?: number | null;
    platform: string;
    source_id?: string | null;
    keyword?: string | null;
    title?: string | null;
    author?: string | null;
    content?: string | null;
    url?: string | null;
    cover_url?: string | null;
    like_count: number;
    comment_count: number;
    collect_count: number;
    share_count: number;
    parse_status: string;
    risk_status: string;
    quality_score: number;
    relevance_score: number;
    lead_score: number;
    is_duplicate: boolean;
    filter_reason?: string | null;
    status: string;
    submitted_by_employee_id?: number | null;
    remark?: string | null;
    review_note?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
  }>;
}

export async function getMaterialInboxItem(id: number) {
  const { data } = await api.get(`/api/v1/material/inbox/${id}`);
  return data;
}

export async function updateMaterialInboxStatus(id: number, payload: {
  status: "pending" | "review" | "discard";
  review_note?: string;
}) {
  const { data } = await api.patch(`/api/v1/material/inbox/${id}/status`, payload);
  return data;
}

// ═══════════ MVP API ═══════════

// 收件箱
export async function mvpListInbox(params?: Record<string, any>) {
  const { data } = await api.get("/api/mvp/inbox", { params });
  return data;
}
export async function mvpGetInbox(id: number) {
  const { data } = await api.get(`/api/mvp/inbox/${id}`);
  return data;
}
export async function mvpInboxToMaterial(id: number) {
  const { data } = await api.post(`/api/mvp/inbox/${id}/to-material`);
  return data;
}
export async function mvpInboxMarkHot(id: number) {
  const { data } = await api.post(`/api/mvp/inbox/${id}/mark-hot`);
  return data;
}
export async function mvpInboxDiscard(id: number) {
  const { data } = await api.post(`/api/mvp/inbox/${id}/discard`);
  return data;
}

// 素材库
export async function mvpListMaterials(params?: Record<string, any>) {
  const { data } = await api.get("/api/mvp/materials", { params });
  return data;
}
export async function mvpGetMaterial(id: number) {
  const { data } = await api.get(`/api/mvp/materials/${id}`);
  return data;
}
export async function mvpCreateMaterial(payload: Record<string, any>) {
  const { data } = await api.post("/api/mvp/materials", payload);
  return data;
}
export async function mvpBuildKnowledge(materialId: number) {
  const { data } = await api.post(`/api/mvp/materials/${materialId}/build-knowledge`);
  return data;
}
export async function mvpRewriteHot(materialId: number) {
  const { data } = await api.post(`/api/mvp/materials/${materialId}/rewrite`);
  return data;
}
export async function mvpUpdateTags(materialId: number, tagIds: number[]) {
  const { data } = await api.post(`/api/mvp/materials/${materialId}/tags`, { tag_ids: tagIds });
  return data;
}

// 知识库
export async function mvpListKnowledge(params?: Record<string, any>) {
  const { data } = await api.get("/api/mvp/knowledge", { params });
  return data;
}
export async function mvpGetKnowledge(id: number) {
  const { data } = await api.get(`/api/mvp/knowledge/${id}`);
  return data;
}
export async function mvpBuildKnowledgeFromMaterial(payload: { material_id: number }) {
  const { data } = await api.post("/api/mvp/knowledge/build", payload);
  return data;
}
export async function mvpSearchKnowledge(payload: { query: string; platform?: string; audience?: string }) {
  const { data } = await api.post("/api/mvp/knowledge/search", payload);
  return data;
}

// 知识库分库统计
export async function getKnowledgeLibraries() {
  const resp = await api.get("/api/mvp/knowledge/libraries");
  return resp.data?.libraries || [];
}

// 知识库切块列表
export async function getKnowledgeChunks(knowledgeId: number) {
  const resp = await api.get(`/api/mvp/knowledge/chunks/${knowledgeId}`);
  return resp.data?.chunks || [];
}

// 重建知识索引
export async function reindexKnowledge(payload?: { knowledge_ids?: number[], embedding_model?: string }) {
  const resp = await api.post("/api/mvp/knowledge/reindex", payload || {});
  return resp.data;
}

// AI工作台
export async function mvpGenerate(payload: Record<string, any>) {
  const { data } = await api.post("/api/mvp/generate", payload);
  return data;
}
export async function mvpGenerateFinal(payload: Record<string, any>) {
  const { data } = await api.post("/api/mvp/generate/final", payload);
  return data;
}

// 合规审核
export async function mvpComplianceCheck(payload: { text: string }) {
  const { data } = await api.post("/api/mvp/compliance/check", payload);
  return data;
}

// 标签
export async function mvpListTags(params?: { type?: string }) {
  const { data } = await api.get("/api/mvp/tags", { params });
  return data;
}
export async function mvpCreateTag(payload: { name: string; type: string }) {
  const { data } = await api.post("/api/mvp/tags", payload);
  return data;
}

// 统计
export async function mvpGetStatsOverview() {
  const { data } = await api.get("/api/mvp/stats/overview");
  return data;
}

// 全流程内容生成（6步链路）
export async function generateFullPipeline(payload: {
  platform: string;
  account_type: string;
  audience: string;
  topic: string;
  goal?: string;
  model?: string;  // "volcano" | "local"
  extra_requirements?: string;
  tone?: string;
}) {
  const { data } = await api.post("/api/mvp/generate/full-pipeline", payload, {
    timeout: 120000,  // 全流程生成需要较长时间
  });
  return data;
}

// ── 采集中心 V1 ──────────────────────────────────────────

// 采集搜索
export async function collectorSearch(params: {
  platform: string;
  keyword: string;
  count: number;
  fetch_detail?: boolean;
  fetch_comments?: boolean;
  source_type?: string;
}) {
  const { data } = await api.post('/api/v1/collector/search', params, {
    timeout: 180000  // 采集可能需要较长时间
  });
  return data;
}

// 获取采集任务列表
export async function getCollectorTasks(params?: { page?: number; size?: number }) {
  const { data } = await api.get('/api/v1/collector/tasks', { params });
  return data;
}

// 获取采集结果列表
export async function getCollectorResults(params?: { page?: number; size?: number }) {
  const { data } = await api.get('/api/v1/collector/results', { params });
  const list = Array.isArray(data) ? data : data?.items || [];
  
  return list.map((item: any) => ({
    id: item.id,
    title: item.title,
    platform: item.platform,
    author: item.author_name || item.author,
    content: item.content_preview || item.content,
    summary: item.content_preview ? item.content_preview.substring(0, 100) : '',
    tags: item.tags || [],
    risk_level: item.risk_status || item.risk_level || 'low',
    ingest_status: item.status || item.ingest_status || 'pending',
    source_url: item.source_url,
    created_at: item.created_at || new Date().toISOString(),
  }));
}

// 自动入库Pipeline
export async function autoIngestPipeline(params: {
  title: string;
  content: string;
  platform?: string;
  source_url?: string;
  author?: string;
}) {
  const { data } = await api.post('/api/mvp/raw-contents/auto-pipeline', params);
  return data;
}
