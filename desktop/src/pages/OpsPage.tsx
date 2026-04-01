import { useEffect, useState } from "react";
import { getSystemHealth, getSystemVersion, getAICallStats } from "../lib/api";
import { AICallStatsResponse } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

type HealthStatus = {
  status: string;
  database: string;
  redis: string;
  timestamp: string;
  version?: string;
};

type VersionInfo = {
  api_version: string;
  latest_desktop_version: string;
};

export function OpsPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const [aiStats, setAiStats] = useState<AICallStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchData() {
    setLoading(true);
    setError("");
    try {
      const [h, v, a] = await Promise.all([
        getSystemHealth().catch(() => null),
        getSystemVersion().catch(() => null),
        getAICallStats(7, "all").catch(() => null),
      ]);
      setHealth(h);
      setVersion(v);
      setAiStats(a);
    } catch (err: any) {
      setError("运维数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
    // 每30秒刷新一次
    const timer = setInterval(fetchData, 30000);
    return () => clearInterval(timer);
  }, []);

  function getStatusColor(status: string) {
    if (status === "ok" || status === "healthy" || status === "connected") return "ok";
    if (status === "degraded" || status === "slow") return "warn";
    return "danger";
  }

  function formatTimestamp(ts?: string) {
    if (!ts) return "-";
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  }

  // 计算 AI 调用统计
  const totalCalls = aiStats?.data?.reduce((sum, d) => sum + d.call_count, 0) || 0;
  const totalFailed = aiStats?.data?.reduce((sum, d) => sum + d.failed_count, 0) || 0;
  const totalTokens = aiStats?.data?.reduce((sum, d) => sum + d.total_tokens, 0) || 0;
  const avgLatency = aiStats?.data?.length
    ? Math.round(aiStats.data.reduce((sum, d) => sum + d.avg_latency_ms, 0) / aiStats.data.length)
    : 0;

  return (
    <div className="page grid" style={{ gap: 20 }}>
      {/* 页面标题 */}
      <section style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ marginBottom: 8 }}>⚙️ 运维看板</h2>
          <p className="muted" style={{ margin: 0 }}>
            系统健康状态实时监控，每 30 秒自动刷新
          </p>
        </div>
        <button className="ghost" onClick={fetchData} disabled={loading}>
          {loading ? "刷新中..." : "立即刷新"}
        </button>
      </section>

      {error && (
        <section className="card">
          <div className="error">{error}</div>
        </section>
      )}

      {/* 系统状态 */}
      <section className="card">
        <h3 style={{ marginBottom: 16 }}>🏥 系统健康状态</h3>
        {loading && !health ? (
          <div className="muted">加载中...</div>
        ) : health ? (
          <div className="ops-grid">
            <div className="ops-metric">
              <div className="metric-label">整体状态</div>
              <div className="metric-value" style={{ color: getStatusColor(health.status) === "ok" ? "var(--ok)" : "var(--danger)" }}>
                {health.status === "healthy" ? "✅ 健康" : health.status}
              </div>
              <div className="metric-status">
                <span className={`status-dot ${getStatusColor(health.status)}`}></span>
                最后检查: {formatTimestamp(health.timestamp)}
              </div>
            </div>

            <div className="ops-metric">
              <div className="metric-label">数据库连接</div>
              <div className="metric-value" style={{ color: getStatusColor(health.database) === "ok" ? "var(--ok)" : "var(--danger)" }}>
                {health.database === "connected" ? "✅ 已连接" : health.database}
              </div>
              <div className="metric-status">
                <span className={`status-dot ${getStatusColor(health.database)}`}></span>
                PostgreSQL
              </div>
            </div>

            <div className="ops-metric">
              <div className="metric-label">缓存服务</div>
              <div className="metric-value" style={{ color: getStatusColor(health.redis) === "ok" ? "var(--ok)" : "var(--warn)" }}>
                {health.redis === "connected" ? "✅ 已连接" : health.redis === "not_configured" ? "⚠️ 未配置" : health.redis}
              </div>
              <div className="metric-status">
                <span className={`status-dot ${getStatusColor(health.redis)}`}></span>
                Redis
              </div>
            </div>

            <div className="ops-metric">
              <div className="metric-label">API 版本</div>
              <div className="metric-value">{version?.api_version || "-"}</div>
              <div className="metric-status">
                <span className="status-dot ok"></span>
                桌面端: {version?.latest_desktop_version || "-"}
              </div>
            </div>
          </div>
        ) : (
          <div className="muted">
            无法获取健康状态，请检查后端服务是否正常运行。
            <br />
            尝试访问: <code>http://后端地址:8000/api/system/ops/health</code>
          </div>
        )}
      </section>

      {/* AI 调用统计 */}
      <section className="card">
        <h3 style={{ marginBottom: 16 }}>🤖 AI 调用统计（近 7 天）</h3>
        <div className="ops-grid">
          <div className="ops-metric">
            <div className="metric-label">总调用次数</div>
            <div className="metric-value">{totalCalls.toLocaleString()}</div>
            <div className="metric-status">
              <span className="status-dot ok"></span>
              累计调用
            </div>
          </div>

          <div className="ops-metric">
            <div className="metric-label">失败次数</div>
            <div className="metric-value" style={{ color: totalFailed > 0 ? "var(--warn)" : "inherit" }}>
              {totalFailed.toLocaleString()}
            </div>
            <div className="metric-status">
              <span className={`status-dot ${totalFailed > 0 ? "warn" : "ok"}`}></span>
              失败率: {totalCalls > 0 ? ((totalFailed / totalCalls) * 100).toFixed(1) : 0}%
            </div>
          </div>

          <div className="ops-metric">
            <div className="metric-label">Token 消耗</div>
            <div className="metric-value">{(totalTokens / 1000).toFixed(1)}K</div>
            <div className="metric-status">
              <span className="status-dot muted"></span>
              输入 + 输出
            </div>
          </div>

          <div className="ops-metric">
            <div className="metric-label">平均延迟</div>
            <div className="metric-value">{avgLatency} ms</div>
            <div className="metric-status">
              <span className={`status-dot ${avgLatency < 2000 ? "ok" : avgLatency < 5000 ? "warn" : "danger"}`}></span>
              响应时间
            </div>
          </div>
        </div>
      </section>

      {/* 每日明细 */}
      {aiStats?.data && aiStats.data.length > 0 && (
        <section className="card">
          <h3 style={{ marginBottom: 16 }}>📊 每日调用明细</h3>
          <table className="table">
            <thead>
              <tr>
                <th>日期</th>
                <th>调用次数</th>
                <th>失败次数</th>
                <th>失败率</th>
                <th>Token 消耗</th>
                <th>平均延迟</th>
              </tr>
            </thead>
            <tbody>
              {aiStats.data.map((row) => (
                <tr key={row.date}>
                  <td>{row.date}</td>
                  <td>{row.call_count}</td>
                  <td style={{ color: row.failed_count > 0 ? "var(--warn)" : "inherit" }}>
                    {row.failed_count}
                  </td>
                  <td>{(row.failure_rate * 100).toFixed(1)}%</td>
                  <td>{row.total_tokens.toLocaleString()}</td>
                  <td>{Math.round(row.avg_latency_ms)} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* 快速链接 */}
      <section className="card">
        <h3 style={{ marginBottom: 12 }}>🔗 运维资源</h3>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <a
            href={`${API_BASE_URL}/api/system/ops/health`}
            target="_blank"
            rel="noopener noreferrer"
            className="ghost"
            style={{
              display: "inline-block",
              padding: "8px 14px",
              border: "1px solid var(--line)",
              borderRadius: 8,
              textDecoration: "none",
              color: "var(--text)",
            }}
          >
            健康检查 API
          </a>
          <a
            href={`${API_BASE_URL}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-block",
              padding: "8px 14px",
              border: "1px solid var(--line)",
              borderRadius: 8,
              textDecoration: "none",
              color: "var(--text)",
            }}
          >
            API 文档
          </a>
        </div>
      </section>
    </div>
  );
}
