import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDashboardSummary, getTrend, getPublishTaskStats } from "../../lib/api";
import { DashboardSummary, TrendItem, PublishTaskStats } from "../../types";

const emptySummary: DashboardSummary = {
  today_new_customers: 0,
  today_wechat_adds: 0,
  today_leads: 0,
  today_valid_leads: 0,
  today_conversions: 0,
  pending_follow_count: 0,
  pending_review_count: 0,
};

const emptyStats: PublishTaskStats = {
  total: 0,
  pending: 0,
  claimed: 0,
  submitted: 0,
  rejected: 0,
  closed: 0,
};

const upgradeFeatures = [
  { icon: "🗄️", title: "PostgreSQL 回归", desc: "生产级数据库，数据更安全" },
  { icon: "🔒", title: "权限收紧", desc: "跨用户数据隔离保护" },
  { icon: "🏥", title: "运维健康检查", desc: "系统状态一目了然" },
  { icon: "🧪", title: "自动化测试", desc: "桌面端回归测试覆盖" },
];

const quickEntries = [
  { icon: "🎯", label: "采集中心", desc: "采集爆款内容", to: "/collect-center" },
  { icon: "🤖", label: "AI 中枢", desc: "素材清洗与生成", to: "/ai-hub" },
  { icon: "📤", label: "发布任务", desc: "创建发布计划", to: "/publish" },
  { icon: "🔄", label: "业务闭环", desc: "发布→线索→客户", to: "/workflow" },
  { icon: "💎", label: "线索池", desc: "跟进转化线索", to: "/leads" },
  { icon: "👥", label: "客户管理", desc: "管理客户资料", to: "/customers" },
  { icon: "⚙️", label: "运维看板", desc: "查看系统状态", to: "/ops" },
  { icon: "📊", label: "爆款洞察", desc: "分析热门内容", to: "/insight" },
];

export function DashboardPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [taskStats, setTaskStats] = useState<PublishTaskStats>(emptyStats);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function run() {
      try {
        const [s, t, ts] = await Promise.all([
          getDashboardSummary(),
          getTrend(7),
          getPublishTaskStats().catch(() => emptyStats),
        ]);
        setSummary(s);
        setTrend(t?.data || []);
        setTaskStats(ts || emptyStats);
      } catch (err: any) {
        setError(err?.response?.data?.detail || "看板数据加载失败，请稍后重试");
      } finally {
        setLoading(false);
      }
    }

    run();
  }, []);

  return (
    <div className="page grid" style={{ gap: 20 }}>
      {/* 升级横幅 */}
      <section className="upgrade-banner">
        <h2>🚀 系统能力升级上线</h2>
        <p>本次发布包含后端主链路优化、数据库回归、权限收紧等重要更新</p>
        <div className="upgrade-features">
          {upgradeFeatures.map((f) => (
            <div key={f.title} className="upgrade-feature">
              <div className="icon">{f.icon}</div>
              <h4>{f.title}</h4>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 工作流线路图 */}
      <section className="card">
        <h3 style={{ marginBottom: 16 }}>📈 业务闭环概览</h3>
        <div className="workflow-pipeline">
          <div
            className="workflow-step"
            onClick={() => navigate("/collect-center")}
          >
            <div className="step-icon">🎯</div>
            <div className="step-label">采集</div>
            <div className="step-count">{summary.pending_review_count}</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div
            className="workflow-step"
            onClick={() => navigate("/ai-hub")}
          >
            <div className="step-icon">🤖</div>
            <div className="step-label">AI处理</div>
            <div className="step-count">-</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div
            className="workflow-step"
            onClick={() => navigate("/publish")}
          >
            <div className="step-icon">📤</div>
            <div className="step-label">发布</div>
            <div className="step-count">{taskStats.pending}</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div
            className="workflow-step"
            onClick={() => navigate("/leads")}
          >
            <div className="step-icon">💎</div>
            <div className="step-label">线索</div>
            <div className="step-count">{summary.today_leads}</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div
            className="workflow-step"
            onClick={() => navigate("/customers")}
          >
            <div className="step-icon">👥</div>
            <div className="step-label">客户</div>
            <div className="step-count">{summary.today_new_customers}</div>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="card">加载中...</div>
      ) : (
        <>
          {error && (
            <section className="card">
              <div className="error">{error}</div>
            </section>
          )}

          {/* 核心指标 */}
          <section className="grid cards-4">
            <div className="card">
              <h3>今日新增客户</h3>
              <div className="big-number">{summary.today_new_customers}</div>
            </div>
            <div className="card">
              <h3>今日加微数</h3>
              <div className="big-number">{summary.today_wechat_adds}</div>
            </div>
            <div className="card">
              <h3>今日线索数</h3>
              <div className="big-number">{summary.today_leads}</div>
            </div>
            <div className="card">
              <h3>今日有效线索</h3>
              <div className="big-number">{summary.today_valid_leads}</div>
            </div>
          </section>

          {/* 快捷入口 */}
          <section className="card">
            <h3 style={{ marginBottom: 16 }}>⚡ 快捷入口</h3>
            <div className="quick-entry-grid">
              {quickEntries.map((entry) => (
                <Link key={entry.to} to={entry.to} className="quick-entry">
                  <div className="icon">{entry.icon}</div>
                  <div className="label">{entry.label}</div>
                  <div className="desc">{entry.desc}</div>
                </Link>
              ))}
            </div>
          </section>

          {/* 趋势图 */}
          <section className="card">
            <h3 style={{ marginBottom: 12 }}>📊 最近7天线索趋势</h3>
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <LineChart data={trend}>
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="total_leads"
                    stroke="#b63d1f"
                    strokeWidth={3}
                    name="总线索"
                  />
                  <Line
                    type="monotone"
                    dataKey="total_valid_leads"
                    stroke="#0f6d7a"
                    strokeWidth={3}
                    name="有效线索"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
