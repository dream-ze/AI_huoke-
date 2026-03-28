import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getDashboardSummary,
  getPublishTaskStats,
  listPublishTasks,
  listLeads,
  listCustomers,
  getPublishTaskTrace,
} from "../lib/api";
import { DashboardSummary, PublishTaskStats, PublishTask, LeadItem, Customer } from "../types";

const emptyStats: PublishTaskStats = {
  total: 0,
  pending: 0,
  claimed: 0,
  submitted: 0,
  rejected: 0,
  closed: 0,
};

const emptySummary: DashboardSummary = {
  today_new_customers: 0,
  today_wechat_adds: 0,
  today_leads: 0,
  today_valid_leads: 0,
  today_conversions: 0,
  pending_follow_count: 0,
  pending_review_count: 0,
};

type TraceResult = {
  task_id: number;
  publish_record_id?: number;
  lead_id?: number;
  customer_id?: number;
};

export function WorkflowPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [taskStats, setTaskStats] = useState<PublishTaskStats>(emptyStats);
  const [recentTasks, setRecentTasks] = useState<PublishTask[]>([]);
  const [recentLeads, setRecentLeads] = useState<LeadItem[]>([]);
  const [recentCustomers, setRecentCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [traceLoading, setTraceLoading] = useState<number | null>(null);
  const [traceResult, setTraceResult] = useState<TraceResult | null>(null);

  useEffect(() => {
    async function run() {
      try {
        const [s, ts, tasks, leads, customers] = await Promise.all([
          getDashboardSummary().catch(() => emptySummary),
          getPublishTaskStats().catch(() => emptyStats),
          listPublishTasks({ limit: 5 }).catch(() => []),
          listLeads({ limit: 5 }).catch(() => []),
          listCustomers().catch(() => []),
        ]);
        setSummary(s || emptySummary);
        setTaskStats(ts || emptyStats);
        setRecentTasks(tasks || []);
        setRecentLeads(leads || []);
        setRecentCustomers((customers || []).slice(0, 5));
      } finally {
        setLoading(false);
      }
    }
    run();
  }, []);

  async function handleTrace(taskId: number) {
    setTraceLoading(taskId);
    setTraceResult(null);
    try {
      const result = await getPublishTaskTrace(taskId);
      setTraceResult(result);
    } catch {
      setTraceResult({ task_id: taskId });
    } finally {
      setTraceLoading(null);
    }
  }

  return (
    <div className="page grid" style={{ gap: 20 }}>
      {/* 页面标题 */}
      <section>
        <h2 style={{ marginBottom: 8 }}>🔄 业务闭环操作台</h2>
        <p className="muted" style={{ margin: 0 }}>
          从发布任务到线索转化，完整业务链路一目了然
        </p>
      </section>

      {/* 核心流程可视化 */}
      <section className="card">
        <h3 style={{ marginBottom: 16 }}>📈 业务流程概览</h3>
        <div className="workflow-pipeline">
          <div
            className="workflow-step"
            onClick={() => navigate("/collect-center")}
          >
            <div className="step-icon">🎯</div>
            <div className="step-label">采集内容</div>
            <div className="step-count">{summary.pending_review_count}</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div
            className="workflow-step"
            onClick={() => navigate("/ai-hub")}
          >
            <div className="step-icon">🤖</div>
            <div className="step-label">AI 改写</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div
            className="workflow-step active"
            onClick={() => navigate("/publish")}
          >
            <div className="step-icon">📤</div>
            <div className="step-label">发布任务</div>
            <div className="step-count">{taskStats.total}</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div
            className="workflow-step"
            onClick={() => navigate("/leads")}
          >
            <div className="step-icon">💎</div>
            <div className="step-label">线索池</div>
            <div className="step-count">{summary.today_leads}</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div
            className="workflow-step"
            onClick={() => navigate("/customers")}
          >
            <div className="step-icon">👥</div>
            <div className="step-label">客户管理</div>
            <div className="step-count">{summary.today_new_customers}</div>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="card">加载中...</div>
      ) : (
        <>
          {/* 转化漏斗 */}
          <section className="grid cards-4">
            <div className="card">
              <h3>待发布任务</h3>
              <div className="big-number">{taskStats.pending}</div>
              <div className="muted" style={{ marginTop: 8 }}>
                已领取: {taskStats.claimed}
              </div>
            </div>
            <div className="card">
              <h3>已提交任务</h3>
              <div className="big-number">{taskStats.submitted}</div>
              <div className="muted" style={{ marginTop: 8 }}>
                已关闭: {taskStats.closed}
              </div>
            </div>
            <div className="card">
              <h3>今日线索</h3>
              <div className="big-number">{summary.today_leads}</div>
              <div className="muted" style={{ marginTop: 8 }}>
                有效线索: {summary.today_valid_leads}
              </div>
            </div>
            <div className="card">
              <h3>今日转化</h3>
              <div className="big-number">{summary.today_conversions}</div>
              <div className="muted" style={{ marginTop: 8 }}>
                新客户: {summary.today_new_customers}
              </div>
            </div>
          </section>

          {/* 链路追踪 */}
          {traceResult && (
            <section className="card">
              <h3 style={{ marginBottom: 16 }}>🔍 链路追踪结果</h3>
              <div className="trace-timeline">
                <div className="trace-item">
                  <div className="trace-icon">📤</div>
                  <div className="trace-content">
                    <div className="trace-title">发布任务 #{traceResult.task_id}</div>
                    <div className="trace-meta">
                      <button
                        className="ghost"
                        style={{ padding: "4px 8px", fontSize: 12 }}
                        onClick={() => navigate(`/publish?taskId=${traceResult.task_id}`)}
                      >
                        查看详情
                      </button>
                    </div>
                  </div>
                </div>
                {traceResult.lead_id && (
                  <div className="trace-item">
                    <div className="trace-icon" style={{ background: "var(--brand-2)" }}>💎</div>
                    <div className="trace-content">
                      <div className="trace-title">关联线索 #{traceResult.lead_id}</div>
                      <div className="trace-meta">
                        <button
                          className="ghost"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          onClick={() => navigate(`/leads?focusLeadId=${traceResult.lead_id}`)}
                        >
                          查看线索
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                {traceResult.customer_id && (
                  <div className="trace-item">
                    <div className="trace-icon" style={{ background: "var(--ok)" }}>👥</div>
                    <div className="trace-content">
                      <div className="trace-title">转化客户 #{traceResult.customer_id}</div>
                      <div className="trace-meta">
                        <button
                          className="ghost"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          onClick={() => navigate(`/customers?focusCustomerId=${traceResult.customer_id}`)}
                        >
                          查看客户
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                {!traceResult.lead_id && !traceResult.customer_id && (
                  <div className="trace-item">
                    <div className="trace-icon" style={{ background: "var(--muted)" }}>⏳</div>
                    <div className="trace-content">
                      <div className="trace-title">暂无后续记录</div>
                      <div className="trace-meta">任务尚未产生线索或客户转化</div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* 最近发布任务 */}
          <section className="card">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <h3>📤 最近发布任务</h3>
              <button className="ghost" onClick={() => navigate("/publish")}>
                查看全部
              </button>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>平台</th>
                  <th>标题</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {recentTasks.length === 0 ? (
                  <tr><td colSpan={5} className="muted">暂无发布任务</td></tr>
                ) : recentTasks.map((task) => (
                  <tr key={task.id}>
                    <td>{task.id}</td>
                    <td>{task.platform}</td>
                    <td>{task.task_title}</td>
                    <td>{task.status}</td>
                    <td>
                      <button
                        className="ghost"
                        disabled={traceLoading === task.id}
                        onClick={() => handleTrace(task.id)}
                      >
                        {traceLoading === task.id ? "追踪中..." : "追踪链路"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* 最近线索 */}
          <section className="card">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <h3>💎 最近线索</h3>
              <button className="ghost" onClick={() => navigate("/leads")}>
                查看全部
              </button>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>来源任务</th>
                  <th>平台</th>
                  <th>标题</th>
                  <th>状态</th>
                  <th>客户ID</th>
                </tr>
              </thead>
              <tbody>
                {recentLeads.length === 0 ? (
                  <tr><td colSpan={6} className="muted">暂无线索</td></tr>
                ) : recentLeads.map((lead) => (
                  <tr key={lead.id}>
                    <td>{lead.id}</td>
                    <td>{lead.publish_task_id || "-"}</td>
                    <td>{lead.platform}</td>
                    <td>{lead.title}</td>
                    <td>{lead.status}</td>
                    <td>
                      {lead.customer_id ? (
                        <button
                          className="ghost"
                          style={{ padding: "4px 8px", fontSize: 12 }}
                          onClick={() => navigate(`/customers?focusCustomerId=${lead.customer_id}`)}
                        >
                          #{lead.customer_id}
                        </button>
                      ) : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* 最近客户 */}
          <section className="card">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <h3>👥 最近客户</h3>
              <button className="ghost" onClick={() => navigate("/customers")}>
                查看全部
              </button>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>昵称</th>
                  <th>来源平台</th>
                  <th>意向等级</th>
                  <th>状态</th>
                  <th>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {recentCustomers.length === 0 ? (
                  <tr><td colSpan={6} className="muted">暂无客户</td></tr>
                ) : recentCustomers.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td>{c.nickname}</td>
                    <td>{c.source_platform}</td>
                    <td>{c.intention_level}</td>
                    <td>{c.customer_status}</td>
                    <td>{c.created_at ? new Date(c.created_at).toLocaleDateString() : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}

      {/* 快捷操作 */}
      <section className="card">
        <h3 style={{ marginBottom: 12 }}>⚡ 快捷操作</h3>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button className="primary" onClick={() => navigate("/publish")}>
            创建发布任务
          </button>
          <button className="secondary" onClick={() => navigate("/leads")}>
            管理线索
          </button>
          <button className="ghost" onClick={() => navigate("/customers")}>
            查看客户
          </button>
        </div>
      </section>
    </div>
  );
}
