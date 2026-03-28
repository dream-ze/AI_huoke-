import { useNavigate } from "react-router-dom";

type AICapability = {
  id: string;
  icon: string;
  title: string;
  badge?: string;
  desc: string;
  features: string[];
  action: () => void;
};

export function AIHubPage() {
  const navigate = useNavigate();

  const capabilities: AICapability[] = [
    {
      id: "material-clean",
      icon: "🧹",
      title: "素材清洗",
      badge: "核心",
      desc: "自动识别采集内容的质量、相关性和线索价值，过滤低质量内容，标记高价值素材。",
      features: ["质量评分", "相关性评估", "线索价值分析", "风险检测"],
      action: () => navigate("/inbox"),
    },
    {
      id: "knowledge-retrieval",
      icon: "🔍",
      title: "知识检索",
      badge: "新能力",
      desc: "基于语义理解的知识库检索，改写时自动引用相关素材文档，提升内容质量。",
      features: ["语义匹配", "文档检索", "参考引用", "知识图谱"],
      action: () => navigate("/materials"),
    },
    {
      id: "content-rewrite",
      icon: "✏️",
      title: "内容改写",
      badge: "核心",
      desc: "根据目标平台风格，将原始素材改写为适合发布的内容，支持多版本生成。",
      features: ["多平台适配", "风格转换", "三版生成", "合规检查"],
      action: () => navigate("/ai-workbench"),
    },
    {
      id: "compliance-check",
      icon: "🛡️",
      title: "合规审核",
      badge: "安全",
      desc: "自动检测文案中的敏感词、违规表述和潜在风险，给出修改建议。",
      features: ["敏感词检测", "违规识别", "风险等级", "修改建议"],
      action: () => navigate("/compliance"),
    },
    {
      id: "vision-analysis",
      icon: "👁️",
      title: "图片理解",
      desc: "使用火山方舟视觉模型分析图片内容，一键转换为可编辑素材。",
      features: ["图片识别", "内容提取", "一键入库", "素材转换"],
      action: () => navigate("/ai-workbench"),
    },
    {
      id: "insight-analysis",
      icon: "🔥",
      title: "爆款洞察",
      desc: "分析热门内容的结构和特点，提取爆款规律，指导内容创作。",
      features: ["热点追踪", "结构分析", "规律提取", "创作指导"],
      action: () => navigate("/insight"),
    },
  ];

  return (
    <div className="page grid" style={{ gap: 20 }}>
      {/* 页面标题 */}
      <section>
        <h2 style={{ marginBottom: 8 }}>🤖 AI 中枢</h2>
        <p className="muted" style={{ margin: 0 }}>
          智获客 AI 能力中心，从素材清洗到内容生成，全链路智能化
        </p>
      </section>

      {/* AI 能力流程图 */}
      <section className="card">
        <h3 style={{ marginBottom: 16 }}>📈 AI 处理流程</h3>
        <div className="workflow-pipeline">
          <div className="workflow-step" onClick={() => navigate("/collect-center")}>
            <div className="step-icon">📥</div>
            <div className="step-label">采集入库</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step active" onClick={() => navigate("/inbox")}>
            <div className="step-icon">🧹</div>
            <div className="step-label">素材清洗</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step" onClick={() => navigate("/materials")}>
            <div className="step-icon">🔍</div>
            <div className="step-label">知识检索</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step" onClick={() => navigate("/ai-workbench")}>
            <div className="step-icon">✏️</div>
            <div className="step-label">内容生成</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step" onClick={() => navigate("/compliance")}>
            <div className="step-icon">🛡️</div>
            <div className="step-label">合规审核</div>
          </div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step" onClick={() => navigate("/publish")}>
            <div className="step-icon">📤</div>
            <div className="step-label">发布就绪</div>
          </div>
        </div>
      </section>

      {/* AI 能力卡片 */}
      <section>
        <h3 style={{ marginBottom: 16 }}>⚡ AI 能力模块</h3>
        <div className="ai-capability-grid">
          {capabilities.map((cap) => (
            <div
              key={cap.id}
              className="ai-capability-card"
              onClick={cap.action}
            >
              <div className="card-header">
                <div className="card-icon">{cap.icon}</div>
                <h4 className="card-title">{cap.title}</h4>
                {cap.badge && <span className="card-badge">{cap.badge}</span>}
              </div>
              <p className="card-desc">{cap.desc}</p>
              <div className="card-features">
                {cap.features.map((f) => (
                  <span key={f} className="feature-tag">{f}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 使用说明 */}
      <section className="card">
        <h3 style={{ marginBottom: 12 }}>💡 使用指南</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
          <div>
            <h4 style={{ fontSize: 14, marginBottom: 8 }}>1. 内容采集</h4>
            <p className="muted" style={{ margin: 0, lineHeight: 1.6 }}>
              通过采集中心获取爆款内容，支持链接提交和关键词批量采集。
            </p>
          </div>
          <div>
            <h4 style={{ fontSize: 14, marginBottom: 8 }}>2. 素材处理</h4>
            <p className="muted" style={{ margin: 0, lineHeight: 1.6 }}>
              在收件箱审核采集结果，系统自动进行质量评分和风险检测。
            </p>
          </div>
          <div>
            <h4 style={{ fontSize: 14, marginBottom: 8 }}>3. 内容改写</h4>
            <p className="muted" style={{ margin: 0, lineHeight: 1.6 }}>
              选择素材进行 AI 改写，自动参考知识库生成多版本内容。
            </p>
          </div>
          <div>
            <h4 style={{ fontSize: 14, marginBottom: 8 }}>4. 发布转化</h4>
            <p className="muted" style={{ margin: 0, lineHeight: 1.6 }}>
              通过合规审核后创建发布任务，追踪线索转化效果。
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
