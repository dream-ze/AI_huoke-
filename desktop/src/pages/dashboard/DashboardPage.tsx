import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDashboardSummary, getTrend } from "../../lib/api";
import { DashboardSummary, TrendItem } from "../../types";

const emptySummary: DashboardSummary = {
  today_new_customers: 0,
  today_wechat_adds: 0,
  today_leads: 0,
  today_valid_leads: 0,
  today_conversions: 0,
  pending_follow_count: 0,
  pending_review_count: 0,
};

export function DashboardPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function run() {
      try {
        const [s, t] = await Promise.all([getDashboardSummary(), getTrend(7)]);
        setSummary(s);
        setTrend(t?.data || []);
      } catch (err: any) {
        setError(err?.response?.data?.detail || "看板数据加载失败，请稍后重试");
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
          {error && <section className="card"><div className="error">{error}</div></section>}
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
            <h3 style={{ marginBottom: 12 }}>快捷入口</h3>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button className="secondary" type="button" onClick={() => navigate("/collect-center")}>去采集中心</button>
              <button className="secondary" type="button" onClick={() => navigate("/inbox")}>去收件箱分拣</button>
              <button className="secondary" type="button" onClick={() => navigate("/materials")}>去素材编辑</button>
              <button className="secondary" type="button" onClick={() => navigate("/publish")}>去发布任务</button>
              <button className="secondary" type="button" onClick={() => navigate("/leads")}>去线索池</button>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
