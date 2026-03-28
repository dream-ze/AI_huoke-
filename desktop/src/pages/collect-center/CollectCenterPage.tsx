import { FormEvent, useState, useEffect, useCallback } from "react";
import { collectorSearch, getCollectorResults } from "../../lib/api";
import { CollectorResult } from "../../types";

const PLATFORMS: [string, string][] = [
  ["xiaohongshu", "小红书"],
  ["douyin", "抖音"],
  ["zhihu", "知乎"],
];

const SOURCE_TYPES: [string, string][] = [
  ["search", "搜索采集"],
  ["link", "链接导入"],
  ["manual", "手动录入"],
];

function truncate(text: string, len: number): string {
  if (!text) return "";
  return text.length > len ? text.slice(0, len) + "..." : text;
}

function getRiskColor(level?: string): string {
  switch (level) {
    case "high": return "var(--danger)";
    case "medium": return "var(--warn)";
    case "low": return "var(--ok)";
    default: return "var(--muted)";
  }
}

function getRiskLabel(level?: string): string {
  switch (level) {
    case "high": return "高";
    case "medium": return "中";
    case "low": return "低";
    default: return "-";
  }
}

function getIngestStatusStyle(status: string): { color: string; bg: string; label: string } {
  switch (status) {
    case "completed":
      return { color: "#1b5e20", bg: "#e8f5e9", label: "已入库" };
    case "processing":
      return { color: "#e65100", bg: "#fff8e1", label: "处理中" };
    case "pending":
    default:
      return { color: "#616161", bg: "#f5f5f5", label: "未入库" };
  }
}

