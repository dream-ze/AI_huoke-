import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getDashboardStats, mvpGetStatsOverview } from "../../lib/api";
import { MvpStatsOverview, DashboardStats } from "../../types";

// 流程步骤定义
const pipelineSteps = [
  { icon: "📥", label: "采集入库", path: "/mvp-inbox" },
  { icon: "🧹", label: "素材清洗", path: "/mvp-inbox" },
  { icon: "🔍", label: "知识检索", path: "/mvp-knowledge" },
  { icon: "✏️", label: "内容生成", path: "/mvp-workbench" },
  { icon: "🛡️", label: "合规审核", path: "/mvp-workbench" },
  { icon: "🚀", label: "发布就绪", path: "/mvp-workbench" },
];

// 快捷入口定义
const quickActions = [
  { icon: "📥", label: "去收件箱处理", path: "/mvp-inbox", color: "#e67e22" },
  { icon: "📦", label: "去素材库筛选", path: "/mvp-materials", color: "#27ae60" },
  { icon: "✨", label: "去AI工作台生成", path: "/mvp-workbench", color: "#9b59b6" },
  { icon: "📚", label: "去知识库查看", path: "/mvp-knowledge", color: "#3498db" },
];

// 样式定义
const styles = {
  page: {
    padding: "24px",
    maxWidth: "1400px",
    margin: "0 auto",
    display: "flex",
    flexDirection: "column" as const,
    gap: "24px",
  },
  header: {
    marginBottom: "8px",
  },
  title: {
    fontSize: "24px",
    fontWeight: 600,
    margin: 0,
    color: "var(--text)",
  },
  subtitle: {
    margin: "8px 0 0 0",
    color: "var(--muted)",
    fontSize: "14px",
  },
  card: {
    background: "var(--panel)",
    borderRadius: "var(--radius)",
    padding: "20px",
    border: "1px solid var(--line)",
  },
  sectionTitle: {
    fontSize: "16px",
    fontWeight: 600,
    margin: "0 0 16px 0",
    color: "var(--text)",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  // 流程图样式
  pipelineContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexWrap: "wrap" as const,
    gap: "8px",
    padding: "16px 0",
  },
  pipelineStep: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    gap: "8px",
    padding: "16px 20px",
    borderRadius: "12px",
    background: "linear-gradient(135deg, var(--brand) 0%, var(--brand-2) 100%)",
    cursor: "pointer",
    transition: "transform 0.2s, box-shadow 0.2s",
    minWidth: "100px",
  },
  pipelineStepHover: {
    transform: "translateY(-2px)",
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
  },
  stepIcon: {
    fontSize: "28px",
  },
  stepLabel: {
    fontSize: "13px",
    fontWeight: 500,
    color: "#fff",
    textAlign: "center" as const,
    whiteSpace: "nowrap" as const,
  },
  pipelineArrow: {
    fontSize: "20px",
    color: "var(--muted)",
    fontWeight: "bold",
    flexShrink: 0,
  },
  // 指标卡片样式
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "16px",
  },
  statCard: {
    background: "var(--panel)",
    borderRadius: "var(--radius)",
    padding: "20px",
    border: "1px solid var(--line)",
    cursor: "pointer",
    transition: "transform 0.2s, border-color 0.2s",
    textAlign: "center" as const,
  },
  statCardHover: {
    transform: "translateY(-2px)",
    borderColor: "var(--brand)",
  },
  statIcon: {
    fontSize: "28px",
    marginBottom: "8px",
  },
  statValue: {
    fontSize: "32px",
    fontWeight: 700,
    color: "var(--text)",
    lineHeight: 1.2,
  },
  statLabel: {
    fontSize: "13px",
    color: "var(--muted)",
    marginTop: "4px",
  },
  // 快捷入口样式
  quickActionsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "12px",
  },
  quickActionBtn: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "16px 20px",
    borderRadius: "var(--radius)",
    border: "none",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: 500,
    color: "#fff",
    transition: "transform 0.2s, opacity 0.2s",
  },
  quickActionIcon: {
    fontSize: "20px",
  },
  // 最近任务样式
  recentGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
    gap: "20px",
  },
  recentColumn: {
    background: "var(--bg)",
    borderRadius: "var(--radius)",
    padding: "16px",
    border: "1px solid var(--line)",
  },
  recentTitle: {
    fontSize: "14px",
    fontWeight: 600,
    color: "var(--text)",
    marginBottom: "12px",
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  recentList: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "10px",
  },
  recentItem: {
    padding: "12px",
    background: "var(--panel)",
    borderRadius: "8px",
    border: "1px solid var(--line)",
    cursor: "pointer",
    transition: "border-color 0.2s",
  },
  recentItemHover: {
    borderColor: "var(--brand)",
  },
  recentItemTitle: {
    fontSize: "14px",
    fontWeight: 500,
    color: "var(--text)",
    marginBottom: "4px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
  },
  recentItemMeta: {
    fontSize: "12px",
    color: "var(--muted)",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  badge: {
    display: "inline-block",
    padding: "2px 6px",
    borderRadius: "4px",
    fontSize: "11px",
    fontWeight: 500,
    background: "var(--brand)",
    color: "#fff",
  },
  emptyState: {
    padding: "24px",
    textAlign: "center" as const,
    color: "var(--muted)",
    fontSize: "14px",
  },
  loadingState: {
    padding: "60px",
    textAlign: "center" as const,
    color: "var(--muted)",
    fontSize: "16px",
  },
  errorState: {
    padding: "40px",
    textAlign: "center" as const,
  },
  errorText: {
    color: "#e74c3c",
    marginBottom: "16px",
    fontSize: "14px",
  },
  retryBtn: {
    padding: "10px 24px",
    background: "var(--brand)",
    color: "#fff",
    border: "none",
    borderRadius: "var(--radius)",
    fontSize: "14px",
    cursor: "pointer",
  },
};

