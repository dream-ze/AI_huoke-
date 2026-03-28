import { useState, useEffect, useCallback } from "react";
import { mvpListInbox } from "../../lib/api";
import { MvpInboxItem } from "../../types";

const platformOptions = [
  { value: "", label: "全部平台" },
  { value: "小红书", label: "小红书" },
  { value: "抖音", label: "抖音" },
  { value: "知乎", label: "知乎" },
  { value: "微博", label: "微博" },
];

const statusOptions = [
  { value: "", label: "全部状态" },
  { value: "pending", label: "待处理" },
  { value: "to_material", label: "已入素材库" },
  { value: "discarded", label: "已废弃" },
];

const channelOptions = [
  { value: "", label: "全部来源" },
  { value: "collect", label: "采集" },
  { value: "manual", label: "手动导入" },
];

const riskOptions = [
  { value: "", label: "全部风险" },
  { value: "low", label: "低风险" },
  { value: "medium", label: "中风险" },
  { value: "high", label: "高风险" },
];

const duplicateOptions = [
  { value: "", label: "全部重复" },
  { value: "unique", label: "唯一" },
  { value: "suspected", label: "疑似重复" },
  { value: "duplicate", label: "重复" },
];

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${mm}-${dd} ${hh}:${min}`;
}

function truncate(text: string, len: number): string {
  if (!text) return "";
  return text.length > len ? text.slice(0, len) + "..." : text;
}

function getRiskColor(level: string): string {
  switch (level) {
    case "low": return "var(--ok)";
    case "medium": return "var(--warn)";
    case "high": return "var(--danger)";
    default: return "var(--muted)";
  }
}

function getRiskLabel(level: string): string {
  switch (level) {
    case "low": return "低";
    case "medium": return "中";
    case "high": return "高";
    default: return level;
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "pending": return "待处理";
    case "to_material": return "已入库";
    case "discarded": return "已废弃";
    default: return status;
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case "pending": return "var(--brand)";
    case "to_material": return "var(--ok)";
    case "discarded": return "var(--muted)";
    default: return "var(--text)";
  }
}

function getDuplicateLabel(status: string): string {
  switch (status) {
    case "unique": return "唯一";
    case "suspected": return "疑似重复";
    case "duplicate": return "重复";
    default: return status;
  }
}

function getChannelLabel(type: string): string {
  switch (type) {
    case "collect": return "采集";
    case "manual": return "手动导入";
    default: return type;
  }
}

export default function MvpInboxPage() {
  // 数据状态
  const [items, setItems] = useState<MvpInboxItem[]>([]);
  const [total, setTotal] = useState(0);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });

  // 筛选状态
  const [filterStatus, setFilterStatus] = useState("");
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterChannel, setFilterChannel] = useState("");
  const [filterRisk, setFilterRisk] = useState("");
  const [filterDuplicate, setFilterDuplicate] = useState("");
  const [filterKeyword, setFilterKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");

  // 显示消息
  const showMessage = useCallback((text: string, type: "success" | "error") => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: "", type: "" }), 3000);
  }, []);

  // 加载列表
  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {};
      if (filterStatus) params.status = filterStatus;
      if (filterPlatform) params.platform = filterPlatform;
      if (filterChannel) params.source_type = filterChannel;
      if (filterRisk) params.risk_level = filterRisk;
      if (filterDuplicate) params.duplicate_status = filterDuplicate;
      if (filterKeyword) params.keyword = filterKeyword;
      
      const res = await mvpListInbox(params);
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      showMessage(err.message || "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterPlatform, filterChannel, filterRisk, filterDuplicate, filterKeyword, showMessage]);

  // 监听筛选变化重新加载
  useEffect(() => {
    loadList();
  }, [loadList]);

  // 搜索处理
  const handleSearch = () => {
    setFilterKeyword(searchInput);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  // 展开/折叠处理
  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  // 操作按钮处理
  const handleToMaterial = (item: MvpInboxItem) => {
    showMessage(`已将「${truncate(item.title, 20)}」入素材库`, "success");
    // TODO: 调用实际API
  };

  const handleMarkHot = (item: MvpInboxItem) => {
    showMessage(`已标记「${truncate(item.title, 20)}」为爆款`, "success");
    // TODO: 调用实际API
  };

  const handleDiscard = (item: MvpInboxItem) => {
    showMessage(`已废弃「${truncate(item.title, 20)}」`, "success");
    // TODO: 调用实际API
  };

  return (
    <div className="page inbox-page">
      {/* 消息条 */}
      {message.text && (
        <div className={`inbox-message inbox-message--${message.type}`}>
          {message.text}
        </div>
      )}

      {/* 标题区 */}
      <div className="inbox-header">
        <h2 className="inbox-title">收件箱 - 素材筛选中心</h2>
        <span className="inbox-count">共 {total} 条</span>
      </div>

      {/* 筛选区 */}
      <div className="inbox-filter-card">
        <div className="inbox-filters">
          <select 
            className="inbox-select" 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <select 
            className="inbox-select" 
            value={filterPlatform} 
            onChange={(e) => setFilterPlatform(e.target.value)}
          >
            {platformOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <select 
            className="inbox-select" 
            value={filterChannel} 
            onChange={(e) => setFilterChannel(e.target.value)}
          >
            {channelOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <select 
            className="inbox-select" 
            value={filterRisk} 
            onChange={(e) => setFilterRisk(e.target.value)}
          >
            {riskOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <select 
            className="inbox-select" 
            value={filterDuplicate} 
            onChange={(e) => setFilterDuplicate(e.target.value)}
          >
            {duplicateOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <div className="inbox-search-group">
            <input
              type="text"
              className="inbox-search-input"
              placeholder="关键词搜索..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button className="inbox-search-btn" onClick={handleSearch}>
              搜索
            </button>
          </div>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="inbox-main">
        <div className="inbox-list-panel">
          {loading ? (
            <div className="inbox-loading">加载中...</div>
          ) : items.length === 0 ? (
            <div className="inbox-empty">
              <div className="inbox-empty-icon">📥</div>
              <div className="inbox-empty-title">暂无收件箱内容</div>
              <div className="inbox-empty-desc">请前往采集中心导入内容，或手动添加素材</div>
            </div>
          ) : (
            <div className="inbox-card-list">
              {items.map((item) => (
                <div
                  key={item.id}
                  className={`inbox-card ${expandedId === item.id ? "inbox-card-expanded" : ""}`}
                  onClick={() => toggleExpand(item.id)}
                >
                  {/* 卡片头部 */}
                  <div className="inbox-card-header">
                    <div className="inbox-card-main">
                      <h4 className="inbox-card-title">{item.title || "无标题"}</h4>
                      <div className="inbox-card-meta">
                        <span className="inbox-card-platform">{item.platform}</span>
                        <span className="inbox-card-sep">·</span>
                        <span className="inbox-card-source">{getChannelLabel(item.source_type)}</span>
                        {item.author && (
                          <>
                            <span className="inbox-card-sep">·</span>
                            <span className="inbox-card-author">{item.author}</span>
                          </>
                        )}
                        <span className="inbox-card-sep">·</span>
                        <span className="inbox-card-time">{formatDate(item.created_at)}</span>
                      </div>
                    </div>
                    <div className="inbox-card-badges">
                      <span 
                        className="inbox-risk-tag" 
                        style={{ backgroundColor: getRiskColor(item.risk_level) }}
                      >
                        {getRiskLabel(item.risk_level)}
                      </span>
                      <span 
                        className="inbox-status-tag" 
                        style={{ color: getStatusColor(item.biz_status) }}
                      >
                        {getStatusLabel(item.biz_status)}
                      </span>
                      {item.score !== undefined && (
                        <span className="inbox-score-tag">{item.score.toFixed(1)}分</span>
                      )}
                    </div>
                  </div>

                  {/* 内容摘要（始终显示） */}
                  <div className="inbox-card-summary">
                    {truncate(item.content, 200)}
                  </div>

                  {/* 展开后的完整内容 */}
                  {expandedId === item.id && (
                    <div className="inbox-card-expanded-content" onClick={(e) => e.stopPropagation()}>
                      {/* 完整内容 */}
                      <div className="inbox-card-full-content">
                        {item.content || "无内容"}
                      </div>

                      {/* 附加信息 */}
                      <div className="inbox-card-extra">
                        {item.keyword && (
                          <div className="inbox-card-keyword">
                            关键词：<span className="inbox-keyword-tag">{item.keyword}</span>
                          </div>
                        )}
                        {item.source_url && (
                          <div className="inbox-card-link">
                            <a href={item.source_url} target="_blank" rel="noopener noreferrer">
                              查看原文链接 ↗
                            </a>
                          </div>
                        )}
                        <div className="inbox-card-analysis">
                          <span>重复状态：{getDuplicateLabel(item.duplicate_status)}</span>
                          <span className="inbox-card-analysis-sep">|</span>
                          <span>技术状态：{item.tech_status || "-"}</span>
                        </div>
                      </div>

                      {/* 操作按钮 */}
                      <div className="inbox-card-actions">
                        <button 
                          className="inbox-action-btn inbox-action-primary"
                          onClick={() => handleToMaterial(item)}
                        >
                          入素材库
                        </button>
                        <button 
                          className="inbox-action-btn inbox-action-secondary"
                          onClick={() => handleMarkHot(item)}
                        >
                          标记爆款
                        </button>
                        <button 
                          className="inbox-action-btn inbox-action-danger"
                          onClick={() => handleDiscard(item)}
                        >
                          废弃
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .inbox-page {
          padding: 24px;
          min-height: 100%;
        }

        /* 消息条 */
        .inbox-message {
          position: fixed;
          top: 20px;
          left: 50%;
          transform: translateX(-50%);
          padding: 12px 24px;
          border-radius: var(--radius);
          font-weight: 500;
          z-index: 1000;
          animation: inbox-message-in 0.3s ease;
        }
        .inbox-message--success {
          background: var(--ok);
          color: white;
        }
        .inbox-message--error {
          background: var(--danger);
          color: white;
        }
        @keyframes inbox-message-in {
          from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }

        /* 标题区 */
        .inbox-header {
          display: flex;
          align-items: baseline;
          gap: 16px;
          margin-bottom: 20px;
        }
        .inbox-title {
          font-size: 24px;
          font-weight: 700;
          color: var(--text);
        }
        .inbox-count {
          color: var(--muted);
          font-size: 14px;
        }

        /* 筛选区 */
        .inbox-filter-card {
          background: var(--panel);
          border-radius: var(--radius);
          padding: 16px 20px;
          margin-bottom: 20px;
          border: 1px solid var(--line);
        }
        .inbox-filters {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          align-items: center;
        }
        .inbox-select {
          padding: 8px 12px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: white;
          color: var(--text);
          font-size: 14px;
          min-width: 120px;
          cursor: pointer;
        }
        .inbox-select:focus {
          outline: none;
          border-color: var(--brand);
        }
        .inbox-search-group {
          display: flex;
          gap: 8px;
          flex: 1;
          min-width: 200px;
          max-width: 300px;
        }
        .inbox-search-input {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid var(--line);
          border-radius: 8px;
          font-size: 14px;
        }
        .inbox-search-input:focus {
          outline: none;
          border-color: var(--brand);
        }
        .inbox-search-btn {
          padding: 8px 16px;
          background: var(--brand);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          cursor: pointer;
          transition: background 0.2s;
        }
        .inbox-search-btn:hover {
          background: color-mix(in srgb, var(--brand) 85%, black);
        }

        /* 主内容区 */
        .inbox-main {
          min-height: calc(100vh - 280px);
        }

        /* 列表面板 */
        .inbox-list-panel {
          background: var(--panel);
          border-radius: var(--radius);
          border: 1px solid var(--line);
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        .inbox-loading {
          padding: 60px;
          text-align: center;
          color: var(--muted);
          font-size: 16px;
        }
        .inbox-empty {
          padding: 80px 40px;
          text-align: center;
        }
        .inbox-empty-icon {
          font-size: 64px;
          margin-bottom: 16px;
        }
        .inbox-empty-title {
          font-size: 20px;
          font-weight: 600;
          color: var(--text);
          margin-bottom: 8px;
        }
        .inbox-empty-desc {
          color: var(--muted);
          font-size: 14px;
        }

        /* 卡片列表 */
        .inbox-card-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 16px;
        }
        .inbox-card {
          background: white;
          border-radius: 12px;
          border: 1px solid var(--line);
          padding: 16px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .inbox-card:hover {
          border-color: var(--brand);
          box-shadow: 0 2px 8px rgba(182, 61, 31, 0.08);
        }
        .inbox-card-expanded {
          border-color: var(--brand);
          box-shadow: 0 4px 16px rgba(182, 61, 31, 0.12);
        }
        .inbox-card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
          margin-bottom: 12px;
        }
        .inbox-card-main {
          flex: 1;
          min-width: 0;
        }
        .inbox-card-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--text);
          margin: 0 0 8px 0;
          line-height: 1.4;
        }
        .inbox-card-meta {
          display: flex;
          align-items: center;
          gap: 6px;
          color: var(--muted);
          font-size: 13px;
          flex-wrap: wrap;
        }
        .inbox-card-sep {
          color: var(--line);
        }
        .inbox-card-platform {
          color: var(--brand);
          font-weight: 500;
        }
        .inbox-card-source {
          color: var(--brand-2);
        }
        .inbox-card-author {
          color: var(--text);
        }
        .inbox-card-badges {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
        }
        .inbox-risk-tag {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          color: white;
          font-size: 12px;
          font-weight: 500;
        }
        .inbox-status-tag {
          font-weight: 500;
          font-size: 12px;
        }
        .inbox-score-tag {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          background: var(--bg-2);
          color: var(--text);
          font-size: 12px;
          font-weight: 500;
        }
        .inbox-card-summary {
          color: var(--muted);
          font-size: 14px;
          line-height: 1.6;
          white-space: pre-wrap;
          word-break: break-word;
        }

        /* 展开内容 */
        .inbox-card-expanded-content {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid var(--line);
          animation: inbox-expand-in 0.2s ease;
        }
        @keyframes inbox-expand-in {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .inbox-card-full-content {
          color: var(--text);
          font-size: 14px;
          line-height: 1.8;
          white-space: pre-wrap;
          word-break: break-word;
          margin-bottom: 16px;
          max-height: 400px;
          overflow-y: auto;
          padding: 12px;
          background: var(--bg-2);
          border-radius: 8px;
        }
        .inbox-card-extra {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 16px;
          font-size: 13px;
          color: var(--muted);
        }
        .inbox-card-keyword {
          color: var(--muted);
        }
        .inbox-keyword-tag {
          display: inline-block;
          padding: 2px 8px;
          background: var(--bg-2);
          border-radius: 4px;
          color: var(--text);
          margin-left: 4px;
        }
        .inbox-card-link a {
          color: var(--brand-2);
          text-decoration: none;
        }
        .inbox-card-link a:hover {
          text-decoration: underline;
        }
        .inbox-card-analysis {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .inbox-card-analysis-sep {
          color: var(--line);
        }
        .inbox-card-actions {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        /* 操作按钮 */
        .inbox-action-btn {
          padding: 10px 20px;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          border: none;
          transition: all 0.2s;
          text-align: center;
        }
        .inbox-action-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .inbox-action-primary {
          background: var(--brand);
          color: white;
        }
        .inbox-action-primary:hover:not(:disabled) {
          background: color-mix(in srgb, var(--brand) 85%, black);
        }
        .inbox-action-secondary {
          background: var(--brand-2);
          color: white;
        }
        .inbox-action-secondary:hover:not(:disabled) {
          background: color-mix(in srgb, var(--brand-2) 85%, black);
        }
        .inbox-action-danger {
          background: transparent;
          color: var(--danger);
          border: 1px solid var(--danger);
        }
        .inbox-action-danger:hover:not(:disabled) {
          background: rgba(161, 29, 47, 0.08);
        }
      `}</style>
    </div>
  );
}
