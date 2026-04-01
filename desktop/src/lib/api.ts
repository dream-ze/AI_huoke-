import api from "./httpClient";
import { apiRoutes } from "../api/routes";
import { leadApi } from "../api/leadApi";
import { publishApi } from "../api/publishApi";
import { insightApi } from "../api/insightApi";
import { socialAccountApi } from "../api/socialAccountApi";
import { systemApi } from "../api/systemApi";

// Legacy 聚合 API。新增接口优先放到 src/api/* 模块，并复用 apiRoutes。

export async function login(username: string, password: string) {
  const { data } = await api.post(apiRoutes.auth.login, { username, password });
  return data;
}

export async function getCurrentUser() {
  const { data } = await api.get(apiRoutes.auth.me);
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
  const { data } = await api.get(apiRoutes.auth.activeUsers);
  return data as Array<{
    id: number;
    username: string;
    role: string;
    is_active: boolean;
  }>;
}

export async function getDashboardSummary() {
  const { data } = await api.get(apiRoutes.dashboard.summary);
  return data;
}

export async function getDashboardStats() {
  const { data } = await api.get(apiRoutes.dashboard.mvpStats);
  return data;
}

export async function getTrend(days = 7) {
  const { data } = await api.get(`${apiRoutes.dashboard.trend}?days=${days}`);
  return data;
}

export async function getAICallStats(days = 7, scope: "me" | "all" = "me") {
  const { data } = await api.get(`${apiRoutes.dashboard.aiCallStats}?days=${days}&scope=${scope}`);
  return data;
}

export async function listContent() {
  const { data } = await api.get(apiRoutes.v2.materials);
  return data;
}

