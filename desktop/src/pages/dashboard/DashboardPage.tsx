import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDashboardSummary, getTrend, getPublishTaskStats } from "../../lib/api";
import { dashboardApi } from "../../api/dashboardApi";
import { DashboardSummary, TrendItem, PublishTaskStats, BusinessMetrics, ConversionFunnel, ContentLayerMetrics, AcquisitionLayerMetrics, ConversionLayerMetrics } from "../../types";

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

const emptyMetrics: BusinessMetrics = {
  leads_today: 0,
  high_intent_leads: 0,
  ai_handle_rate: 0,
  takeover_rate: 0,
  content_to_lead_rate: 0,
  published_this_week: 0,
  leads_this_week: 0,
};

const emptyFunnel: ConversionFunnel = {
  funnel: [],
  conversion_rates: {
    content_to_publish: 0,
    publish_to_lead: 0,
    lead_to_customer: 0,
    customer_to_deal: 0,
  },
};

const emptyContentLayer: ContentLayerMetrics = {
  today_generation_count: 0,
  compliance_pass_rate: 0,
  adoption_rate: 0,
  publish_rate: 0,
  total_materials: 0,
  knowledge_items: 0,
};

const emptyAcquisitionLayer: AcquisitionLayerMetrics = {
  total_leads: 0,
  leads_by_platform: [],
  leads_by_account: [],
  leads_by_topic: [],
  wechat_add_rate: 0,
  contact_rate: 0,
};

const emptyConversionLayer: ConversionLayerMetrics = {
  grade_distribution: {},
  avg_first_response_hours: 0,
  followup_completion_rate: 0,
  conversion_rate: 0,
  total_converted: 0,
  total_revenue: 0,
};

const metricConfigs = [
  { key: "leads_today", label: "今日线索", color: "#3b82f6" },
  { key: "high_intent_leads", label: "高意向线索", color: "#10b981" },
  { key: "ai_handle_rate", label: "AI处理率", color: "#8b5cf6", isPercent: true },
  { key: "takeover_rate", label: "人工接管率", color: "#f59e0b", isPercent: true },
  { key: "content_to_lead_rate", label: "内容转化率", color: "#ef4444", isPercent: true },
  { key: "published_this_week", label: "本周发布", color: "#06b6d4" },
  { key: "leads_this_week", label: "本周线索", color: "#ec4899" },
];