function getPlatformLabel(platform: string): string {
  const map: Record<string, string> = {
    xiaohongshu: "小红书",
    douyin: "抖音",
    zhihu: "知乎",
  };
  return map[platform] || platform;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${mm}-${dd} ${hh}:${min}`;
}

export function CollectCenterPage() {
  // 采集表单状态
  const [platform, setPlatform] = useState("xiaohongshu");
  const [keyword, setKeyword] = useState("");
  const [count, setCount] = useState(10);
  const [fetchDetail, setFetchDetail] = useState(true); // 默认开启
  const [fetchComments, setFetchComments] = useState(false);
  const [sourceType, setSourceType] = useState("search");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState({ text: "", type: "" });

  // 采集结果列表
  const [results, setResults] = useState<CollectorResult[]>([]);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [total, setTotal] = useState(0);

  // 显示消息
  const showMessage = useCallback((text: string, type: "success" | "error") => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: "", type: "" }), 3000);
  }, []);

  // 加载采集结果列表
  const loadResults = useCallback(async () => {
    setResultsLoading(true);
    try {
      const res = await getCollectorResults({ page: 1, size: 50 });
      const list = Array.isArray(res) ? res : res?.items || [];
      setResults(list);
      setTotal(res?.total ?? list.length);
    } catch (err: any) {
      console.error("加载采集结果失败:", err);
    } finally {
      setResultsLoading(false);
    }
  }, []);

  // 初始加载
  useEffect(() => {
    loadResults();
  }, [loadResults]);

  // 提交采集
  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!keyword.trim()) return;
    setLoading(true);
    setError("");
    try {
      await collectorSearch({
        platform,
        keyword: keyword.trim(),
        count,
        fetch_detail: fetchDetail,
        fetch_comments: fetchComments,
        source_type: sourceType,
      });
      showMessage("采集任务已提交，结果将在下方列表显示", "success");
      setKeyword("");
      // 延迟一点重新加载结果
      setTimeout(() => loadResults(), 2000);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "采集失败，请稍后重试";
      setError(msg);
      showMessage(msg, "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page collect-center-page">
      {/* 消息条 */}
      {message.text && (
        <div className={`collect-message collect-message--${message.type}`}>
          {message.text}
        </div>
      )}

      <h2 style={{ marginBottom: 8 }}>采集中心</h2>
      <p className="muted" style={{ marginTop: 0, marginBottom: 24, fontSize: 13 }}>
        采集内容自动进入收件箱，系统会自动执行详情补采和入库流程。
      </p>

      {/* 采集表单 */}
      <section className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>发起采集</h3>
        <form onSubmit={onSubmit}>
          <div className="collect-form-grid">
            {/* 平台选择 */}
            <div className="collect-form-item">
              <label>平台</label>
              <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
                {PLATFORMS.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            {/* 关键词 */}
            <div className="collect-form-item" style={{ flex: 2 }}>
              <label>关键词 *</label>
              <input
                type="text"
                placeholder="输入采集关键词，如：信用卡逾期"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                required
              />
            </div>

            {/* 数量 */}
            <div className="collect-form-item">
              <label>数量</label>
              <select value={count} onChange={(e) => setCount(Number(e.target.value))}>
                {[5, 10, 20, 30, 50].map((n) => (
                  <option key={n} value={n}>{n} 条</option>
                ))}
              </select>
            </div>

            {/* 来源方式 */}
            <div className="collect-form-item">
              <label>来源方式</label>
              <select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
                {SOURCE_TYPES.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* 开关选项 */}
          <div className="collect-switches">
            <label className="collect-switch">
              <input
                type="checkbox"
                checked={fetchDetail}
                onChange={(e) => setFetchDetail(e.target.checked)}
              />
              <span className="collect-switch-slider"></span>
              <span className="collect-switch-label">采集详情</span>
              <span className="collect-switch-hint">（默认开启，获取完整内容）</span>
            </label>

            <label className="collect-switch">
              <input
                type="checkbox"
                checked={fetchComments}
                onChange={(e) => setFetchComments(e.target.checked)}
              />
              <span className="collect-switch-slider"></span>
              <span className="collect-switch-label">采集评论</span>
            </label>
          </div>

          {/* 提交按钮 */}
          <div style={{ marginTop: 16 }}>
            <button className="primary" type="submit" disabled={loading || !keyword.trim()}>
              {loading ? "采集中，请稍候..." : "开始采集"}
            </button>
          </div>
        </form>

        {error && (
          <div style={{ color: "var(--danger)", marginTop: 12, fontSize: 13 }}>{error}</div>
        )}
      </section>

      {/* 采集结果列表 */}
      <section className="card">
        <div className="collect-results-header">
          <h3>采集结果</h3>
          <span className="collect-results-count">共 {total} 条</span>
          <button 
            className="ghost" 
            onClick={loadResults} 
            disabled={resultsLoading}
            style={{ marginLeft: "auto", padding: "6px 12px", fontSize: 13 }}
          >
            {resultsLoading ? "刷新中..." : "刷新"}
          </button>
        </div>

        {resultsLoading ? (
          <div className="collect-loading">加载中...</div>
        ) : results.length === 0 ? (
          <div className="collect-empty">
            <div className="collect-empty-icon">📥</div>
            <div className="collect-empty-title">暂无采集结果</div>
            <div className="collect-empty-desc">请在上方发起采集任务</div>
          </div>
        ) : (
          <div className="collect-table-wrap">
            <table className="collect-table">
              <thead>
                <tr>
                  <th>标题</th>
                  <th>平台</th>
                  <th>作者</th>
                  <th>摘要</th>
                  <th>标签</th>
                  <th>风险等级</th>
                  <th>入库状态</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                {results.map((item) => {
                  const ingestStyle = getIngestStatusStyle(item.ingest_status);
                  return (
                    <tr key={item.id}>
                      <td className="collect-cell-title">{truncate(item.title, 30)}</td>
                      <td>{getPlatformLabel(item.platform)}</td>
                      <td>{item.author || "-"}</td>
                      <td className="collect-cell-summary">{truncate(item.summary || item.content || "", 40)}</td>
                      <td>
                        {(item.tags || []).slice(0, 2).map((tag, idx) => (
                          <span key={idx} className="collect-tag">{tag}</span>
                        ))}
                        {(item.tags || []).length > 2 && (
                          <span className="collect-tag collect-tag-more">+{(item.tags || []).length - 2}</span>
                        )}
                      </td>
                      <td>
                        <span 
                          className="collect-risk-tag" 
                          style={{ backgroundColor: getRiskColor(item.risk_level), color: "#fff" }}
                        >
                          {getRiskLabel(item.risk_level)}
                        </span>
                      </td>
                      <td>
                        <span 
                          className="collect-ingest-tag"
                          style={{ backgroundColor: ingestStyle.bg, color: ingestStyle.color }}
                        >
                          {ingestStyle.label}
                        </span>
                      </td>
                      <td>{formatDate(item.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <style>{`
        .collect-center-page {
          padding: 24px;
        }

        /* 消息条 */
        .collect-message {
          position: fixed;
          top: 20px;
          left: 50%;
          transform: translateX(-50%);
          padding: 12px 24px;
          border-radius: var(--radius);
          font-weight: 500;
          z-index: 1000;
          animation: collect-msg-in 0.3s ease;
        }
        .collect-message--success {
          background: var(--ok);
          color: white;
        }
        .collect-message--error {
          background: var(--danger);
          color: white;
        }
        @keyframes collect-msg-in {
          from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }

        /* 表单网格 */
        .collect-form-grid {
          display: flex;
          flex-wrap: wrap;
          gap: 16px;
          margin-bottom: 16px;
        }
        .collect-form-item {
          display: flex;
          flex-direction: column;
          gap: 6px;
          min-width: 120px;
          flex: 1;
        }
        .collect-form-item label {
          font-size: 13px;
          font-weight: 500;
          color: var(--text);
        }
        .collect-form-item input,
        .collect-form-item select {
          padding: 10px 12px;
          border: 1px solid var(--line);
          border-radius: 8px;
          font-size: 14px;
          background: white;
        }
        .collect-form-item input:focus,
        .collect-form-item select:focus {
          outline: none;
          border-color: var(--brand);
        }

        /* 开关样式 */
        .collect-switches {
          display: flex;
          flex-wrap: wrap;
          gap: 24px;
        }
        .collect-switch {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          user-select: none;
        }
        .collect-switch input {
          width: 0;
          height: 0;
          opacity: 0;
          position: absolute;
        }
        .collect-switch-slider {
          position: relative;
          width: 40px;
          height: 22px;
          background: var(--line);
          border-radius: 11px;
          transition: background 0.2s;
        }
        .collect-switch-slider::before {
          content: '';
          position: absolute;
          top: 2px;
          left: 2px;
          width: 18px;
          height: 18px;
          background: white;
          border-radius: 50%;
          transition: transform 0.2s;
          box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }
        .collect-switch input:checked + .collect-switch-slider {
          background: var(--brand);
        }
        .collect-switch input:checked + .collect-switch-slider::before {
          transform: translateX(18px);
        }
        .collect-switch-label {
          font-size: 14px;
          font-weight: 500;
          color: var(--text);
        }
        .collect-switch-hint {
          font-size: 12px;
          color: var(--muted);
        }

        /* 结果区域 */
        .collect-results-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }
        .collect-results-header h3 {
          margin: 0;
        }
        .collect-results-count {
          color: var(--muted);
          font-size: 13px;
        }

        .collect-loading {
          padding: 60px;
          text-align: center;
          color: var(--muted);
        }
        .collect-empty {
          padding: 60px;
          text-align: center;
        }
        .collect-empty-icon {
          font-size: 48px;
          margin-bottom: 12px;
        }
        .collect-empty-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--text);
          margin-bottom: 8px;
        }
        .collect-empty-desc {
          font-size: 13px;
          color: var(--muted);
        }

        /* 表格 */
        .collect-table-wrap {
          overflow-x: auto;
        }
        .collect-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
        }
        .collect-table th {
          padding: 12px 10px;
          text-align: left;
          font-weight: 600;
          color: var(--text);
          border-bottom: 2px solid var(--line);
          background: var(--bg-2);
          white-space: nowrap;
        }
        .collect-table td {
          padding: 12px 10px;
          border-bottom: 1px solid var(--line);
          vertical-align: top;
        }
        .collect-table tbody tr:hover {
          background: rgba(182, 61, 31, 0.04);
        }
        .collect-cell-title {
          font-weight: 500;
          color: var(--text);
          max-width: 200px;
        }
        .collect-cell-summary {
          color: var(--muted);
          max-width: 250px;
        }

        /* 标签 */
        .collect-tag {
          display: inline-block;
          padding: 2px 8px;
          background: rgba(15, 109, 122, 0.12);
          color: var(--brand-2);
          border-radius: 10px;
          font-size: 11px;
          margin-right: 4px;
        }
        .collect-tag-more {
          background: var(--bg-2);
          color: var(--muted);
        }
        .collect-risk-tag {
          display: inline-block;
          padding: 2px 10px;
          border-radius: 10px;
          font-size: 12px;
          font-weight: 500;
        }
        .collect-ingest-tag {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 10px;
          font-size: 12px;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}
