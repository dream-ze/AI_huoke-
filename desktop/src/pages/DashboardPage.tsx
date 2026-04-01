import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDashboardSummary, getLeadFunnel, getTrend } from "../lib/api";
import { DashboardSummary, LeadFunnel, TrendItem } from "../types";

const emptySummary: DashboardSummary = {
  today_new_customers: 0,
  today_wechat_adds: 0,
  today_leads: 0,
  today_valid_leads: 0,
  today_conversions: 0,
  pending_follow_count: 0,
  pending_review_count: 0
};

const emptyFunnel: LeadFunnel = {
  stages: [],
  period_days: 30
};

const funnelColors: Record<string, string> = {
  published: "#3b82f6",
  leads_generated: "#10b981",
  contacted: "#f59e0b",
  qualified: "#8b5cf6",
  converted: "#ef4444",
};

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [funnel, setFunnel] = useState<LeadFunnel>(emptyFunnel);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function run() {
      try {
        const [s, t, f] = await Promise.all([getDashboardSummary(), getTrend(7), getLeadFunnel(30)]);
        setSummary(s);
        setTrend(t?.data || []);
        setFunnel(f || emptyFunnel);
      } finally {
        setLoading(false);
      }
    }

    run();
  }, []);

  return (
    <div className="page grid" style={{ gap: 18 }}>
      <h2>经营看板</h2>

      {loading ? (
        <div className="card">加载中...</div>
      ) : (
        <>
          <section className="grid cards">
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
            <div className="card">
              <h3>今日转化数</h3>
              <div className="big-number">{summary.today_conversions}</div>
            </div>
            <div className="card">
              <h3>待审核内容</h3>
              <div className="big-number">{summary.pending_review_count}</div>
            </div>
          </section>

          <section className="card">
            <h3 style={{ marginBottom: 12 }}>最近7天线索趋势</h3>
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <LineChart data={trend}>
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="total_leads" stroke="#b63d1f" strokeWidth={3} />
                  <Line
                    type="monotone"
                    dataKey="total_valid_leads"
                    stroke="#0f6d7a"
                    strokeWidth={3}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="card">
            <h3 style={{ marginBottom: 12 }}>转化漏斗（近{funnel.period_days}天）</h3>
            {funnel.stages.length === 0 ? (
              <div style={{ color: "#999", textAlign: "center", padding: 20 }}>暂无数据</div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
                {funnel.stages.map((stage, idx) => (
                  <div
                    key={stage.stage}
                    style={{
                      textAlign: "center",
                      padding: "12px 8px",
                      background: "#f8f9fa",
                      borderRadius: 8,
                      borderLeft: idx === 0 ? "none" : "1px solid #e9ecef",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 28,
                        fontWeight: "bold",
                        color: funnelColors[stage.stage] || "#333",
                      }}
                    >
                      {stage.count}
                    </div>
                    <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>{stage.stage_label}</div>
                    <div
                      style={{
                        fontSize: 12,
                        color: "#999",
                        marginTop: 4,
                        background: "#fff",
                        padding: "2px 6px",
                        borderRadius: 4,
                      }}
                    >
                      {(stage.rate * 100).toFixed(1)}%
                    </div>
                    {/* 进度条 */}
                    <div
                      style={{
                        width: "100%",
                        height: 4,
                        background: "#e9ecef",
                        borderRadius: 2,
                        marginTop: 8,
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${stage.rate * 100}%`,
                          height: "100%",
                          background: funnelColors[stage.stage] || "#333",
                          borderRadius: 2,
                          transition: "width 0.3s ease",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
