import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  assignPublishTask,
  claimPublishTask,
  closePublishTask,
  createPublishTask,
  exportPublishTasksCsv,
  getCurrentUser,
  getPublishTaskTrace,
  getPublishTaskStats,
  listPublishTasks,
  listActiveUsers,
  listSocialAccounts,
  rejectPublishTask,
  submitPublishTask,
  getPublishStatsByPlatform,
  getPublishRoiTrend,
  getPublishContentAnalysis,
} from "../lib/api";
import { publishApi } from "../api/publishApi";
import { PublishTask, PublishTaskStats, UserSummary, ContentLeadStats, ContentLeadItem } from "../types";

interface SocialAccount {
  id: number;
  platform: string;
  account_name: string;
  account_id: string | null;
  status: string;
}

interface PlatformStats {
  platform: string;
  total_tasks: number;
  completed_tasks: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_wechat_adds: number;
  total_leads: number;
  total_valid_leads: number;
  total_conversions: number;
  avg_views_per_task: number;
  conversion_rate: number;
}

interface RoiTrendItem {
  date: string;
  publish_count: number;
  total_leads: number;
  total_valid_leads: number;
  total_conversions: number;
  lead_rate: number;
  conversion_rate: number;
}

interface ContentAnalysisItem {
  platform: string;
  task_count: number;
  avg_views: number;
  avg_likes: number;
  avg_wechat_adds: number;
  avg_conversions: number;
  best_task_title: string | null;
  best_task_conversions: number;
}

const emptyStats: PublishTaskStats = {
  total: 0,
  pending: 0,
  claimed: 0,
  submitted: 0,
  rejected: 0,
  closed: 0,
};