export async function submitManualToInbox(payload: {
  platform: string;
  title: string;
  content: string;
  tags?: string[];
  note?: string;
}) {
  const { data } = await api.post(apiRoutes.v1.materialInboxManual, {
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
  const { data } = await api.post(apiRoutes.v2.materialRewrite(payload.content_id), {
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
  const { data } = await api.post(`${apiRoutes.v2.materialAnalyze(contentId)}?force_cloud=${forceCloud}`);
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
  const { data } = await api.get(apiRoutes.v2.materials, { params });
  return data || [];
}

export async function getCollectDetail(id: number) {
  const { data } = await api.get(apiRoutes.v2.materialDetail(id));
  return data;
}

export async function rewriteCollect(id: number, targetPlatform: "xiaohongshu" | "douyin" | "zhihu") {
  const { data } = await api.post(apiRoutes.v2.materialRewrite(id), {
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
  const { data } = await api.post(apiRoutes.v2.materialAdoptGeneration(materialId, generationTaskId), {
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
  const { data } = await api.patch(apiRoutes.v2.materialDetail(id), {
    title: payload.title,
    content_text: payload.content,
    review_note: payload.review_note,
    remark: payload.remark,
    status: payload.status,
  });
  return data;
}

export async function deleteCollect(id: number) {
  const { data } = await api.delete(apiRoutes.v2.materialDetail(id));
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
  const { data } = await api.post(apiRoutes.v1.arkVision, payload);
  return data;
}

export async function checkCompliance(content: string) {
  const { data } = await api.post(apiRoutes.compliance.check, { content, content_type: "post" });
  return data;
}

export async function listCustomers() {
  const { data } = await api.get(apiRoutes.customer.list);
  return data;
}

export async function exportCustomersCsv(status?: string) {
  const { data, headers } = await api.get(apiRoutes.customer.exportCsv, {
    params: status ? { status } : undefined,
    responseType: "blob",
  });
  return { blob: data as Blob, headers };
}

export async function createCustomer(payload: {
  nickname: string;
  wechat_id?: string;
  phone?: string;
  source_platform: string;
  source_content_id?: number;
  tags: string[];
  intention_level: string;
  inquiry_content?: string;
  // 扩展字段
  company?: string;
  position?: string;
  industry?: string;
  deal_value?: number;
  email?: string;
  address?: string;
}) {
  const { data } = await api.post(apiRoutes.customer.create, payload);
  return data;
}

export async function listLeads(params?: {
  status?: string;
  owner_id?: number;
  skip?: number;
  limit?: number;
}) {
  return leadApi.list(params);
}

export async function updateLeadStatus(leadId: number, status: string) {
  return leadApi.updateStatus(leadId, status);
}

export async function assignLeadOwner(leadId: number, ownerId?: number) {
  return leadApi.assignOwner(leadId, ownerId);
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
  return leadApi.convertToCustomer(leadId, payload || {});
}

export async function getLeadAttribution(days?: number) {
  return leadApi.getAttributionStats(days);
}

export async function getLeadFunnel(days?: number) {
  return leadApi.getFunnelStats(days);
}

export async function getPublishTaskTrace(taskId: number) {
  return publishApi.getTaskTrace(taskId);
}

export async function listPublishRecords() {
  return publishApi.listRecords();
}

export async function createPublishRecord(payload: {
  rewritten_content_id: number;
  platform: string;
  account_name: string;
}) {
  return publishApi.createRecord(payload);
}

export async function listPublishTasks(params?: {
  status?: string;
  platform?: string;
  assigned_to?: number;
  skip?: number;
  limit?: number;
}) {
  return publishApi.listTasks(params);
}

export async function exportPublishTasksCsv(params?: {
  status?: string;
  platform?: string;
}) {
  const blob = await publishApi.exportTasksCsv(params);
  return { blob, headers: undefined };
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
  return publishApi.createTask(payload);
}

export async function getPublishTaskStats() {
  return publishApi.getTaskStats();
}

export async function claimPublishTask(taskId: number, note?: string) {
  return publishApi.claimTask(taskId, note);
}

export async function assignPublishTask(taskId: number, payload: {
  assigned_to: number;
  note?: string;
}) {
  return publishApi.assignTask(taskId, payload);
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
  return publishApi.submitTask(taskId, payload);
}

export async function rejectPublishTask(taskId: number, note?: string) {
  return publishApi.rejectTask(taskId, note);
}

export async function closePublishTask(taskId: number, note?: string) {
  return publishApi.closeTask(taskId, note);
}

// ── 发布效果统计 ──────────────────────────────────────

export async function getPublishStatsByPlatform(days?: number) {
  return publishApi.getStatsByPlatform(days);
}

export async function getPublishRoiTrend(days?: number) {
  return publishApi.getRoiTrend(days);
}

export async function getPublishContentAnalysis(days?: number) {
  return publishApi.getContentAnalysis(days);
}

// ── 爆款内容采集分析中心 ──────────────────────────────

export async function listInsightTopics() {
  return insightApi.listTopics();
}

export async function createInsightTopic(payload: {
  name: string;
  description?: string;
  platform_focus?: string[];
  audience_tags?: string[];
  risk_notes?: string;
}) {
  return insightApi.createTopic(payload);
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
  return insightApi.importItem({
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
  return insightApi.listItems(params);
}

export async function listInsightAnalyzeTasks(params?: {
  skip?: number;
  limit?: number;
}) {
  return insightApi.listAnalyzeTasks(params);
}

export async function getSystemVersion() {
  return systemApi.getVersion();
}

export async function getSystemHealth() {
  return systemApi.getHealth();
}

export async function analyzeInsightItem(itemId: number) {
  return insightApi.analyzeItem(itemId);
}

export async function deleteInsightItem(itemId: number) {
  return insightApi.deleteItem(itemId);
}

export async function getInsightStats() {
  return insightApi.getStats();
}

export async function retrieveInsightContext(payload: {
  platform: string;
  topic_name?: string;
  audience_tags?: string[];
  limit?: number;
}) {
  return insightApi.retrieve({
    audience_tags: [],
    limit: 5,
    ...payload,
  });
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
export async function mvpBatchBuildKnowledge(materialIds: number[]) {
  const { data } = await api.post("/api/mvp/materials/batch-build-knowledge", {
    material_ids: materialIds,
  });
  return data;
}
export async function mvpRewriteHot(materialId: number) {
  const { data } = await api.post(`/api/mvp/materials/${materialId}/rewrite`);
  return data;
}
export async function mvpToggleMaterialHot(materialId: number) {
  const { data } = await api.post(`/api/mvp/materials/${materialId}/toggle-hot`);
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

// 知识库分库统计（带最近更新时间）
export async function getKnowledgeLibraryStats() {
  const resp = await api.get("/api/mvp/knowledge/library-stats");
  return resp.data || [];
}

// 按分库列出知识条目
export async function listKnowledgeByLibrary(
  library_type: string,
  params?: { page?: number; size?: number; keyword?: string }
) {
  const resp = await api.get(`/api/mvp/knowledge/library/${library_type}`, { params });
  return resp.data || { items: [], total: 0, page: 1, size: 20 };
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

// ── 合规规则管理 ──
export async function listComplianceRules(params?: Record<string, any>) {
  const { data } = await api.get("/api/mvp/compliance/rules", { params });
  return data;
}

export async function createComplianceRule(payload: Record<string, any>) {
  const { data } = await api.post("/api/mvp/compliance/rules", payload);
  return data;
}

export async function updateComplianceRule(ruleId: number, payload: Record<string, any>) {
  const { data } = await api.put(`/api/mvp/compliance/rules/${ruleId}`, payload);
  return data;
}

export async function deleteComplianceRule(ruleId: number) {
  const { data } = await api.delete(`/api/mvp/compliance/rules/${ruleId}`);
  return data;
}

export async function testComplianceRule(text: string) {
  const { data } = await api.post("/api/mvp/compliance/test", { text });
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
    timeout: 180000,  // 全流程生成需要较长时间（与后端180s超时对齐）
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

// ── 反馈闭环 ──

// 提交反馈
export async function submitFeedback(params: {
  generation_id: string;
  query: string;
  generated_text: string;
  feedback_type: 'adopted' | 'modified' | 'rejected';
  modified_text?: string;
  rating?: number;
  feedback_tags?: string[];
  knowledge_ids_used?: number[];
}) {
  const { data } = await api.post('/api/mvp/feedback', params);
  return data as {
    success: boolean;
    feedback_id: number;
    message: string;
    quality_scores_updated: number;
  };
}

// 获取反馈统计
export async function getFeedbackStats(days: number = 30) {
  const { data } = await api.get(`/api/mvp/feedback/stats?days=${days}`);
  return data as {
    total_feedback: number;
    adopted_count: number;
    modified_count: number;
    rejected_count: number;
    adoption_rate: number;
    modification_rate: number;
    rejection_rate: number;
    avg_rating: number | null;
    recent_feedback_count: number;
  };
}

// 获取知识库质量排行
export async function getKnowledgeQualityRankings(limit: number = 20, order: 'asc' | 'desc' = 'desc') {
  const { data } = await api.get(`/api/mvp/knowledge/quality/rankings?limit=${limit}&order=${order}`);
  return data as {
    items: Array<{
      knowledge_id: number;
      title: string;
      quality_score: number;
      reference_count: number;
      positive_feedback: number;
      negative_feedback: number;
      weight_boost: number;
      last_referenced_at: string | null;
    }>;
    total: number;
  };
}

// 获取学习建议
export async function getLearningSuggestions() {
  const { data } = await api.get('/api/mvp/knowledge/quality/suggestions');
  return data as {
    suggestions: Array<{
      type: string;
      knowledge_id: number;
      title: string;
      current_score: number;
      suggestion: string;
      priority: string;
      reason: string;
    }>;
    boost_candidates: number;
    downgrade_candidates: number;
    remove_candidates: number;
  };
}

// 应用权重调整
export async function applyWeightAdjustment() {
  const { data } = await api.post('/api/mvp/knowledge/quality/adjust');
  return data as {
    boosted_count: number;
    downgraded_count: number;
    cold_marked_count: number;
    message: string;
    details: Array<Record<string, any>>;
  };
}

// 获取反馈标签选项
export async function getFeedbackTags() {
  const { data } = await api.get('/api/mvp/feedback/tags');
  return data.tags as string[];
}

// ═══════════ 社交账号管理 API ═══════════

export async function listSocialAccounts(platform?: string) {
  return socialAccountApi.list(platform);
}

export async function createSocialAccount(payload: {
  platform: string;
  account_name: string;
  account_id?: string;
  avatar_url?: string;
  notes?: string;
}) {
  return socialAccountApi.create(payload);
}

export async function updateSocialAccount(
  id: number,
  payload: {
    account_name?: string;
    account_id?: string;
    avatar_url?: string;
    status?: string;
    followers_count?: number;
    notes?: string;
  }
) {
  return socialAccountApi.update(id, payload);
}

export async function deleteSocialAccount(id: number) {
  return socialAccountApi.delete(id);
}

export async function getSocialPlatforms() {
  return socialAccountApi.getPlatforms();
}

// ── 知识图谱 ──

// 构建全量知识图谱关系
export async function buildKnowledgeGraph() {
  const { data } = await api.post('/api/mvp/knowledge/graph/build');
  return data as {
    total_items: number;
    processed: number;
    relations_created: number;
    errors: number;
    message: string;
  };
}

// 为单条知识构建关系
export async function buildSingleKnowledgeRelations(knowledgeId: number) {
  const { data } = await api.post(`/api/mvp/knowledge/${knowledgeId}/relations/build`);
  return data as {
    success: boolean;
    knowledge_id: number;
    relations_created: number;
    message: string;
  };
}

// 获取关联知识条目
export async function getRelatedKnowledgeItems(
  knowledgeId: number,
  params?: { relation_type?: string; limit?: number }
) {
  const { data } = await api.get(`/api/mvp/knowledge/${knowledgeId}/related`, { params });
  return data as { items: any[]; total: number };
}

// 获取知识图谱数据
export async function getKnowledgeGraph(params?: { library_type?: string; limit?: number }) {
  const { data } = await api.get('/api/mvp/knowledge/graph', { params });
  return data as {
    nodes: Array<{
      id: number;
      title: string;
      platform: string | null;
      audience: string | null;
      topic: string | null;
      library_type: string | null;
      use_count: number;
      is_hot: boolean;
    }>;
    edges: Array<{
      source: number;
      target: number;
      type: string;
      weight: number;
    }>;
    stats: { node_count: number; edge_count: number };
  };
}

// 获取图谱统计
export async function getGraphStats() {
  const { data } = await api.get('/api/mvp/knowledge/graph/stats');
  return data as {
    node_count: number;
    edge_count: number;
    avg_degree: number;
    nodes_with_relations: number;
    nodes_with_embedding: number;
    relation_type_stats: Record<string, number>;
    connectivity_ratio: number;
  };
}

// 获取主题聚类
export async function getTopicClusters(minSize: number = 2) {
  const { data } = await api.get(`/api/mvp/knowledge/graph/clusters?min_size=${minSize}`);
  return data as {
    clusters: Array<{
      topic: string;
      item_ids: number[];
      items: Array<{ id: number; title: string; topic: string | null }>;
      count: number;
    }>;
    total: number;
  };
}

// 图增强检索
export async function enhancedKnowledgeSearch(
  query: string,
  params?: { top_k?: number; expand_limit?: number }
) {
  const { data } = await api.get('/api/mvp/knowledge/graph/enhanced-search', {
    params: { query, ...params }
  });
  return data as {
    results: Array<{
      id: number;
      title: string;
      content: string;
      score: number;
      source: string;
      chunk_id: number | null;
      relation_weight: number | null;
    }>;
    total: number;
  };
}