const funnelStageLabels: Record<string, string> = {
  content_generated: "内容生成",
  published: "已发布",
  leads: "获得线索",
  customers: "转化客户",
  deals: "成交",
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

type LayerTab = 'content' | 'acquisition' | 'conversion';

export function DashboardPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [taskStats, setTaskStats] = useState<PublishTaskStats>(emptyStats);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [metrics, setMetrics] = useState<BusinessMetrics>(emptyMetrics);
  const [funnel, setFunnel] = useState<ConversionFunnel>(emptyFunnel);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [metricsError, setMetricsError] = useState("");
  const [error, setError] = useState("");
  
  // 三层看板状态
  const [activeLayerTab, setActiveLayerTab] = useState<LayerTab>('content');
  const [contentLayer, setContentLayer] = useState<ContentLayerMetrics>(emptyContentLayer);
  const [acquisitionLayer, setAcquisitionLayer] = useState<AcquisitionLayerMetrics>(emptyAcquisitionLayer);
  const [conversionLayer, setConversionLayer] = useState<ConversionLayerMetrics>(emptyConversionLayer);
  const [layerLoading, setLayerLoading] = useState(false);

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
  
  useEffect(() => {
    async function fetchMetricsAndFunnel() {
      try {
        setMetricsLoading(true);
        const [m, f] = await Promise.all([
          dashboardApi.getMetrics().catch(() => null),
          dashboardApi.getFunnel().catch(() => null),
        ]);
        if (m) setMetrics(m);
        if (f) setFunnel(f);
      } catch (err: any) {
        setMetricsError("驾驶舱指标加载失败");
      } finally {
        setMetricsLoading(false);
      }
    }
  
    fetchMetricsAndFunnel();
  }, []);
  
  // 获取三层看板数据
  useEffect(() => {
    async function fetchLayerData() {
      try {
        setLayerLoading(true);
        const [content, acquisition, conversion] = await Promise.all([
          dashboardApi.getContentLayerMetrics('today').catch(() => null),
          dashboardApi.getAcquisitionLayerMetrics('week').catch(() => null),
          dashboardApi.getConversionLayerMetrics('month').catch(() => null),
        ]);
        if (content) setContentLayer(content);
        if (acquisition) setAcquisitionLayer(acquisition);
        if (conversion) setConversionLayer(conversion);
      } catch (err) {
        console.error('三层看板数据加载失败', err);
      } finally {
        setLayerLoading(false);
      }
    }
    
    fetchLayerData();
  }, []);

  // 计算漏斗最大数量用于宽度计算
  const maxFunnelCount = Math.max(...(funnel.funnel?.map((s) => s.count) || [1]), 1);

  return (
    <div className="page grid" style={{ gap: 20 }}>
      {/* 三层看板 Tab */}
      <section className="card" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          {[
            { key: 'content', label: '内容层', icon: '📝' },
            { key: 'acquisition', label: '获客层', icon: '🎯' },
            { key: 'conversion', label: '转化层', icon: '💰' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveLayerTab(tab.key as LayerTab)}
              style={{
                padding: "10px 20px",
                border: "none",
                borderRadius: 8,
                background: activeLayerTab === tab.key ? "#3b82f6" : "#f1f5f9",
                color: activeLayerTab === tab.key ? "#fff" : "#64748b",
                cursor: "pointer",
                fontWeight: 500,
                fontSize: 14,
                transition: "all 0.2s ease",
              }}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
        
        {layerLoading ? (
          <div style={{ color: "#999", textAlign: "center", padding: 20 }}>加载中...</div>
        ) : (
          <>
            {/* 内容层 */}
            {activeLayerTab === 'content' && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                <MetricCard label="今日生成数" value={contentLayer.today_generation_count} color="#3b82f6" />
                <MetricCard label="合规通过率" value={contentLayer.compliance_pass_rate} color="#10b981" isPercent />
                <MetricCard label="人工采纳率" value={contentLayer.adoption_rate} color="#8b5cf6" isPercent />
                <MetricCard label="发布率" value={contentLayer.publish_rate} color="#f59e0b" isPercent />
                <MetricCard label="素材总数" value={contentLayer.total_materials} color="#06b6d4" />
                <MetricCard label="知识库条目" value={contentLayer.knowledge_items} color="#ec4899" />
              </div>
            )}
            
            {/* 获客层 */}
            {activeLayerTab === 'acquisition' && (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
                  <MetricCard label="总线索数" value={acquisitionLayer.total_leads} color="#3b82f6" />
                  <MetricCard label="加微率" value={acquisitionLayer.wechat_add_rate} color="#10b981" isPercent />
                  <MetricCard label="留资率" value={acquisitionLayer.contact_rate} color="#f59e0b" isPercent />
                </div>
                {acquisitionLayer.leads_by_platform.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <h4 style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>平台线索分布</h4>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {acquisitionLayer.leads_by_platform.map((p) => (
                        <span key={p.platform} style={{ background: "#f1f5f9", padding: "4px 12px", borderRadius: 4, fontSize: 12 }}>
                          {p.platform}: {p.count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* 转化层 */}
            {activeLayerTab === 'conversion' && (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
                  <MetricCard label="平均首次响应(h)" value={conversionLayer.avg_first_response_hours} color="#3b82f6" isDecimal />
                  <MetricCard label="跟进完成率" value={conversionLayer.followup_completion_rate} color="#10b981" isPercent />
                  <MetricCard label="转化率" value={conversionLayer.conversion_rate} color="#8b5cf6" isPercent />
                  <MetricCard label="总转化数" value={conversionLayer.total_converted} color="#f59e0b" />
                  <MetricCard label="预估收入" value={conversionLayer.total_revenue} color="#06b6d4" isDecimal prefix="¥" />
                </div>
                {Object.keys(conversionLayer.grade_distribution).length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <h4 style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>线索分级分布</h4>
                    <div style={{ display: "flex", gap: 8 }}>
                      {Object.entries(conversionLayer.grade_distribution).map(([grade, percent]) => (
                        <span key={grade} style={{ 
                          background: grade === 'A' ? '#10b981' : grade === 'B' ? '#3b82f6' : grade === 'C' ? '#f59e0b' : '#6b7280',
                          color: '#fff',
                          padding: "4px 12px", 
                          borderRadius: 4, 
                          fontSize: 12 
                        }}>
                          {grade}级: {percent.toFixed(1)}%
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </section>
      
      {/* 驾驶舱指标卡片区 */}
      <section className="card" style={{ padding: "20px 24px" }}>
        <h3 style={{ marginBottom: 16, fontSize: 16, color: "#333" }}>📊 驾驶舱核心指标</h3>
        {metricsLoading ? (
          <div style={{ color: "#999", textAlign: "center", padding: 20 }}>加载中...</div>
        ) : metricsError ? (
          <div style={{ color: "#ef4444", textAlign: "center", padding: 20 }}>{metricsError}</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 12 }}>
            {metricConfigs.map((cfg) => (
              <div
                key={cfg.key}
                style={{
                  textAlign: "center",
                  padding: "16px 8px",
                  background: "#f8fafc",
                  borderRadius: 8,
                  borderLeft: `3px solid ${cfg.color}`,
                }}
              >
                <div
                  style={{
                    fontSize: 28,
                    fontWeight: "bold",
                    color: cfg.color,
                  }}
                >
                  {cfg.isPercent
                    ? `${((metrics as any)[cfg.key] * 100).toFixed(1)}%`
                    : (metrics as any)[cfg.key]}
                </div>
                <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>{cfg.label}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 转化漏斗 */}
      <section className="card" style={{ padding: "20px 24px" }}>
        <h3 style={{ marginBottom: 16, fontSize: 16, color: "#333" }}>🔄 转化漏斗</h3>
        {metricsLoading ? (
          <div style={{ color: "#999", textAlign: "center", padding: 20 }}>加载中...</div>
        ) : !funnel.funnel || funnel.funnel.length === 0 ? (
          <div style={{ color: "#999", textAlign: "center", padding: 20 }}>暂无数据</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {funnel.funnel.map((stage, idx) => {
              const widthPercent = Math.max((stage.count / maxFunnelCount) * 100, 15);
              const colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444"];
              return (
                <div key={stage.stage} style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <div style={{ width: 80, fontSize: 13, color: "#666", textAlign: "right" }}>
                    {funnelStageLabels[stage.stage] || stage.stage}
                  </div>
                  <div style={{ flex: 1, height: 32, position: "relative" }}>
                    <div
                      style={{
                        width: `${widthPercent}%`,
                        height: "100%",
                        background: colors[idx % colors.length],
                        borderRadius: 4,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                        fontWeight: "bold",
                        fontSize: 14,
                        transition: "width 0.3s ease",
                      }}
                    >
                      {stage.count}
                    </div>
                  </div>
                  {idx > 0 && (
                    <div style={{ width: 60, fontSize: 12, color: "#999" }}>
                      {funnel.conversion_rates &&
                        `${(((funnel.conversion_rates as any)[
                          ["content_to_publish", "publish_to_lead", "lead_to_customer", "customer_to_deal"][idx - 1]
                        ] || 0) * 100).toFixed(1)}%`}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

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

// 辅助组件：指标卡片
function MetricCard({ 
  label, 
  value, 
  color, 
  isPercent = false, 
  isDecimal = false,
  prefix = ''
}: { 
  label: string; 
  value: number; 
  color: string; 
  isPercent?: boolean; 
  isDecimal?: boolean;
  prefix?: string;
}) {
  return (
    <div
      style={{
        textAlign: "center",
        padding: "16px 12px",
        background: "#f8fafc",
        borderRadius: 8,
        borderLeft: `3px solid ${color}`,
      }}
    >
      <div
        style={{
          fontSize: 24,
          fontWeight: "bold",
          color: color,
        }}
      >
        {prefix}{isPercent ? `${(value * 100).toFixed(1)}%` : isDecimal ? value.toFixed(1) : value}
      </div>
      <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>{label}</div>
    </div>
  );
}