export function PublishPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<PublishTaskStats>(emptyStats);
  const [tasks, setTasks] = useState<PublishTask[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyTaskId, setBusyTaskId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [platformFilter, setPlatformFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [assignTaskId, setAssignTaskId] = useState(0);

  // 效果分析数据
  const [platformStats, setPlatformStats] = useState<PlatformStats[]>([]);
  const [roiTrend, setRoiTrend] = useState<RoiTrendItem[]>([]);
  const [contentAnalysis, setContentAnalysis] = useState<ContentAnalysisItem[]>([]);
  const [statsDays, setStatsDays] = useState(30);
  const [statsLoading, setStatsLoading] = useState(false);

  const [taskForm, setTaskForm] = useState({
    platform: "xiaohongshu",
    account_name: "主账号",
    task_title: "",
    content_text: "",
    rewritten_content_id: "",
  });

  const [submitForm, setSubmitForm] = useState({
    taskId: 0,
    post_url: "",
    views: "0",
    likes: "0",
    comments: "0",
    favorites: "0",
    shares: "0",
    private_messages: "0",
    wechat_adds: "0",
    leads: "0",
    valid_leads: "0",
    conversions: "0",
    note: "",
  });

  const [assignForm, setAssignForm] = useState({
    assigned_to: "",
    note: "",
  });

  // 社交账号列表
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [useCustomAccount, setUseCustomAccount] = useState(false);

  const [message, setMessage] = useState("");

  // 线索追踪面板状态
  const [leadPanelTaskId, setLeadPanelTaskId] = useState<number | null>(null);
  const [leadPanelData, setLeadPanelData] = useState<ContentLeadStats | null>(null);
  const [leadPanelLoading, setLeadPanelLoading] = useState(false);

  // Tab 切换状态
  const [activeTab, setActiveTab] = useState<"tasks" | "accounts">("tasks");

  async function refreshData() {
    const [statsData, listData] = await Promise.all([
      getPublishTaskStats().catch(() => emptyStats),
      listPublishTasks({
        platform: platformFilter === "all" ? undefined : platformFilter,
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: 100,
      }).catch(() => []),
    ]);
    setStats(statsData || emptyStats);
    setTasks(listData || []);
  }

  async function loadEffectStats() {
    setStatsLoading(true);
    try {
      const [platformData, roiData, contentData] = await Promise.all([
        getPublishStatsByPlatform(statsDays).catch(() => []),
        getPublishRoiTrend(statsDays).catch(() => []),
        getPublishContentAnalysis(statsDays).catch(() => []),
      ]);
      setPlatformStats(platformData || []);
      setRoiTrend(roiData || []);
      setContentAnalysis(contentData || []);
    } catch {
      // 静默处理错误
    } finally {
      setStatsLoading(false);
    }
  }

  // 加载社交账号列表
  async function loadSocialAccounts(platform: string) {
    try {
      const accounts = await listSocialAccounts(platform);
      setSocialAccounts(accounts.filter((a) => a.status === "active"));
    } catch {
      setSocialAccounts([]);
    }
  }

  useEffect(() => {
    async function run() {
      try {
        const [me, activeUsers] = await Promise.all([
          getCurrentUser(),
          listActiveUsers().catch(() => []),
        ]);
        setCurrentUserId(me.id);
        setUsers(activeUsers || []);
        await Promise.all([
          refreshData(),
          loadEffectStats(),
        ]);
        // 初始加载当前平台的社交账号
        await loadSocialAccounts(taskForm.platform);
      } finally {
        setLoading(false);
      }
    }
    run();
  }, [platformFilter, statusFilter]);

  // 当统计天数变化时重新加载效果分析
  useEffect(() => {
    loadEffectStats();
  }, [statsDays]);

  function getUserLabel(userId?: number) {
    if (!userId) return "未分配";
    const user = users.find((item) => item.id === userId);
    return user ? `${user.username} (#${user.id})` : `用户 #${userId}`;
  }

  async function onCreateTask(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    setCreating(true);
    try {
      await createPublishTask({
        platform: taskForm.platform,
        account_name: taskForm.account_name,
        task_title: taskForm.task_title,
        content_text: taskForm.content_text,
        rewritten_content_id: taskForm.rewritten_content_id
          ? Number(taskForm.rewritten_content_id)
          : undefined,
      });
      setMessage("发布任务已创建，可直接领取执行");
      setTaskForm((current) => ({
        ...current,
        task_title: "",
        content_text: "",
        rewritten_content_id: "",
      }));
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "创建任务失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleClaim(taskId: number) {
    setBusyTaskId(taskId);
    setMessage("");
    try {
      await claimPublishTask(taskId, "开始执行发布任务");
      setMessage(`任务 #${taskId} 已领取`);
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "领取失败");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleReject(taskId: number) {
    const reason = window.prompt("请输入驳回原因", "发布素材或数据不完整");
    if (!reason) return;
    setBusyTaskId(taskId);
    setMessage("");
    try {
      await rejectPublishTask(taskId, reason);
      setMessage(`任务 #${taskId} 已驳回`);
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "驳回失败");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleClose(taskId: number) {
    setBusyTaskId(taskId);
    setMessage("");
    try {
      await closePublishTask(taskId, "任务闭环完成");
      setMessage(`任务 #${taskId} 已关闭`);
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "关闭失败");
    } finally {
      setBusyTaskId(null);
    }
  }

  function openAssignPanel(task: PublishTask) {
    setAssignTaskId(task.id);
    setAssignForm({
      assigned_to: task.assigned_to ? String(task.assigned_to) : "",
      note: task.assigned_to ? "改派执行人" : "分配执行人",
    });
  }

  async function onAssignTask(e: FormEvent) {
    e.preventDefault();
    if (!assignTaskId || !assignForm.assigned_to) return;
    setBusyTaskId(assignTaskId);
    setMessage("");
    try {
      await assignPublishTask(assignTaskId, {
        assigned_to: Number(assignForm.assigned_to),
        note: assignForm.note || undefined,
      });
      setMessage(`任务 #${assignTaskId} 已完成分配`);
      setAssignTaskId(0);
      setAssignForm({ assigned_to: "", note: "" });
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "分配失败");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleViewTrace(taskId: number) {
    setBusyTaskId(taskId);
    setMessage("");
    try {
      const trace = await getPublishTaskTrace(taskId);
      if (!trace.lead_id) {
        setMessage(`任务 #${taskId} 暂无关联线索，请先回填发布结果`);
        return;
      }

      const customerPart = trace.customer_id ? `&customerId=${trace.customer_id}` : "";
      navigate(`/leads?focusLeadId=${trace.lead_id}&taskId=${taskId}${customerPart}`);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "查询链路失败");
    } finally {
      setBusyTaskId(null);
    }
  }

  function openSubmitPanel(task: PublishTask) {
    setSubmitForm({
      taskId: task.id,
      post_url: task.post_url || "",
      views: String(task.views ?? 0),
      likes: String(task.likes ?? 0),
      comments: String(task.comments ?? 0),
      favorites: String(task.favorites ?? 0),
      shares: String(task.shares ?? 0),
      private_messages: String(task.private_messages ?? 0),
      wechat_adds: String(task.wechat_adds ?? 0),
      leads: String(task.leads ?? 0),
      valid_leads: String(task.valid_leads ?? 0),
      conversions: String(task.conversions ?? 0),
      note: "",
    });
  }

  async function onSubmitResult(e: FormEvent) {
    e.preventDefault();
    if (!submitForm.taskId) return;
    setBusyTaskId(submitForm.taskId);
    setMessage("");
    try {
      await submitPublishTask(submitForm.taskId, {
        post_url: submitForm.post_url || undefined,
        views: Number(submitForm.views || 0),
        likes: Number(submitForm.likes || 0),
        comments: Number(submitForm.comments || 0),
        favorites: Number(submitForm.favorites || 0),
        shares: Number(submitForm.shares || 0),
        private_messages: Number(submitForm.private_messages || 0),
        wechat_adds: Number(submitForm.wechat_adds || 0),
        leads: Number(submitForm.leads || 0),
        valid_leads: Number(submitForm.valid_leads || 0),
        conversions: Number(submitForm.conversions || 0),
        note: submitForm.note || undefined,
      });
      setMessage(`任务 #${submitForm.taskId} 已回填并提交`);
      setSubmitForm((current) => ({ ...current, taskId: 0, note: "" }));
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "回填失败");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleExportTasks() {
    setMessage("");
    try {
      const { blob } = await exportPublishTasksCsv({
        status: statusFilter === "all" ? undefined : statusFilter,
        platform: platformFilter === "all" ? undefined : platformFilter,
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "publish_tasks_export.csv";
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("发布任务导出已开始");
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "导出失败");
    }
  }

  // 查看线索面板
  async function handleViewLeads(taskId: number) {
    setLeadPanelTaskId(taskId);
    setLeadPanelLoading(true);
    setLeadPanelData(null);
    try {
      const data = await publishApi.getContentLeadStats(taskId);
      setLeadPanelData(data);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "获取线索数据失败");
    } finally {
      setLeadPanelLoading(false);
    }
  }

  function closeLeadPanel() {
    setLeadPanelTaskId(null);
    setLeadPanelData(null);
  }

  // 计算单个任务的 ROI 数据
  function calculateTaskRoi(task: PublishTask) {
    const views = task.views || 0;
    const leads = task.leads || 0;
    const conversions = task.conversions || 0;
    return {
      views,
      leads,
      conversions,
      lead_rate: views > 0 ? leads / views : 0,
      conversion_rate: leads > 0 ? conversions / leads : 0,
    };
  }

  return (
    <div className="page grid">
      <h2>发布任务中心</h2>

      <section className="card">
        <h3>任务概览</h3>
        <div className="grid cards">
          <div className="card">
            <h3>总任务</h3>
            <div className="big-number">{stats.total}</div>
          </div>
          <div className="card">
            <h3>待发布</h3>
            <div className="big-number">{stats.pending}</div>
          </div>
          <div className="card">
            <h3>已提交</h3>
            <div className="big-number">{stats.submitted}</div>
          </div>
          <div className="card">
            <h3>已关闭</h3>
            <div className="big-number">{stats.closed}</div>
          </div>
        </div>
      </section>

      {/* 效果分析区域 */}
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3>效果分析</h3>
          <div>
            <label style={{ marginRight: 8 }}>统计周期:</label>
            <select value={statsDays} onChange={(e) => setStatsDays(Number(e.target.value))}>
              <option value={7}>近7天</option>
              <option value={30}>近30天</option>
              <option value={90}>近90天</option>
            </select>
          </div>
        </div>

        {statsLoading ? (
          <div className="muted">加载统计数据...</div>
        ) : (
          <>
            {/* 平台效果对比 */}
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ marginBottom: 12, fontSize: 16 }}>平台效果对比</h4>
              {platformStats.length === 0 ? (
                <div className="muted">暂无平台统计数据</div>
              ) : (
                <table className="table" style={{ fontSize: 14 }}>
                  <thead>
                    <tr>
                      <th>平台</th>
                      <th>总任务</th>
                      <th>已完成</th>
                      <th>总浏览</th>
                      <th>总点赞</th>
                      <th>加微</th>
                      <th>线索</th>
                      <th>转化</th>
                      <th>均浏览</th>
                      <th>转化率%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {platformStats.map((stat) => (
                      <tr key={stat.platform}>
                        <td>{stat.platform}</td>
                        <td>{stat.total_tasks}</td>
                        <td>{stat.completed_tasks}</td>
                        <td>{stat.total_views.toLocaleString()}</td>
                        <td>{stat.total_likes.toLocaleString()}</td>
                        <td>{stat.total_wechat_adds}</td>
                        <td>{stat.total_leads}</td>
                        <td>{stat.total_conversions}</td>
                        <td>{stat.avg_views_per_task.toLocaleString()}</td>
                        <td>{stat.conversion_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* ROI 趋势 */}
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ marginBottom: 12, fontSize: 16 }}>ROI 趋势（发布-转化）</h4>
              {roiTrend.length === 0 ? (
                <div className="muted">暂无趋势数据</div>
              ) : (
                <table className="table" style={{ fontSize: 14 }}>
                  <thead>
                    <tr>
                      <th>日期</th>
                      <th>发布数</th>
                      <th>线索</th>
                      <th>有效线索</th>
                      <th>转化</th>
                      <th>线索率</th>
                      <th>转化率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roiTrend.slice(-7).map((item) => (
                      <tr key={item.date}>
                        <td>{item.date}</td>
                        <td>{item.publish_count}</td>
                        <td>{item.total_leads}</td>
                        <td>{item.total_valid_leads}</td>
                        <td>{item.total_conversions}</td>
                        <td>{(item.lead_rate * 100).toFixed(1)}%</td>
                        <td>{(item.conversion_rate * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* 内容类型效果分析 */}
            <div>
              <h4 style={{ marginBottom: 12, fontSize: 16 }}>内容效果分析</h4>
              {contentAnalysis.length === 0 ? (
                <div className="muted">暂无内容分析数据</div>
              ) : (
                <>
                  <table className="table" style={{ fontSize: 14, marginBottom: 16 }}>
                    <thead>
                      <tr>
                        <th>平台</th>
                        <th>任务数</th>
                        <th>均浏览</th>
                        <th>均点赞</th>
                        <th>均加微</th>
                        <th>均转化</th>
                      </tr>
                    </thead>
                    <tbody>
                      {contentAnalysis.map((item) => (
                        <tr key={item.platform}>
                          <td>{item.platform}</td>
                          <td>{item.task_count}</td>
                          <td>{item.avg_views.toFixed(0)}</td>
                          <td>{item.avg_likes.toFixed(1)}</td>
                          <td>{item.avg_wechat_adds.toFixed(1)}</td>
                          <td>{item.avg_conversions.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* 最佳内容标注 */}
                  {contentAnalysis.some((item) => item.best_task_title) && (
                    <div className="card" style={{ background: "#f0f9ff", borderLeft: "4px solid #3b82f6" }}>
                      <h4 style={{ marginBottom: 8, fontSize: 14, color: "#1e40af" }}>最佳转化内容</h4>
                      {contentAnalysis
                        .filter((item) => item.best_task_title && item.best_task_conversions > 0)
                        .sort((a, b) => b.best_task_conversions - a.best_task_conversions)
                        .slice(0, 3)
                        .map((item) => (
                          <div key={item.platform} style={{ marginBottom: 8, fontSize: 13 }}>
                            <span style={{ fontWeight: 600 }}>[{item.platform}]</span>{" "}
                            <span>{item.best_task_title}</span>{" "}
                            <span style={{ color: "#059669", fontWeight: 600 }}>
                              {item.best_task_conversions} 转化
                            </span>
                          </div>
                        ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </section>

      <section className="card">
        <h3>创建发布任务</h3>
        <form onSubmit={onCreateTask} className="grid">
          <div className="form-row">
            <div>
              <label>平台</label>
              <select
                value={taskForm.platform}
                onChange={(e) => {
                  const newPlatform = e.target.value;
                  setTaskForm((current) => ({ ...current, platform: newPlatform }));
                  // 切换平台时重新加载社交账号
                  loadSocialAccounts(newPlatform);
                  setUseCustomAccount(false);
                }}
              >
                <option value="xiaohongshu">小红书</option>
                <option value="douyin">抖音</option>
                <option value="zhihu">知乎</option>
              </select>
            </div>
            <div>
              <label>账号名称</label>
              {socialAccounts.length > 0 && !useCustomAccount ? (
                <select
                  value={taskForm.account_name}
                  onChange={(e) => {
                    if (e.target.value === "__custom__") {
                      setUseCustomAccount(true);
                      setTaskForm((current) => ({ ...current, account_name: "" }));
                    } else {
                      setTaskForm((current) => ({ ...current, account_name: e.target.value }));
                    }
                  }}
                  required
                >
                  <option value="">请选择账号</option>
                  {socialAccounts.map((account) => (
                    <option key={account.id} value={account.account_name}>
                      {account.account_name}
                    </option>
                  ))}
                  <option value="__custom__">+ 手动输入...</option>
                </select>
              ) : (
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    value={taskForm.account_name}
                    onChange={(e) => setTaskForm((current) => ({ ...current, account_name: e.target.value }))}
                    placeholder="输入账号名称"
                    required
                    style={{ flex: 1 }}
                  />
                  {socialAccounts.length > 0 && (
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => {
                        setUseCustomAccount(false);
                        setTaskForm((current) => ({ ...current, account_name: "" }));
                      }}
                    >
                      选择已有账号
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="form-row">
            <div>
              <label>任务标题</label>
              <input
                value={taskForm.task_title}
                onChange={(e) => setTaskForm((current) => ({ ...current, task_title: e.target.value }))}
                required
              />
            </div>
            <div>
              <label>改写内容ID（可选）</label>
              <input
                type="number"
                value={taskForm.rewritten_content_id}
                onChange={(e) =>
                  setTaskForm((current) => ({ ...current, rewritten_content_id: e.target.value }))
                }
                min={1}
              />
            </div>
          </div>

          <div>
            <label>发布内容</label>
            <textarea
              value={taskForm.content_text}
              onChange={(e) => setTaskForm((current) => ({ ...current, content_text: e.target.value }))}
              required
            />
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button className="primary" type="submit" disabled={creating}>
              {creating ? "创建中..." : "创建任务"}
            </button>
            {message && <span className="muted">{message}</span>}
          </div>
        </form>
      </section>

      <section className="card">
        <h3>任务队列</h3>
        <div style={{ marginBottom: 10 }}>
          <button className="ghost" type="button" onClick={handleExportTasks}>导出任务CSV</button>
        </div>
        <div className="form-row" style={{ marginBottom: 12 }}>
          <div>
            <label>平台筛选</label>
            <select value={platformFilter} onChange={(e) => setPlatformFilter(e.target.value)}>
              <option value="all">全部</option>
              <option value="xiaohongshu">小红书</option>
              <option value="douyin">抖音</option>
              <option value="zhihu">知乎</option>
            </select>
          </div>
          <div>
            <label>状态筛选</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">全部</option>
              <option value="pending">待发布</option>
              <option value="claimed">已领取</option>
              <option value="submitted">已提交</option>
              <option value="rejected">已驳回</option>
              <option value="closed">已关闭</option>
            </select>
          </div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>账号</th>
              <th>标题</th>
              <th>状态</th>
              <th>执行人</th>
              <th>加微</th>
              <th>线索</th>
              <th>转化</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10}>加载中...</td>
              </tr>
            ) : (
              tasks.map((task) => {
                const busy = busyTaskId === task.id;
                const canAssign = currentUserId === task.owner_id;
                return (
                  <tr key={task.id}>
                    <td>{task.id}</td>
                    <td>{task.platform}</td>
                    <td>{task.account_name}</td>
                    <td>{task.task_title}</td>
                    <td>{task.status}</td>
                    <td>{getUserLabel(task.assigned_to)}</td>
                    <td>{task.wechat_adds}</td>
                    <td>{task.leads}</td>
                    <td>{task.conversions}</td>
                    <td>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {canAssign && (
                          <button
                            className="ghost"
                            type="button"
                            disabled={busy || ["submitted", "closed"].includes(task.status)}
                            onClick={() => openAssignPanel(task)}
                          >
                            {task.assigned_to ? "改派" : "分配"}
                          </button>
                        )}
                        <button
                          className="ghost"
                          type="button"
                          disabled={busy || !["pending", "rejected"].includes(task.status)}
                          onClick={() => handleClaim(task.id)}
                        >
                          领取
                        </button>
                        <button
                          className="secondary"
                          type="button"
                          disabled={busy || ["closed", "rejected"].includes(task.status)}
                          onClick={() => openSubmitPanel(task)}
                        >
                          回填
                        </button>
                        <button
                          className="ghost"
                          type="button"
                          disabled={busy || task.status === "closed"}
                          onClick={() => handleReject(task.id)}
                        >
                          驳回
                        </button>
                        <button
                          className="ghost"
                          type="button"
                          disabled={busy || task.status === "closed"}
                          onClick={() => handleClose(task.id)}
                        >
                          关闭
                        </button>
                        <button
                          className="ghost"
                          type="button"
                          disabled={busy}
                          onClick={() => handleViewTrace(task.id)}
                        >
                          查看链路
                        </button>
                        {task.status === "submitted" && (task.leads || 0) > 0 && (
                          <button
                            className="ghost"
                            type="button"
                            disabled={busy}
                            onClick={() => handleViewLeads(task.id)}
                          >
                            查看线索
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </section>

      {assignTaskId > 0 && (
        <section className="card">
          <h3>分配/改派执行人（任务 #{assignTaskId}）</h3>
          <form onSubmit={onAssignTask} className="grid">
            <div className="form-row">
              <div>
                <label>执行人</label>
                <select
                  value={assignForm.assigned_to}
                  onChange={(e) => setAssignForm((current) => ({ ...current, assigned_to: e.target.value }))}
                  required
                >
                  <option value="">请选择执行人</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.username} (#{user.id} / {user.role})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label>备注</label>
                <input
                  value={assignForm.note}
                  onChange={(e) => setAssignForm((current) => ({ ...current, note: e.target.value }))}
                  placeholder="可选：说明分配原因或交接备注"
                />
              </div>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="primary" type="submit" disabled={busyTaskId === assignTaskId}>
                保存分配
              </button>
              <button
                className="ghost"
                type="button"
                onClick={() => {
                  setAssignTaskId(0);
                  setAssignForm({ assigned_to: "", note: "" });
                }}
              >
                取消
              </button>
            </div>
          </form>
        </section>
      )}

      {submitForm.taskId > 0 && (
        <section className="card">
          <h3>回填发布结果（任务 #{submitForm.taskId}）</h3>
          <form onSubmit={onSubmitResult} className="grid">
            <div>
              <label>帖子链接</label>
              <input
                value={submitForm.post_url}
                onChange={(e) => setSubmitForm((current) => ({ ...current, post_url: e.target.value }))}
              />
            </div>
            <div className="form-row">
              <div>
                <label>浏览</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.views}
                  onChange={(e) => setSubmitForm((current) => ({ ...current, views: e.target.value }))}
                />
              </div>
              <div>
                <label>点赞</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.likes}
                  onChange={(e) => setSubmitForm((current) => ({ ...current, likes: e.target.value }))}
                />
              </div>
              <div>
                <label>评论</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.comments}
                  onChange={(e) => setSubmitForm((current) => ({ ...current, comments: e.target.value }))}
                />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label>收藏</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.favorites}
                  onChange={(e) => setSubmitForm((current) => ({ ...current, favorites: e.target.value }))}
                />
              </div>
              <div>
                <label>转发</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.shares}
                  onChange={(e) => setSubmitForm((current) => ({ ...current, shares: e.target.value }))}
                />
              </div>
              <div>
                <label>私信</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.private_messages}
                  onChange={(e) =>
                    setSubmitForm((current) => ({ ...current, private_messages: e.target.value }))
                  }
                />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label>加微</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.wechat_adds}
                  onChange={(e) =>
                    setSubmitForm((current) => ({ ...current, wechat_adds: e.target.value }))
                  }
                />
              </div>
              <div>
                <label>线索</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.leads}
                  onChange={(e) => setSubmitForm((current) => ({ ...current, leads: e.target.value }))}
                />
              </div>
              <div>
                <label>有效线索</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.valid_leads}
                  onChange={(e) =>
                    setSubmitForm((current) => ({ ...current, valid_leads: e.target.value }))
                  }
                />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label>转化</label>
                <input
                  type="number"
                  min={0}
                  value={submitForm.conversions}
                  onChange={(e) =>
                    setSubmitForm((current) => ({ ...current, conversions: e.target.value }))
                  }
                />
              </div>
            </div>
            <div>
              <label>备注</label>
              <input
                value={submitForm.note}
                onChange={(e) => setSubmitForm((current) => ({ ...current, note: e.target.value }))}
              />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="primary" type="submit" disabled={busyTaskId === submitForm.taskId}>
                提交回填
              </button>
              <button
                className="ghost"
                type="button"
                onClick={() => setSubmitForm((current) => ({ ...current, taskId: 0 }))}
              >
                取消
              </button>
            </div>
          </form>
        </section>
      )}

      {/* 线索追踪面板 */}
      {leadPanelTaskId !== null && (
        <section className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>线索追踪（任务 #{leadPanelTaskId}）</h3>
            <button className="ghost" type="button" onClick={closeLeadPanel}>
              关闭
            </button>
          </div>
          {leadPanelLoading ? (
            <div className="muted">加载线索数据...</div>
          ) : leadPanelData ? (
            <>
              {/* ROI 漏斗 */}
              <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24, padding: 16, background: "#f8fafc", borderRadius: 8 }}>
                <div style={{ textAlign: "center", flex: 1 }}>
                  <div style={{ fontSize: 24, fontWeight: 600, color: "#3b82f6" }}>{leadPanelData.total_lead_count}</div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>线索数</div>
                </div>
                <div style={{ fontSize: 20, color: "#94a3b8" }}>→</div>
                <div style={{ textAlign: "center", flex: 1 }}>
                  <div style={{ fontSize: 24, fontWeight: 600, color: "#10b981" }}>{leadPanelData.total_valid_leads}</div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>有效线索</div>
                </div>
                <div style={{ fontSize: 20, color: "#94a3b8" }}>→</div>
                <div style={{ textAlign: "center", flex: 1 }}>
                  <div style={{ fontSize: 24, fontWeight: 600, color: "#f59e0b" }}>{leadPanelData.total_conversions}</div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>转化数</div>
                </div>
              </div>

              {/* 转化率 */}
              <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
                <div className="card" style={{ flex: 1, background: "#eff6ff" }}>
                  <div style={{ fontSize: 14, color: "#1e40af" }}>线索转化率</div>
                  <div style={{ fontSize: 20, fontWeight: 600 }}>{(leadPanelData.conversion_rate * 100).toFixed(1)}%</div>
                </div>
                <div className="card" style={{ flex: 1, background: "#ecfdf5" }}>
                  <div style={{ fontSize: 14, color: "#047857" }}>加微数</div>
                  <div style={{ fontSize: 20, fontWeight: 600 }}>{leadPanelData.total_wechat_adds}</div>
                </div>
              </div>

              {/* 分级占比 */}
              {Object.keys(leadPanelData.status_distribution).length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <h4 style={{ marginBottom: 8, fontSize: 14 }}>线索状态分布</h4>
                  <div style={{ display: "flex", gap: 8 }}>
                    {Object.entries(leadPanelData.status_distribution).map(([status, count]) => (
                      <div key={status} style={{ padding: "4px 12px", background: "#f1f5f9", borderRadius: 4, fontSize: 13 }}>
                        {status}: {count}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 线索列表 */}
              <div>
                <h4 style={{ marginBottom: 12, fontSize: 14 }}>线索列表</h4>
                {leadPanelData.leads.length === 0 ? (
                  <div className="muted">暂无线索数据</div>
                ) : (
                  <table className="table" style={{ fontSize: 13 }}>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>标题</th>
                        <th>状态</th>
                        <th>加微</th>
                        <th>线索</th>
                        <th>有效</th>
                        <th>转化</th>
                        <th>时间</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leadPanelData.leads.map((lead) => (
                        <tr key={lead.id}>
                          <td>{lead.id}</td>
                          <td>{lead.title}</td>
                          <td>{lead.status}</td>
                          <td>{lead.wechat_adds}</td>
                          <td>{lead.leads}</td>
                          <td>{lead.valid_leads}</td>
                          <td>{lead.conversions}</td>
                          <td>{lead.created_at ? new Date(lead.created_at).toLocaleDateString() : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          ) : (
            <div className="muted">无法获取线索数据</div>
          )}
        </section>
      )}

      {/* 账号效果对比面板 */}
      <section className="card">
        <h3>账号效果对比</h3>
        <table className="table" style={{ fontSize: 14 }}>
          <thead>
            <tr>
              <th>账号</th>
              <th>平台</th>
              <th>发布数</th>
              <th>总浏览</th>
              <th>总点赞</th>
              <th>线索数</th>
              <th>转化数</th>
              <th>线索转化率</th>
            </tr>
          </thead>
          <tbody>
            {/* 从 tasks 数据聚合账号统计 */}
            {(() => {
              const accountMap = new Map<string, { name: string; platform: string; tasks: PublishTask[] }>();
              tasks.forEach((task) => {
                const key = `${task.platform}_${task.account_name}`;
                if (!accountMap.has(key)) {
                  accountMap.set(key, { name: task.account_name, platform: task.platform, tasks: [] });
                }
                accountMap.get(key)!.tasks.push(task);
              });
              const accountStats = Array.from(accountMap.values()).map((acc) => ({
                account_name: acc.name,
                platform: acc.platform,
                total_tasks: acc.tasks.length,
                total_views: acc.tasks.reduce((sum, t) => sum + (t.views || 0), 0),
                total_likes: acc.tasks.reduce((sum, t) => sum + (t.likes || 0), 0),
                total_leads: acc.tasks.reduce((sum, t) => sum + (t.leads || 0), 0),
                total_conversions: acc.tasks.reduce((sum, t) => sum + (t.conversions || 0), 0),
                lead_conversion_rate: acc.tasks.reduce((sum, t) => sum + (t.leads || 0), 0) > 0
                  ? acc.tasks.reduce((sum, t) => sum + (t.conversions || 0), 0) /
                    acc.tasks.reduce((sum, t) => sum + (t.leads || 0), 0)
                  : 0,
              }));
              return accountStats.length === 0 ? (
                <tr>
                  <td colSpan={8} className="muted">暂无账号数据</td>
                </tr>
              ) : (
                accountStats.sort((a, b) => b.total_conversions - a.total_conversions).map((stat, idx) => (
                  <tr key={idx}>
                    <td>{stat.account_name}</td>
                    <td>{stat.platform}</td>
                    <td>{stat.total_tasks}</td>
                    <td>{stat.total_views.toLocaleString()}</td>
                    <td>{stat.total_likes.toLocaleString()}</td>
                    <td>{stat.total_leads}</td>
                    <td>{stat.total_conversions}</td>
                    <td>{(stat.lead_conversion_rate * 100).toFixed(1)}%</td>
                  </tr>
                ))
              );
            })()}
          </tbody>
        </table>
      </section>
    </div>
  );
}
