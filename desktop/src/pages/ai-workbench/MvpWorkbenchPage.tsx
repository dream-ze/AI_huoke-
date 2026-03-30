import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { generateFullPipeline, mvpComplianceCheck, getKnowledgeLibraries, submitFeedback, getFeedbackTags } from "../../lib/api";
import { FullPipelineResponse, KnowledgeLibraryStat } from "../../types";
import { copyToClipboard } from "../../utils/clipboard";

// 选项配置
const PLATFORM_OPTIONS = [
  { value: "xiaohongshu", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
];

const ACCOUNT_TYPE_OPTIONS = [
  { value: "loan_advisor", label: "助贷顾问" },
  { value: "agent", label: "中介" },
  { value: "knowledge_account", label: "科普号" },
];

const AUDIENCE_OPTIONS = [
  { value: "bad_credit", label: "征信花" },
  { value: "high_debt", label: "负债高" },
  { value: "office_worker", label: "上班族" },
  { value: "self_employed", label: "个体户" },
];

const TOPIC_OPTIONS = [
  { value: "loan", label: "贷款" },
  { value: "credit", label: "征信" },
  { value: "online_loan", label: "网贷" },
  { value: "housing_fund", label: "公积金" },
];

const GOAL_OPTIONS = [
  { value: "private_message", label: "引导私信" },
  { value: "consultation", label: "引导咨询" },
  { value: "conversion", label: "促进转化" },
];

const TONE_OPTIONS = [
  { value: "professional", label: "专业严谨" },
  { value: "friendly", label: "亲切友好" },
  { value: "humorous", label: "幽默风趣" },
  { value: "empathetic", label: "共情走心" },
  { value: "urgent", label: "紧迫感" },
];

const MODEL_OPTIONS = [
  { value: "volcano", label: "🌋 火山模型" },
  { value: "local", label: "💻 本地模型" },
];

// 版本名称映射
const VERSION_LABELS: Record<string, string> = {
  rewrite_base: "基础改写版",
  professional: "专业型",
  casual: "口语型",
  seeding: "种草型",
};

// 版本颜色配置
const VERSION_COLORS: Record<string, { border: string; bg: string }> = {
  rewrite_base: { border: "#64748b", bg: "#f8fafc" },
  professional: { border: "#3b82f6", bg: "#eff6ff" },
  casual: { border: "#f97316", bg: "#fff7ed" },
  seeding: { border: "#ec4899", bg: "#fdf2f8" },
};

// 风险等级显示
const RISK_DISPLAY: Record<string, { icon: string; label: string; color: string }> = {
  low: { icon: "🟢", label: "低风险", color: "#4caf50" },
  medium: { icon: "🟡", label: "中风险", color: "#ff9800" },
  high: { icon: "🔴", label: "高风险", color: "#f44336" },
};

// 选项按钮组组件
function OptionGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontSize: 13, color: "var(--muted)", marginBottom: 8, fontWeight: 500 }}>
        {label}
      </label>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            style={{
              padding: "8px 16px",
              borderRadius: 20,
              border: value === opt.value ? "2px solid var(--brand)" : "1px solid var(--line)",
              background: value === opt.value ? "linear-gradient(90deg, var(--brand), #d45b39)" : "var(--panel)",
              color: value === opt.value ? "#fff" : "var(--text)",
              fontWeight: value === opt.value ? 600 : 400,
              cursor: "pointer",
              transition: "all 0.2s ease",
              fontSize: 14,
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function MvpWorkbenchPage() {
  const location = useLocation();
  
  // 条件配置状态
  const [platform, setPlatform] = useState("xiaohongshu");
  const [accountType, setAccountType] = useState("loan_advisor");
  const [audience, setAudience] = useState("bad_credit");
  const [topic, setTopic] = useState("loan");
  const [goal, setGoal] = useState("private_message");
  const [tone, setTone] = useState("professional");
  const [model, setModel] = useState("volcano");
  const [extraRequirements, setExtraRequirements] = useState("");

  // 生成状态
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FullPipelineResponse | null>(null);

  // 复制状态
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [copiedFinal, setCopiedFinal] = useState(false);

  // 合规检测状态
  const [complianceText, setComplianceText] = useState("");
  const [complianceResult, setComplianceResult] = useState<any>(null);
  const [complianceLoading, setComplianceLoading] = useState(false);
  
  // 版本复制状态
  const [copiedVersions, setCopiedVersions] = useState<Record<string, boolean>>({});

  // 反馈状态
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<Record<string, boolean>>({});
  const [showFeedbackPanel, setShowFeedbackPanel] = useState<string | null>(null);  // 当前显示反馈面板的版本style
  const [feedbackRating, setFeedbackRating] = useState<number>(0);
  const [feedbackTags, setFeedbackTags] = useState<string[]>([]);
  const [availableFeedbackTags, setAvailableFeedbackTags] = useState<string[]>([]);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [generationId, setGenerationId] = useState<string>("");

  // 知识库状态
  const [knowledgeStatus, setKnowledgeStatus] = useState<{
    hasData: boolean;
    totalCount: number;
    libraries: KnowledgeLibraryStat[];
    loading: boolean;
  }>({ hasData: false, totalCount: 0, libraries: [], loading: true });

  // 检查知识库状态
  const checkKnowledgeStatus = async () => {
    setKnowledgeStatus(prev => ({ ...prev, loading: true }));
    try {
      const libraries = await getKnowledgeLibraries();
      const total = libraries.reduce((sum: number, lib: KnowledgeLibraryStat) => sum + (lib.count || 0), 0);
      setKnowledgeStatus({
        hasData: total > 0,
        totalCount: total,
        libraries: libraries,
        loading: false,
      });
    } catch (e) {
      console.warn('知识库状态检查失败:', e);
      setKnowledgeStatus(prev => ({ ...prev, loading: false }));
    }
  };

  // 页面加载时检查知识库状态
  useEffect(() => {
    checkKnowledgeStatus();
  }, []);

  // 加载反馈标签选项
  useEffect(() => {
    const loadFeedbackTags = async () => {
      try {
        const tags = await getFeedbackTags();
        setAvailableFeedbackTags(tags);
      } catch (e) {
        // 使用默认值
        setAvailableFeedbackTags([
          "太长", "太短", "不够专业", "太生硬", "不相关",
          "数据错误", "风格不符", "缺少关键信息", "风险敏感词", "其他"
        ]);
      }
    };
    loadFeedbackTags();
  }, []);

  // 接收素材库跳转参数
  useEffect(() => {
    const state = location.state as { 
      materialId?: number; 
      materialTitle?: string; 
      materialContent?: string; 
      materialPlatform?: string;
    } | null;
    
    if (state?.materialContent) {
      setExtraRequirements(state.materialContent);
    }
    
    if (state?.materialPlatform) {
      const platformMap: Record<string, string> = {
        xiaohongshu: "xiaohongshu",
        douyin: "douyin",
        zhihu: "zhihu",
        weibo: "weibo",
      };
      if (platformMap[state.materialPlatform]) {
        setPlatform(platformMap[state.materialPlatform]);
      }
    }
  }, [location.state]);

  // 解析错误信息，返回用户友好的错误提示
  const parseErrorMessage = (err: any): string => {
    // 增加调试日志
    console.error('[AI工作台] 生成失败:', err);
      
    const detail = err?.response?.data?.detail || err?.message || '';
    const detailStr = String(detail).toLowerCase();
      
    // axios 网络错误 (ERR_NETWORK)
    if (err?.code === 'ERR_NETWORK' || err?.code === 'ECONNABORTED') {
      return '网络连接失败，请检查网络状态或后端服务是否正常运行。';
    }
      
    // 知识库相关错误
    if (detailStr.includes('knowledge') || detailStr.includes('知识库') || detailStr.includes('no context') || detailStr.includes('empty')) {
      return '知识库暂无相关内容，请先完成知识库构建后再试。可前往"内容采集"添加素材并构建知识库。';
    }
      
    // AI 模型相关错误
    if (detailStr.includes('model') || detailStr.includes('ollama') || detailStr.includes('ark') || 
        detailStr.includes('llm') || detailStr.includes('ai service') || detailStr.includes('timeout') && detailStr.includes('model')) {
      return 'AI 模型服务暂不可用，请检查 Ollama 或火山方舟配置是否正常。';
    }
      
    // 网络连接错误
    if (detailStr.includes('timeout') || detailStr.includes('connect') || detailStr.includes('network') || 
        detailStr.includes('econnrefused') || detailStr.includes('enotfound') || err?.code === 'ECONNREFUSED') {
      return '网络连接失败，请检查后端服务是否正常运行。';
    }
      
    // 认证错误
    if (err?.response?.status === 401 || detailStr.includes('unauthorized') || detailStr.includes('token')) {
      return '登录已过期，请重新登录后再试。';
    }
      
    // 服务器错误
    if (err?.response?.status >= 500) {
      return '服务器内部错误，请稍后重试或联系管理员。';
    }
      
    // 返回原始错误信息（如果有）
    return detail || '生成失败，请稍后重试。';
  };

  // 生成处理函数
  const handleGenerate = async () => {
    // 先刷新知识库状态
    if (!knowledgeStatus.hasData && !knowledgeStatus.loading) {
      await checkKnowledgeStatus();
    }
    
    setGenerating(true);
    setError(null);
    setResult(null);
    try {
      const payload = {
        platform,
        account_type: accountType,
        audience,
        topic,
        goal,
        model,
        extra_requirements: extraRequirements || undefined,
        tone,
      };
      const data = await generateFullPipeline(payload);
      setResult(data);
    } catch (err: any) {
      setError(parseErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  // 复制功能
  const handleCopy = async (text: string, idx?: number) => {
    const success = await copyToClipboard(text);
    if (success) {
      if (idx !== undefined) {
        setCopiedIdx(idx);
        setTimeout(() => setCopiedIdx(null), 2000);
      } else {
        setCopiedFinal(true);
        setTimeout(() => setCopiedFinal(false), 2000);
      }
    }
  };

  // 复制版本文案
  const handleCopyVersion = async (text: string, versionKey: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedVersions(prev => ({ ...prev, [versionKey]: true }));
      setTimeout(() => {
        setCopiedVersions(prev => ({ ...prev, [versionKey]: false }));
      }, 2000);
    }
  };

  // 获取风险等级显示配置
  const getRiskDisplay = (level: string) => {
    return RISK_DISPLAY[level?.toLowerCase()] || RISK_DISPLAY.low;
  };

  // 合规检测处理函数
  const handleComplianceCheck = async () => {
    if (!complianceText.trim()) return;
    setComplianceLoading(true);
    setComplianceResult(null);
    try {
      const result = await mvpComplianceCheck({ text: complianceText });
      setComplianceResult(result);
    } catch (err) {
      console.error("合规检测失败:", err);
    } finally {
      setComplianceLoading(false);
    }
  };

  // 生成唯一的 generation_id
  const generateUniqueId = () => {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 10);
    return `gen_${timestamp}_${random}`;
  };

  // 提交反馈
  const handleFeedbackSubmit = async (
    text: string,
    feedbackType: 'adopted' | 'modified' | 'rejected',
    styleKey: string
  ) => {
    if (feedbackSubmitted[styleKey]) return; // 已提交过
    
    setFeedbackLoading(true);
    try {
      const genId = generationId || generateUniqueId();
      if (!generationId) setGenerationId(genId);
      
      // 构建查询参数字符串
      const queryParams = JSON.stringify({
        platform, accountType, audience, topic, goal, tone, model
      });
      
      await submitFeedback({
        generation_id: genId,
        query: queryParams,
        generated_text: text,
        feedback_type: feedbackType,
        rating: feedbackRating > 0 ? feedbackRating : undefined,
        feedback_tags: feedbackTags.length > 0 ? feedbackTags : undefined,
      });
      
      setFeedbackSubmitted(prev => ({ ...prev, [styleKey]: true }));
      setShowFeedbackPanel(null);
      setFeedbackRating(0);
      setFeedbackTags([]);
    } catch (err) {
      console.error("反馈提交失败:", err);
    } finally {
      setFeedbackLoading(false);
    }
  };

  // 切换反馈标签
  const toggleFeedbackTag = (tag: string) => {
    setFeedbackTags(prev => 
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  return (
    <div className="page" style={{ maxWidth: 1000, margin: "0 auto" }}>
      {/* 页面标题 */}
      <h2 style={{ marginBottom: 8 }}>AI 内容工作台</h2>
      <p className="muted" style={{ marginBottom: 24 }}>
        选择内容生成条件，一键生成多版本专业文案，自动进行合规审核
      </p>

      {/* 错误提示 */}
      {error && (
        <div
          style={{
            padding: "12px 16px",
            marginBottom: 16,
            borderRadius: 8,
            background: "#fef2f2",
            color: "var(--danger)",
            fontSize: 14,
            border: "1px solid #fecaca",
          }}
        >
          <strong>⚠️ 生成失败</strong>
          <p style={{ margin: "4px 0 0", fontSize: 13, lineHeight: 1.6 }}>{error}</p>
        </div>
      )}

      {/* 知识库状态提示 */}
      {!knowledgeStatus.loading && !knowledgeStatus.hasData && (
        <div
          style={{
            padding: "12px 16px",
            marginBottom: 16,
            borderRadius: 8,
            backgroundColor: "#fff7e6",
            border: "1px solid #ffd591",
            color: "#ad6800",
          }}
        >
          <strong>⚠️ 知识库暂无内容</strong>
          <p style={{ margin: "4px 0 0", fontSize: 13, lineHeight: 1.6 }}>
            请先完成内容采集和知识库构建，或运行种子数据初始化脚本。
            知识库为空时，AI 生成的内容质量会较低。
          </p>
        </div>
      )}

      {/* 知识库有数据时显示统计 */}
      {knowledgeStatus.hasData && knowledgeStatus.libraries.length > 0 && (
        <div
          style={{
            padding: "8px 16px",
            marginBottom: 16,
            borderRadius: 8,
            backgroundColor: "#f0fdf4",
            border: "1px solid #bbf7d0",
            color: "#166534",
            fontSize: 13,
          }}
        >
          <span style={{ marginRight: 12 }}>📚 知识库已就绪</span>
          <span style={{ opacity: 0.8 }}>共 {knowledgeStatus.totalCount} 条内容</span>
        </div>
      )}

      {/* 条件配置区 */}
      <div
        className="card"
        style={{
          marginBottom: 24,
          background: "linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%)",
          color: "#fff",
          border: "none",
        }}
      >
        <h3 style={{ color: "#fff", marginBottom: 20, fontSize: 16 }}>📝 内容生成配置</h3>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
          <OptionGroup
            label="目标平台"
            options={PLATFORM_OPTIONS}
            value={platform}
            onChange={setPlatform}
          />
          <OptionGroup
            label="账号定位"
            options={ACCOUNT_TYPE_OPTIONS}
            value={accountType}
            onChange={setAccountType}
          />
          <OptionGroup
            label="面向人群"
            options={AUDIENCE_OPTIONS}
            value={audience}
            onChange={setAudience}
          />
          <OptionGroup
            label="内容主题"
            options={TOPIC_OPTIONS}
            value={topic}
            onChange={setTopic}
          />
          <div style={{ gridColumn: "1 / -1" }}>
            <OptionGroup
              label="内容目标"
              options={GOAL_OPTIONS}
              value={goal}
              onChange={setGoal}
            />
          </div>

          {/* 口吻选择 */}
          <div style={{ gridColumn: "1 / -1", marginBottom: "1rem" }}>
            <label style={{ color: "#BFA98E", fontSize: "0.9rem", marginBottom: "0.5rem", display: "block" }}>
              说话口吻
            </label>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {TONE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setTone(opt.value)}
                  style={{
                    padding: "0.5rem 1rem",
                    borderRadius: "20px",
                    border: "none",
                    cursor: "pointer",
                    fontSize: "0.85rem",
                    background: tone === opt.value ? "#A0522D" : "#3A322C",
                    color: tone === opt.value ? "#FFF" : "#D4C5B2",
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ gridColumn: "1 / -1" }}>
            <OptionGroup
              label="AI模型"
              options={MODEL_OPTIONS}
              value={model}
              onChange={setModel}
            />
          </div>
          <div style={{ gridColumn: "1 / -1", marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 13, color: "var(--muted)", marginBottom: 8, fontWeight: 500 }}>
              自定义补充要求（可选）
            </label>
            <textarea
              value={extraRequirements}
              onChange={(e) => setExtraRequirements(e.target.value)}
              placeholder="输入额外的内容要求，如风格偏好、特定关键词、禁忌词等..."
              style={{
                width: "100%",
                minHeight: 80,
                padding: 12,
                borderRadius: 8,
                border: "1px solid var(--line)",
                background: "var(--panel)",
                color: "var(--text)",
                fontSize: 14,
                resize: "vertical",
              }}
            />
          </div>
        </div>

        <button
          className="primary"
          onClick={handleGenerate}
          disabled={generating}
          style={{
            width: "100%",
            padding: "16px 24px",
            fontSize: 18,
            fontWeight: 700,
            marginTop: 8,
            opacity: generating ? 0.7 : 1,
            cursor: generating ? "not-allowed" : "pointer",
          }}
        >
          {generating ? "⏳ AI正在生成中..." : "🚀 开始生成"}
        </button>
      </div>

      {/* 生成结果区 */}
      {(generating || result) && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16 }}>✨ 生成结果</h3>

          {generating && (
            <div style={{ textAlign: "center", padding: 48 }}>
              <div style={{ fontSize: 48, marginBottom: 16, animation: "pulse 1.5s infinite" }}>⏳</div>
              <p className="muted">AI正在生成多版本文案，请稍候...</p>
              <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
            </div>
          )}

          {!generating && result?.versions && (
            <>
              {/* 改写基础版 */}
              {result.rewrite_base && (
                <div style={{
                  marginBottom: 20,
                  padding: 16,
                  background: "#f8fafc",
                  borderRadius: 12,
                  border: "1px dashed var(--line)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                    <span style={{
                      background: "#64748b",
                      color: "#fff",
                      padding: "4px 10px",
                      borderRadius: 12,
                      fontSize: 12,
                      fontWeight: 600,
                    }}>
                      📝 改写基础版
                    </span>
                    <span className="muted" style={{ fontSize: 12 }}>知识库+大模型改写的基础版本</span>
                  </div>
                  <div style={{
                    fontSize: 13,
                    lineHeight: 1.7,
                    color: "var(--text)",
                    whiteSpace: "pre-wrap",
                    maxHeight: 120,
                    overflowY: "auto",
                  }}>
                    {result.rewrite_base}
                  </div>
                </div>
              )}

              {/* 版本卡片 - 4个版本：基础改写版 + 专业型 + 口语型 + 种草型 */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
                {result.versions.map((ver, idx) => {
                  const versionLabel = VERSION_LABELS[ver.style] || ver.style;
                  const colors = VERSION_COLORS[ver.style] || { border: "var(--line)", bg: "var(--panel)" };
                  const verCompliance = ver.compliance;

                  return (
                    <div
                      key={idx}
                      style={{
                        border: `2px solid ${colors.border}`,
                        borderRadius: 12,
                        padding: 16,
                        background: colors.bg,
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                        <span
                          style={{
                            background: colors.border,
                            color: "#fff",
                            padding: "4px 12px",
                            borderRadius: 12,
                            fontSize: 12,
                            fontWeight: 700,
                          }}
                        >
                          {versionLabel}
                        </span>
                        {verCompliance && (
                          <span
                            style={{
                              fontSize: 11,
                              padding: "2px 8px",
                              borderRadius: 8,
                              background: getRiskDisplay(verCompliance.risk_level).color,
                              color: "#fff",
                            }}
                          >
                            {getRiskDisplay(verCompliance.risk_level).label}
                          </span>
                        )}
                      </div>

                      <div
                        style={{
                          maxHeight: 160,
                          overflowY: "auto",
                          fontSize: 13,
                          lineHeight: 1.7,
                          color: "var(--text)",
                          whiteSpace: "pre-wrap",
                          marginBottom: 12,
                        }}
                      >
                        {ver.text}
                      </div>

                      {/* 版本合规信息 */}
                      {verCompliance && verCompliance.risk_points?.length > 0 && (
                        <div style={{
                          background: "#fff",
                          padding: 10,
                          borderRadius: 8,
                          marginBottom: 12,
                          fontSize: 12,
                        }}>
                          <div style={{ color: "var(--danger)", fontWeight: 600, marginBottom: 6 }}>
                            风险词: {verCompliance.risk_points.map(p => p.keyword).join("、")}
                          </div>
                          {verCompliance.auto_fixed_text && (
                            <div style={{ color: "var(--ok)", marginTop: 6 }}>
                              ✅ 已自动修正
                            </div>
                          )}
                        </div>
                      )}

                      <button
                        className="ghost"
                        onClick={() => handleCopyVersion(ver.text, ver.style)}
                        style={{ width: "100%", fontSize: 13 }}
                      >
                        {copiedVersions[ver.style] ? "✓ 已复制" : "📋 复制文案"}
                      </button>
                      
                      {/* 反馈按钮组 */}
                      <div style={{ marginTop: 12, display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <button
                          onClick={() => handleFeedbackSubmit(ver.text, 'adopted', ver.style)}
                          disabled={feedbackSubmitted[ver.style] || feedbackLoading}
                          style={{
                            flex: 1,
                            padding: "6px 10px",
                            fontSize: 12,
                            border: feedbackSubmitted[ver.style] ? "1px solid #4caf50" : "1px solid var(--line)",
                            borderRadius: 6,
                            background: feedbackSubmitted[ver.style] ? "#e8f5e9" : "var(--panel)",
                            color: feedbackSubmitted[ver.style] ? "#4caf50" : "var(--text)",
                            cursor: feedbackSubmitted[ver.style] || feedbackLoading ? "default" : "pointer",
                            minWidth: 70,
                          }}
                        >
                          {feedbackSubmitted[ver.style] ? "✓ 已采纳" : "👍 采纳"}
                        </button>
                        <button
                          onClick={() => setShowFeedbackPanel(showFeedbackPanel === ver.style ? null : ver.style)}
                          disabled={feedbackSubmitted[ver.style] || feedbackLoading}
                          style={{
                            flex: 1,
                            padding: "6px 10px",
                            fontSize: 12,
                            border: "1px solid var(--line)",
                            borderRadius: 6,
                            background: "var(--panel)",
                            color: "var(--text)",
                            cursor: "pointer",
                            minWidth: 70,
                          }}
                        >
                          ✏️ 修改
                        </button>
                        <button
                          onClick={() => handleFeedbackSubmit(ver.text, 'rejected', ver.style)}
                          disabled={feedbackSubmitted[ver.style] || feedbackLoading}
                          style={{
                            flex: 1,
                            padding: "6px 10px",
                            fontSize: 12,
                            border: "1px solid var(--line)",
                            borderRadius: 6,
                            background: "var(--panel)",
                            color: "var(--text)",
                            cursor: "pointer",
                            minWidth: 70,
                          }}
                        >
                          👎 拒绝
                        </button>
                      </div>
                      
                      {/* 展开反馈面板 */}
                      {showFeedbackPanel === ver.style && !feedbackSubmitted[ver.style] && (
                        <div style={{
                          marginTop: 12,
                          padding: 12,
                          background: "#f8fafc",
                          borderRadius: 8,
                          border: "1px dashed var(--line)",
                        }}>
                          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8 }}>评分（可选）</div>
                          <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
                            {[1, 2, 3, 4, 5].map(star => (
                              <button
                                key={star}
                                onClick={() => setFeedbackRating(star)}
                                style={{
                                  fontSize: 20,
                                  border: "none",
                                  background: "transparent",
                                  cursor: "pointer",
                                  opacity: feedbackRating >= star ? 1 : 0.4,
                                }}
                              >
                                ⭐
                              </button>
                            ))}
                          </div>
                          
                          <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8 }}>问题标签（可选）</div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 12 }}>
                            {availableFeedbackTags.slice(0, 6).map(tag => (
                              <button
                                key={tag}
                                onClick={() => toggleFeedbackTag(tag)}
                                style={{
                                  padding: "4px 8px",
                                  fontSize: 11,
                                  border: feedbackTags.includes(tag) ? "1px solid var(--brand)" : "1px solid var(--line)",
                                  borderRadius: 12,
                                  background: feedbackTags.includes(tag) ? "var(--brand-2)" : "var(--panel)",
                                  color: feedbackTags.includes(tag) ? "#fff" : "var(--text)",
                                  cursor: "pointer",
                                }}
                              >
                                {tag}
                              </button>
                            ))}
                          </div>
                          
                          <button
                            onClick={() => handleFeedbackSubmit(ver.text, 'modified', ver.style)}
                            disabled={feedbackLoading}
                            style={{
                              width: "100%",
                              padding: "8px 12px",
                              fontSize: 13,
                              border: "none",
                              borderRadius: 6,
                              background: "var(--brand)",
                              color: "#fff",
                              cursor: "pointer",
                            }}
                          >
                            {feedbackLoading ? "提交中..." : "确认修改后采纳"}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* 合规审核区 */}
      {result?.compliance && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16 }}>🛡️ 合规审核</h3>

          {/* 风险等级 */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
            <span className="muted">风险等级:</span>
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 16px",
                borderRadius: 20,
                background: getRiskDisplay(result.compliance.risk_level).color,
                color: "#fff",
                fontWeight: 700,
                fontSize: 14,
              }}
            >
              {getRiskDisplay(result.compliance.risk_level).icon} {getRiskDisplay(result.compliance.risk_level).label}
            </span>
          </div>

          {/* 风险点列表 */}
          {result.compliance.risk_points?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h4 style={{ fontSize: 14, marginBottom: 12, color: "var(--text)" }}>风险词列表</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {result.compliance.risk_points.map((point, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: "#fef2f2",
                      padding: 14,
                      borderRadius: 8,
                      borderLeft: "4px solid var(--danger)",
                    }}
                  >
                    <strong style={{ color: "var(--danger)", fontSize: 14 }}>
                      {point.keyword}
                      {point.source && (
                        <span className="muted" style={{ fontSize: 11, marginLeft: 8, fontWeight: 400 }}>
                          [{point.source}]
                        </span>
                      )}
                    </strong>
                    <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--text)" }}>
                      {point.reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 修改建议 */}
          {result.compliance.suggestions?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h4 style={{ fontSize: 14, marginBottom: 12, color: "var(--text)" }}>修改建议</h4>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {result.compliance.suggestions.map((sug, idx) => (
                  <li key={idx} style={{ fontSize: 13, marginBottom: 6, color: "var(--text)", lineHeight: 1.6 }}>
                    {sug}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 自动修正版本 */}
          {result.compliance.auto_fixed_text && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ fontSize: 14, marginBottom: 12, color: "var(--ok)", display: "flex", alignItems: "center", gap: 6 }}>
                ✅ 自动修正版本
              </h4>
              <div style={{
                background: "#f0fdf4",
                padding: 16,
                borderRadius: 8,
                border: "1px solid #bbf7d0",
                fontSize: 13,
                lineHeight: 1.7,
                whiteSpace: "pre-wrap",
                color: "var(--text)",
              }}>
                {result.compliance.auto_fixed_text}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 最终推荐文案区 */}
      {result?.final_text && (
        <div
          className="card"
          style={{
            background: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)",
            border: "2px solid var(--ok)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
              ⭐ 最终推荐文案
              {result.knowledge_context_used && (
                <span
                  style={{
                    background: "var(--brand-2)",
                    color: "#fff",
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 6,
                  }}
                >
                  已参考知识库
                </span>
              )}
            </h3>
          </div>

          <div
            style={{
              background: "#fff",
              padding: 20,
              borderRadius: 12,
              fontSize: 14,
              lineHeight: 1.8,
              whiteSpace: "pre-wrap",
              color: "var(--text)",
              marginBottom: 16,
              minHeight: 120,
              border: "1px solid var(--line)",
            }}
          >
            {result.final_text}
          </div>

          <button
            className="primary"
            onClick={() => handleCopy(result.final_text)}
            style={{
              width: "100%",
              padding: "14px 24px",
              fontSize: 16,
              fontWeight: 700,
            }}
          >
            {copiedFinal ? "✓ 已复制到剪贴板" : "📋 一键复制最终文案"}
          </button>
        </div>
      )}

      {/* 合规检测区域 */}
      <div style={{
        marginTop: "2rem",
        background: "#2D2520",
        borderRadius: "12px",
        padding: "1.5rem",
      }}>
        <h3 style={{ color: "#E8DDD3", marginBottom: "1rem" }}>合规检测</h3>
        <p style={{ color: "#9B8B7A", fontSize: "0.85rem", marginBottom: "1rem" }}>
          粘贴任意文案进行合规风险检测，或检测上方生成的内容
        </p>
        <textarea
          value={complianceText}
          onChange={e => setComplianceText(e.target.value)}
          placeholder="粘贴或输入要检测的文案..."
          style={{
            width: "100%",
            minHeight: "120px",
            background: "#1E1A16",
            border: "1px solid #4A3F35",
            borderRadius: "8px",
            color: "#E8DDD3",
            padding: "1rem",
            fontSize: "0.9rem",
            resize: "vertical",
          }}
        />
        <button
          onClick={handleComplianceCheck}
          disabled={!complianceText.trim() || complianceLoading}
          style={{
            marginTop: "0.75rem",
            padding: "0.6rem 1.5rem",
            background: complianceLoading ? "#666" : "#A0522D",
            color: "#FFF",
            border: "none",
            borderRadius: "8px",
            cursor: complianceLoading ? "not-allowed" : "pointer",
          }}
        >
          {complianceLoading ? "检测中..." : "开始检测"}
        </button>

        {/* 合规结果展示 */}
        {complianceResult && (
          <div style={{ marginTop: "1rem", padding: "1rem", background: "#1E1A16", borderRadius: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
              <span style={{ fontSize: "1.2rem" }}>
                {complianceResult.risk_level === "low" ? "🟢" : complianceResult.risk_level === "medium" ? "🟡" : "🔴"}
              </span>
              <span style={{ color: "#E8DDD3", fontWeight: "bold" }}>
                风险等级: {complianceResult.risk_level === "low" ? "低" : complianceResult.risk_level === "medium" ? "中" : "高"}
              </span>
              <span style={{ color: "#9B8B7A", marginLeft: "1rem" }}>
                风险分数: {complianceResult.risk_score}/100
              </span>
            </div>
            
            {complianceResult.risk_points?.length > 0 && (
              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ color: "#BFA98E", fontSize: "0.85rem", marginBottom: "0.5rem", fontWeight: 600 }}>⚠️ 检测到的风险点:</div>
                {complianceResult.risk_points.map((p: any, i: number) => (
                  <div key={i} style={{ 
                    color: "#D4C5B2", 
                    fontSize: "0.85rem", 
                    padding: "0.5rem", 
                    marginBottom: "0.5rem",
                    background: "#3A322C",
                    borderRadius: "6px",
                    borderLeft: `3px solid ${complianceResult.risk_level === 'high' ? '#f44336' : complianceResult.risk_level === 'medium' ? '#ff9800' : '#4caf50'}`
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                      <span style={{ color: "#E8A87C", fontWeight: 600 }}>{p.keyword}</span>
                      {p.source && <span style={{ color: "#9B8B7A", fontSize: "0.75rem" }}>[{p.source}]</span>}
                    </div>
                    <div style={{ color: "#D4C5B2", fontSize: "0.8rem" }}>{p.reason}</div>
                    {p.suggestion && (
                      <div style={{ color: "#81c784", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                        💡 建议: {p.suggestion}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {/* 重新生成合规版本按钮 */}
            {(complianceResult.risk_level === 'high' || complianceResult.risk_level === 'medium') && (
              <div style={{ marginBottom: "1rem" }}>
                <button
                  onClick={() => {
                    setExtraRequirements(prev => 
                      prev + (prev ? '\n' : '') + 
                      `【合规优化要求】请避免使用以下风险词汇: ${complianceResult.risk_points?.map((p: any) => p.keyword).join('、') || ''}。请使用更合规、安全的表达方式。`
                    );
                    handleGenerate();
                  }}
                  style={{
                    padding: "0.6rem 1.5rem",
                    background: "#4caf50",
                    color: "#FFF",
                    border: "none",
                    borderRadius: "8px",
                    cursor: "pointer",
                    fontSize: "0.9rem",
                    fontWeight: 600,
                  }}
                >
                  🔄 重新生成合规版本
                </button>
              </div>
            )}
            
            {complianceResult.auto_fixed_text && (
              <div>
                <div style={{ color: "#BFA98E", fontSize: "0.85rem", marginBottom: "0.5rem", fontWeight: 600 }}>✅ 自动修正版本:</div>
                <div style={{ 
                  color: "#D4C5B2", 
                  fontSize: "0.85rem", 
                  background: "#1b3a1b", 
                  padding: "0.75rem", 
                  borderRadius: "6px", 
                  whiteSpace: "pre-wrap",
                  border: "1px solid #4caf50"
                }}>
                  {complianceResult.auto_fixed_text}
                </div>
                <button
                  onClick={() => handleCopy(complianceResult.auto_fixed_text)}
                  style={{
                    marginTop: "0.5rem",
                    padding: "0.4rem 1rem",
                    background: "#2D2520",
                    color: "#D4C5B2",
                    border: "1px solid #4A3F35",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "0.8rem",
                  }}
                >
                  {copiedFinal ? "✓ 已复制" : "📋 复制修正版"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 空状态 */}
      {!generating && !result && (
        <div
          className="card"
          style={{
            textAlign: "center",
            padding: 64,
            color: "var(--muted)",
          }}
        >
          <div style={{ fontSize: 64, marginBottom: 16, opacity: 0.3 }}>✨</div>
          <p style={{ fontSize: 16 }}>选择上方配置条件后，点击"开始生成"</p>
          <p style={{ fontSize: 13, marginTop: 8 }}>AI将为您生成多版本专业文案，并自动进行合规审核</p>
        </div>
      )}
    </div>
  );
}