export function AIHubPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<MvpStatsOverview | null>(null);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hoveredStep, setHoveredStep] = useState<number | null>(null);
  const [hoveredStat, setHoveredStat] = useState<number | null>(null);
  const [hoveredRecent, setHoveredRecent] = useState<string | null>(null);

  // 默认空数据（API失败时的兖底）
  const defaultStats: MvpStatsOverview = {
    inbox_pending: 0,
    material_count: 0,
    knowledge_count: 0,
    today_generation_count: 0,
    risk_content_count: 0,
    recent_generations: [],
    recent_materials: [],
  };

  const defaultDashboardStats: DashboardStats = {
    today_collected: 0,
    today_knowledge_ingested: 0,
    today_generated: 0,
    risk_content_count: 0,
    total_knowledge: 0,
    total_materials: 0,
    date: new Date().toISOString().split('T')[0],
  };

  const loadStats = async () => {
    setLoading(true);
    setError("");
    try {
      // 并行加载两个统计接口
      const [overviewData, dashData] = await Promise.all([
        mvpGetStatsOverview().catch(() => defaultStats),
        getDashboardStats().catch(() => defaultDashboardStats)
      ]);
      setStats(overviewData);
      setDashboardStats(dashData);
    } catch (err: any) {
      console.error("加载统计数据失败:", err);
      setError(err?.message || "加载数据失败");
      // 使用默认值兖底
      setStats(defaultStats);
      setDashboardStats(defaultDashboardStats);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  // 指标卡片配置 - 使用新的dashboard统计数据
  const statCards = [
    {
      icon: "📥",
      label: "今日采集量",
      value: dashboardStats?.today_collected ?? 0,
      path: "/collect-center",
    },
    {
      icon: "📚",
      label: "今日入知识库",
      value: dashboardStats?.today_knowledge_ingested ?? 0,
      path: "/mvp-knowledge",
    },
    {
      icon: "✨",
      label: "今日生成量",
      value: dashboardStats?.today_generated ?? 0,
      path: "/mvp-workbench",
    },
    {
      icon: "⚠️",
      label: "风险文案数",
      value: dashboardStats?.risk_content_count ?? 0,
      path: "/mvp-workbench",
    },
    {
      icon: "📚",
      label: "知识库总量",
      value: dashboardStats?.total_knowledge ?? stats?.knowledge_count ?? 0,
      path: "/mvp-knowledge",
    },
    {
      icon: "📦",
      label: "素材库总量",
      value: dashboardStats?.total_materials ?? stats?.material_count ?? 0,
      path: "/mvp-materials",
    },
  ];

  // 格式化时间
  const formatTime = (dateStr: string) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  };

  // 加载中状态
  if (loading) {
    return (
      <div style={styles.page}>
        <div style={styles.loadingState}>
          <span style={{ fontSize: "32px", marginBottom: "16px", display: "block" }}>⏳</span>
          加载中...
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      {/* 页面标题 */}
      <header style={styles.header}>
        <h1 style={styles.title}>🤖 AI 中枢</h1>
        <p style={styles.subtitle}>
          智获客核心控制台 — 从采集到发布的全链路智能化管理
        </p>
      </header>

      {/* 区域1: 主流程可视化卡片 */}
      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>
          <span>📈</span> 内容生产流程
        </h2>
        <div style={styles.pipelineContainer}>
          {pipelineSteps.map((step, index) => (
            <div key={step.label} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  ...styles.pipelineStep,
                  ...(hoveredStep === index ? styles.pipelineStepHover : {}),
                }}
                onMouseEnter={() => setHoveredStep(index)}
                onMouseLeave={() => setHoveredStep(null)}
                onClick={() => navigate(step.path)}
              >
                <span style={styles.stepIcon}>{step.icon}</span>
                <span style={styles.stepLabel}>{step.label}</span>
              </div>
              {index < pipelineSteps.length - 1 && (
                <span style={styles.pipelineArrow}>→</span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* 区域2: 核心指标区 */}
      <section>
        <h2 style={styles.sectionTitle}>
          <span>📊</span> 核心指标
        </h2>
        {error && !stats && (
          <div style={styles.errorState}>
            <p style={styles.errorText}>{error}</p>
            <button style={styles.retryBtn} onClick={loadStats}>
              重试
            </button>
          </div>
        )}
        <div style={styles.statsGrid}>
          {statCards.map((card, index) => (
            <div
              key={card.label}
              style={{
                ...styles.statCard,
                ...(hoveredStat === index ? styles.statCardHover : {}),
              }}
              onMouseEnter={() => setHoveredStat(index)}
              onMouseLeave={() => setHoveredStat(null)}
              onClick={() => navigate(card.path)}
            >
              <div style={styles.statIcon}>{card.icon}</div>
              <div style={styles.statValue}>{card.value}</div>
              <div style={styles.statLabel}>{card.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 区域3: 快捷入口 */}
      <section>
        <h2 style={styles.sectionTitle}>
          <span>⚡</span> 快捷入口
        </h2>
        <div style={styles.quickActionsGrid}>
          {quickActions.map((action) => (
            <button
              key={action.label}
              style={{
                ...styles.quickActionBtn,
                background: action.color,
              }}
              onClick={() => navigate(action.path)}
              onMouseEnter={(e) => {
                (e.target as HTMLButtonElement).style.opacity = "0.9";
                (e.target as HTMLButtonElement).style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLButtonElement).style.opacity = "1";
                (e.target as HTMLButtonElement).style.transform = "translateY(0)";
              }}
            >
              <span style={styles.quickActionIcon}>{action.icon}</span>
              {action.label}
            </button>
          ))}
        </div>
      </section>

      {/* 区域4: 最近任务区 */}
      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>
          <span>🕐</span> 最近动态
        </h2>
        <div style={styles.recentGrid}>
          {/* 左列：最近生成文案 */}
          <div style={styles.recentColumn}>
            <h3 style={styles.recentTitle}>
              <span>✨</span> 最近生成文案
            </h3>
            <div style={styles.recentList}>
              {stats?.recent_generations && stats.recent_generations.length > 0 ? (
                stats.recent_generations.slice(0, 5).map((item) => (
                  <div
                    key={`gen-${item.id}`}
                    style={{
                      ...styles.recentItem,
                      ...(hoveredRecent === `gen-${item.id}` ? styles.recentItemHover : {}),
                    }}
                    onMouseEnter={() => setHoveredRecent(`gen-${item.id}`)}
                    onMouseLeave={() => setHoveredRecent(null)}
                    onClick={() => navigate("/mvp-workbench")}
                  >
                    <div style={styles.recentItemTitle}>{item.title || "未命名文案"}</div>
                    <div style={styles.recentItemMeta}>
                      <span style={styles.badge}>{item.version || "V1"}</span>
                      <span>{formatTime(item.created_at)}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div style={styles.emptyState}>暂无生成记录</div>
              )}
            </div>
          </div>

          {/* 右列：最近新增素材 */}
          <div style={styles.recentColumn}>
            <h3 style={styles.recentTitle}>
              <span>📦</span> 最近新增素材
            </h3>
            <div style={styles.recentList}>
              {stats?.recent_materials && stats.recent_materials.length > 0 ? (
                stats.recent_materials.slice(0, 5).map((item) => (
                  <div
                    key={`mat-${item.id}`}
                    style={{
                      ...styles.recentItem,
                      ...(hoveredRecent === `mat-${item.id}` ? styles.recentItemHover : {}),
                    }}
                    onMouseEnter={() => setHoveredRecent(`mat-${item.id}`)}
                    onMouseLeave={() => setHoveredRecent(null)}
                    onClick={() => navigate(`/mvp-materials`)}
                  >
                    <div style={styles.recentItemTitle}>{item.title || "未命名素材"}</div>
                    <div style={styles.recentItemMeta}>
                      <span style={styles.badge}>{item.platform || "未知"}</span>
                      <span>{formatTime(item.created_at)}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div style={styles.emptyState}>暂无素材记录</div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
