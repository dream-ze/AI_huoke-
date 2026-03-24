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
  rejectPublishTask,
  submitPublishTask,
} from "../lib/api";
import { PublishTask, PublishTaskStats, UserSummary } from "../types";

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

  const [message, setMessage] = useState("");

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

  useEffect(() => {
    async function run() {
      try {
        const [me, activeUsers] = await Promise.all([
          getCurrentUser(),
          listActiveUsers().catch(() => []),
        ]);
        setCurrentUserId(me.id);
        setUsers(activeUsers || []);
        await refreshData();
      } finally {
        setLoading(false);
      }
    }
    run();
  }, [platformFilter, statusFilter]);

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

      <section className="card">
        <h3>创建发布任务</h3>
        <form onSubmit={onCreateTask} className="grid">
          <div className="form-row">
            <div>
              <label>平台</label>
              <select
                value={taskForm.platform}
                onChange={(e) => setTaskForm((current) => ({ ...current, platform: e.target.value }))}
              >
                <option value="xiaohongshu">小红书</option>
                <option value="douyin">抖音</option>
                <option value="zhihu">知乎</option>
              </select>
            </div>
            <div>
              <label>账号名称</label>
              <input
                value={taskForm.account_name}
                onChange={(e) => setTaskForm((current) => ({ ...current, account_name: e.target.value }))}
                required
              />
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
    </div>
  );
}
