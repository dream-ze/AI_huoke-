export const API_PREFIX = "/api";
export const API_V1_PREFIX = `${API_PREFIX}/v1`;
export const API_V2_PREFIX = `${API_PREFIX}/v2`;

export const apiRoutes = {
  auth: {
    login: `${API_PREFIX}/auth/login`,
    me: `${API_PREFIX}/auth/me`,
    activeUsers: `${API_PREFIX}/auth/users/active`,
  },
  dashboard: {
    summary: `${API_PREFIX}/dashboard/summary`,
    trend: `${API_PREFIX}/dashboard/trend`,
    aiCallStats: `${API_PREFIX}/dashboard/ai-call-stats`,
    mvpStats: `${API_PREFIX}/mvp/dashboard/stats`,
  },
  compliance: {
    check: `${API_PREFIX}/compliance/check`,
  },
  customer: {
    list: `${API_PREFIX}/customer/list`,
    create: `${API_PREFIX}/customer/create`,
    pendingList: `${API_PREFIX}/customer/pending/list`,
    exportCsv: `${API_PREFIX}/customer/export/csv`,
    detail: (customerId: number) => `${API_PREFIX}/customer/${customerId}`,
    follow: (customerId: number) => `${API_PREFIX}/customer/${customerId}/follow`,
  },
  lead: {
    list: `${API_PREFIX}/lead/list`,
    status: (leadId: number) => `${API_PREFIX}/lead/${leadId}/status`,
    assign: (leadId: number) => `${API_PREFIX}/lead/${leadId}/assign`,
    convertCustomer: (leadId: number) => `${API_PREFIX}/lead/${leadId}/convert-customer`,
    attribution: `${API_PREFIX}/lead/stats/attribution`,
    funnel: `${API_PREFIX}/lead/stats/funnel`,
  },
  publish: {
    list: `${API_PREFIX}/publish/list`,
    create: `${API_PREFIX}/publish/create`,
    detail: (recordId: number) => `${API_PREFIX}/publish/${recordId}`,
    tasksList: `${API_PREFIX}/publish/tasks/list`,
    tasksCreate: `${API_PREFIX}/publish/tasks/create`,
    tasksStats: `${API_PREFIX}/publish/tasks/stats`,
    tasksExportCsv: `${API_PREFIX}/publish/tasks/export/csv`,
    taskDetail: (taskId: number) => `${API_PREFIX}/publish/tasks/${taskId}`,
    taskTrace: (taskId: number) => `${API_PREFIX}/publish/tasks/${taskId}/trace`,
    taskClaim: (taskId: number) => `${API_PREFIX}/publish/tasks/${taskId}/claim`,
    taskAssign: (taskId: number) => `${API_PREFIX}/publish/tasks/${taskId}/assign`,
    taskSubmit: (taskId: number) => `${API_PREFIX}/publish/tasks/${taskId}/submit`,
    taskReject: (taskId: number) => `${API_PREFIX}/publish/tasks/${taskId}/reject`,
    taskClose: (taskId: number) => `${API_PREFIX}/publish/tasks/${taskId}/close`,
    statsByPlatform: `${API_PREFIX}/publish/stats/by-platform`,
    roiTrend: `${API_PREFIX}/publish/stats/roi-trend`,
    contentAnalysis: `${API_PREFIX}/publish/stats/content-analysis`,
  },
  insight: {
    topics: `${API_PREFIX}/insight/topics`,
    topicDetail: (topicId: number) => `${API_PREFIX}/insight/topics/${topicId}`,
    import: `${API_PREFIX}/insight/import`,
    importBatch: `${API_PREFIX}/insight/import/batch`,
    list: `${API_PREFIX}/insight/list`,
    detail: (itemId: number) => `${API_PREFIX}/insight/${itemId}`,
    analyze: (itemId: number) => `${API_PREFIX}/insight/analyze/${itemId}`,
    analyzeBatch: `${API_PREFIX}/insight/analyze/batch`,
    analyzeTasks: `${API_PREFIX}/insight/analyze/tasks`,
    analyzeTaskDetail: (taskId: number) => `${API_PREFIX}/insight/analyze/tasks/${taskId}`,
    authors: `${API_PREFIX}/insight/authors`,
    authorDetail: (authorId: number) => `${API_PREFIX}/insight/authors/${authorId}`,
    retrieve: `${API_PREFIX}/insight/retrieve`,
    stats: `${API_PREFIX}/insight/stats`,
  },
  system: {
    version: `${API_PREFIX}/system/version`,
    opsHealth: `${API_PREFIX}/system/ops/health`,
  },
  social: {
    create: `${API_PREFIX}/social/create`,
    list: `${API_PREFIX}/social/list`,
    detail: (id: number) => `${API_PREFIX}/social/${id}`,
    platforms: `${API_PREFIX}/social/platforms`,
  },
  mvp: {
    inbox: `${API_PREFIX}/mvp/inbox`,
  },
  v1: {
    materialInboxManual: `${API_V1_PREFIX}/material/inbox/manual`,
    arkVision: `${API_V1_PREFIX}/ai/ark/vision`,
  },
  v2: {
    materials: `${API_V2_PREFIX}/materials`,
    materialDetail: (id: number) => `${API_V2_PREFIX}/materials/${id}`,
    materialRewrite: (id: number) => `${API_V2_PREFIX}/materials/${id}/rewrite`,
    materialAnalyze: (id: number) => `${API_V2_PREFIX}/materials/${id}/analyze`,
    materialAdoptGeneration: (materialId: number, generationTaskId: number) =>
      `${API_V2_PREFIX}/materials/${materialId}/generation/${generationTaskId}/adopt`,
  },
} as const;
