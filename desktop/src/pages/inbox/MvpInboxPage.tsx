import { useState, useEffect, useCallback } from "react";
import { inboxApi } from "../../api/inboxApi";
import { RawContentInboxItem, InboxListParams } from "../../types";

// ========== 常量定义 ==========

const PLATFORM_OPTIONS = [
  { value: "", label: "全部平台" },
  { value: "xiaohongshu", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
  { value: "weibo", label: "微博" },
  { value: "wechat", label: "微信" },
];

const CLEAN_STATUS_OPTIONS = [
  { value: "", label: "全部清洗" },
  { value: "pending", label: "待清洗" },
  { value: "cleaned", label: "已清洗" },
  { value: "failed", label: "清洗失败" },
];

const QUALITY_STATUS_OPTIONS = [
  { value: "", label: "全部质量" },
  { value: "pending", label: "待评估" },
  { value: "good", label: "优质" },
  { value: "normal", label: "普通" },
  { value: "low", label: "低质" },
];

const RISK_STATUS_OPTIONS = [
  { value: "", label: "全部风险" },
  { value: "normal", label: "无风险" },
  { value: "low_risk", label: "低风险" },
  { value: "high_risk", label: "高风险" },
];

const MATERIAL_STATUS_OPTIONS = [
  { value: "", label: "全部素材" },
  { value: "not_in", label: "未入库" },
  { value: "in_material", label: "已入库" },
  { value: "ignored", label: "已忽略" },
];

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

// ========== 工具函数 ==========

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${mm}-${dd} ${hh}:${min}`;
}

function formatNumber(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + "w";
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}

function truncate(text: string, len: number): string {
  if (!text) return "";
  return text.length > len ? text.slice(0, len) + "..." : text;
}

function getPlatformLabel(platform: string): string {
  const map: Record<string, string> = {
    xiaohongshu: "小红书",
    douyin: "抖音",
    zhihu: "知乎",
    weibo: "微博",
    wechat: "微信",
  };
  return map[platform] || platform;
}

// ========== 状态标签组件 ==========

interface StatusTagProps {
  type: "clean" | "quality" | "risk" | "material";
  status: string;
}

function StatusTag({ type, status }: StatusTagProps) {
  const getStyle = (): { bg: string; color: string; label: string } => {
    switch (type) {
      case "clean":
        switch (status) {
          case "pending": return { bg: "#f0f0f0", color: "#666", label: "待清洗" };
          case "cleaned": return { bg: "#e6f7ed", color: "#2c7a47", label: "已清洗" };
          case "failed": return { bg: "#ffeaea", color: "#a11d2f", label: "清洗失败" };
          default: return { bg: "#f0f0f0", color: "#666", label: status };
        }
      case "quality":
        switch (status) {
          case "pending": return { bg: "#f0f0f0", color: "#666", label: "待评估" };
          case "good": return { bg: "#e6f7ed", color: "#2c7a47", label: "优质" };
          case "normal": return { bg: "#e6f4ff", color: "#0f6d7a", label: "普通" };
          case "low": return { bg: "#fff3e0", color: "#b05a05", label: "低质" };
          default: return { bg: "#f0f0f0", color: "#666", label: status };
        }
      case "risk":
        switch (status) {
          case "normal": return { bg: "#e6f7ed", color: "#2c7a47", label: "无风险" };
          case "low_risk": return { bg: "#fffbe6", color: "#b05a05", label: "低风险" };
          case "high_risk": return { bg: "#ffeaea", color: "#a11d2f", label: "高风险" };
          default: return { bg: "#f0f0f0", color: "#666", label: status };
        }
      case "material":
        switch (status) {
          case "not_in": return { bg: "#f0f0f0", color: "#666", label: "未入库" };
          case "in_material": return { bg: "#e6f7ed", color: "#2c7a47", label: "已入库" };
          case "ignored": return { bg: "#f0f0f0", color: "#999", label: "已忽略" };
          default: return { bg: "#f0f0f0", color: "#666", label: status };
        }
      default:
        return { bg: "#f0f0f0", color: "#666", label: status };
    }
  };
  const { bg, color, label } = getStyle();
  const isStrikethrough = type === "material" && status === "ignored";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: "4px",
        backgroundColor: bg,
        color: color,
        fontSize: "12px",
        fontWeight: 500,
        textDecoration: isStrikethrough ? "line-through" : "none",
      }}
    >
      {label}
    </span>
  );
}

// ========== 主组件 ==========

export default function MvpInboxPage() {
  // 数据状态
  const [items, setItems] = useState<RawContentInboxItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // 筛选状态
  const [filters, setFilters] = useState<InboxListParams>({
    page: 1,
    size: 20,
    platform: "",
    clean_status: "",
    quality_status: "",
    risk_status: "",
    material_status: "",
    keyword: "",
  });
  const [keywordInput, setKeywordInput] = useState("");

  // 选择状态
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  // 操作中状态
  const [operating, setOperating] = useState<string | null>(null);

  // 显示消息
  const showMessage = useCallback((text: string, type: "success" | "error") => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  }, []);

  // 加载列表
  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const params: InboxListParams = { ...filters };
      // 清理空值
      Object.keys(params).forEach((key) => {
        const k = key as keyof InboxListParams;
        if (params[k] === "" || params[k] === undefined) {
          delete params[k];
        }
      });
      const res = await inboxApi.list(params);
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      showMessage(err.message || "加载失败", "error");
    } finally {
      setLoading(false);
    }
  }, [filters, showMessage]);

  // 筛选变化时重新加载
  useEffect(() => {
    loadList();
    setSelectedIds(new Set());
  }, [filters, loadList]);

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((item) => item.id)));
    }
  };

  // 切换单条选择
  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  // 切换展开
  const toggleExpand = (id: number) => {
    const newSet = new Set(expandedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setExpandedIds(newSet);
  };

  // 执行操作
  const executeOperation = async (
    opName: string,
    opFn: () => Promise<{ success: boolean; message?: string }>,
    successMsg: string
  ) => {
    setOperating(opName);
    try {
      const result = await opFn();
      if (result.success) {
        showMessage(successMsg, "success");
        loadList();
      } else {
        showMessage(result.message || "操作失败", "error");
      }
    } catch (err: any) {
      showMessage(err.message || "操作失败", "error");
    } finally {
      setOperating(null);
    }
  };

  // 批量操作
  const handleBatchClean = () => {
    if (selectedIds.size === 0) {
      showMessage("请先选择条目", "error");
      return;
    }
    executeOperation(
      "batchClean",
      () => inboxApi.batchClean(Array.from(selectedIds)),
      `已批量清洗 ${selectedIds.size} 条`
    );
  };

  const handleBatchScreen = () => {
    if (selectedIds.size === 0) {
      showMessage("请先选择条目", "error");
      return;
    }
    executeOperation(
      "batchScreen",
      () => inboxApi.batchScreen(Array.from(selectedIds)),
      `已批量质量筛选 ${selectedIds.size} 条`
    );
  };

  const handleBatchToMaterial = () => {
    if (selectedIds.size === 0) {
      showMessage("请先选择条目", "error");
      return;
    }
    executeOperation(
      "batchToMaterial",
      () => inboxApi.batchToMaterial(Array.from(selectedIds)),
      `已批量入素材库 ${selectedIds.size} 条`
    );
  };

  const handleBatchIgnore = () => {
    if (selectedIds.size === 0) {
      showMessage("请先选择条目", "error");
      return;
    }
    executeOperation(
      "batchIgnore",
      () => inboxApi.batchIgnore(Array.from(selectedIds)),
      `已批量忽略 ${selectedIds.size} 条`
    );
  };

  // 单条操作
  const handleClean = (id: number) => {
    executeOperation(`clean-${id}`, () => inboxApi.clean(id), "清洗完成");
  };

  const handleScreen = (id: number) => {
    executeOperation(`screen-${id}`, () => inboxApi.screen(id), "质量筛选完成");
  };

  const handleToMaterial = (id: number) => {
    executeOperation(`toMaterial-${id}`, () => inboxApi.toMaterial(id), "已入素材库");
  };

  const handleIgnore = (id: number) => {
    executeOperation(`ignore-${id}`, () => inboxApi.ignore(id), "已忽略");
  };

  // 搜索处理
  const handleSearch = () => {
    setFilters((prev) => ({ ...prev, page: 1, keyword: keywordInput }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  // 更新筛选条件
  const updateFilter = (key: keyof InboxListParams, value: string) => {
    setFilters((prev) => ({ ...prev, page: 1, [key]: value }));
  };

  // 分页
  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
  };

  const handleSizeChange = (newSize: number) => {
    setFilters((prev) => ({ ...prev, page: 1, size: newSize }));
  };

  // 计算分页
  const totalPages = Math.ceil(total / (filters.size || 20));
  const currentPage = filters.page || 1;

  return (
    <div className="page inbox-page">
      {/* 消息条 */}
      {message && (
        <div
          style={{
            position: "fixed",
            top: 20,
            left: "50%",
            transform: "translateX(-50%)",
            padding: "12px 24px",
            borderRadius: "var(--radius)",
            fontWeight: 500,
            zIndex: 1000,
            background: message.type === "success" ? "var(--ok)" : "var(--danger)",
            color: "white",
            animation: "inbox-message-in 0.3s ease",
          }}
        >
          {message.text}
        </div>
      )}

      {/* 标题区 */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: "var(--text)", marginBottom: 4 }}>
          原始内容池（收件箱）
        </h2>
        <p style={{ color: "var(--muted)", fontSize: 14, margin: 0 }}>
          采集后内容的原始缓冲池，仅用于浏览与筛选
        </p>
      </div>

      {/* 筛选区域 */}
      <div
        style={{
          background: "var(--panel)",
          borderRadius: "var(--radius)",
          padding: "16px 20px",
          marginBottom: 16,
          border: "1px solid var(--line)",
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            alignItems: "center",
          }}
        >
          <select
            style={selectStyle}
            value={filters.platform || ""}
            onChange={(e) => updateFilter("platform", e.target.value)}
          >
            {PLATFORM_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <select
            style={selectStyle}
            value={filters.clean_status || ""}
            onChange={(e) => updateFilter("clean_status", e.target.value)}
          >
            {CLEAN_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <select
            style={selectStyle}
            value={filters.quality_status || ""}
            onChange={(e) => updateFilter("quality_status", e.target.value)}
          >
            {QUALITY_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <select
            style={selectStyle}
            value={filters.risk_status || ""}
            onChange={(e) => updateFilter("risk_status", e.target.value)}
          >
            {RISK_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <select
            style={selectStyle}
            value={filters.material_status || ""}
            onChange={(e) => updateFilter("material_status", e.target.value)}
          >
            {MATERIAL_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <div style={{ display: "flex", gap: 8, flex: 1, minWidth: 200, maxWidth: 300 }}>
            <input
              type="text"
              placeholder="关键词搜索..."
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{ ...inputStyle, flex: 1 }}
            />
            <button style={searchBtnStyle} onClick={handleSearch}>
              搜索
            </button>
          </div>
        </div>
      </div>

      {/* 批量操作栏 */}
      <div
        style={{
          background: "var(--panel)",
          borderRadius: "var(--radius)",
          padding: "12px 20px",
          marginBottom: 16,
          border: "1px solid var(--line)",
          display: "flex",
          alignItems: "center",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <label
          style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontWeight: 500 }}
        >
          <input
            type="checkbox"
            checked={selectedIds.size === items.length && items.length > 0}
            onChange={handleSelectAll}
            style={{ width: 18, height: 18, cursor: "pointer" }}
          />
          全选
        </label>
        <span style={{ color: "var(--muted)", fontSize: 14 }}>
          已选 {selectedIds.size} 条 / 共 {total} 条
        </span>
        <div style={{ display: "flex", gap: 8, marginLeft: "auto" }}>
          <button
            style={batchBtnStyle}
            onClick={handleBatchClean}
            disabled={selectedIds.size === 0 || operating === "batchClean"}
          >
            {operating === "batchClean" ? "处理中..." : "批量清洗"}
          </button>
          <button
            style={batchBtnStyle}
            onClick={handleBatchScreen}
            disabled={selectedIds.size === 0 || operating === "batchScreen"}
          >
            {operating === "batchScreen" ? "处理中..." : "批量质量筛选"}
          </button>
          <button
            style={{ ...batchBtnStyle, background: "var(--brand)", color: "white" }}
            onClick={handleBatchToMaterial}
            disabled={selectedIds.size === 0 || operating === "batchToMaterial"}
          >
            {operating === "batchToMaterial" ? "处理中..." : "批量入素材库"}
          </button>
          <button
            style={{ ...batchBtnStyle, border: "1px solid var(--danger)", color: "var(--danger)", background: "transparent" }}
            onClick={handleBatchIgnore}
            disabled={selectedIds.size === 0 || operating === "batchIgnore"}
          >
            {operating === "batchIgnore" ? "处理中..." : "批量忽略"}
          </button>
        </div>
      </div>

      {/* 主体列表 */}
      <div
        style={{
          background: "var(--panel)",
          borderRadius: "var(--radius)",
          border: "1px solid var(--line)",
          minHeight: 400,
        }}
      >
        {loading ? (
          <div style={{ padding: 60, textAlign: "center", color: "var(--muted)" }}>
            加载中...
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: "80px 40px", textAlign: "center" }}>
            <div style={{ fontSize: 64, marginBottom: 16 }}>📥</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: "var(--text)", marginBottom: 8 }}>
              暂无收件箱内容
            </div>
            <div style={{ color: "var(--muted)", fontSize: 14 }}>
              请前往采集中心导入内容
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {items.map((item) => {
              const isExpanded = expandedIds.has(item.id);
              const isSelected = selectedIds.has(item.id);
              const isOperating = operating?.includes(`-${item.id}`);

              return (
                <div
                  key={item.id}
                  style={{
                    padding: "16px 20px",
                    borderBottom: "1px solid var(--line)",
                    background: isSelected ? "rgba(182, 61, 31, 0.04)" : "transparent",
                    transition: "background 0.2s",
                  }}
                >
                  <div style={{ display: "flex", gap: 16 }}>
                    {/* 左侧 checkbox */}
                    <div style={{ paddingTop: 4 }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(item.id)}
                        style={{ width: 18, height: 18, cursor: "pointer" }}
                      />
                    </div>

                    {/* 主内容区 */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      {/* 标题 */}
                      <h4
                        style={{
                          fontSize: 16,
                          fontWeight: 600,
                          color: "var(--text)",
                          margin: "0 0 8px",
                          lineHeight: 1.4,
                        }}
                      >
                        {item.title || "无标题"}
                      </h4>

                      {/* 摘要/全文 */}
                      <div
                        style={{
                          color: "var(--muted)",
                          fontSize: 14,
                          lineHeight: 1.6,
                          marginBottom: 12,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {isExpanded
                          ? (item.content || item.content_preview || "无内容")
                          : truncate(item.content_preview || item.content || "", 200)}
                      </div>

                      {/* 展开/收起按钮 */}
                      {(item.content || (item.content_preview && item.content_preview.length > 200)) && (
                        <button
                          onClick={() => toggleExpand(item.id)}
                          style={{
                            background: "none",
                            border: "none",
                            color: "var(--brand-2)",
                            fontSize: 13,
                            cursor: "pointer",
                            padding: "4px 0",
                            marginBottom: 12,
                          }}
                        >
                          {isExpanded ? "收起" : "展开全文"}
                        </button>
                      )}

                      {/* 元信息行 */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          color: "var(--muted)",
                          fontSize: 13,
                          marginBottom: 8,
                          flexWrap: "wrap",
                        }}
                      >
                        <span style={{ color: "var(--brand)", fontWeight: 500 }}>
                          {getPlatformLabel(item.platform)}
                        </span>
                        {item.author_name && (
                          <>
                            <span style={{ color: "var(--line)" }}>|</span>
                            <span>{item.author_name}</span>
                          </>
                        )}
                        {item.publish_time && (
                          <>
                            <span style={{ color: "var(--line)" }}>|</span>
                            <span>{formatDate(item.publish_time)}</span>
                          </>
                        )}
                      </div>

                      {/* 互动数据行 */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 16,
                          fontSize: 13,
                          color: "var(--muted)",
                          marginBottom: 12,
                        }}
                      >
                        <span>👍 {formatNumber(item.like_count)}</span>
                        <span>💬 {formatNumber(item.comment_count)}</span>
                        <span>⭐ {formatNumber(item.favorite_count)}</span>
                      </div>

                      {/* 状态标签组 */}
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                        <StatusTag type="clean" status={item.clean_status} />
                        <StatusTag type="quality" status={item.quality_status} />
                        <StatusTag type="risk" status={item.risk_status} />
                        <StatusTag type="material" status={item.material_status} />
                      </div>

                      {/* 分数 */}
                      <div style={{ display: "flex", gap: 16, fontSize: 13, color: "var(--muted)" }}>
                        <span>质量分: <strong>{item.quality_score.toFixed(1)}</strong></span>
                        <span>风险分: <strong>{item.risk_score.toFixed(1)}</strong></span>
                      </div>
                    </div>

                    {/* 右侧操作按钮 */}
                    <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 100 }}>
                      <button
                        style={actionBtnStyle}
                        onClick={() => handleClean(item.id)}
                        disabled={isOperating}
                      >
                        {operating === `clean-${item.id}` ? "处理中..." : "重新清洗"}
                      </button>
                      <button
                        style={actionBtnStyle}
                        onClick={() => handleScreen(item.id)}
                        disabled={isOperating}
                      >
                        {operating === `screen-${item.id}` ? "处理中..." : "质量筛选"}
                      </button>
                      <button
                        style={{ ...actionBtnStyle, background: "var(--brand)", color: "white" }}
                        onClick={() => handleToMaterial(item.id)}
                        disabled={isOperating}
                      >
                        {operating === `toMaterial-${item.id}` ? "处理中..." : "加入素材库"}
                      </button>
                      <button
                        style={{ ...actionBtnStyle, border: "1px solid var(--danger)", color: "var(--danger)", background: "transparent" }}
                        onClick={() => handleIgnore(item.id)}
                        disabled={isOperating}
                      >
                        {operating === `ignore-${item.id}` ? "处理中..." : "忽略"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 分页 */}
      {total > 0 && (
        <div
          style={{
            marginTop: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ color: "var(--muted)", fontSize: 14 }}>每页</span>
            <select
              value={filters.size || 20}
              onChange={(e) => handleSizeChange(Number(e.target.value))}
              style={{ ...selectStyle, width: 80 }}
            >
              {PAGE_SIZE_OPTIONS.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
            <span style={{ color: "var(--muted)", fontSize: 14 }}>条</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              style={pageBtnStyle}
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
            >
              上一页
            </button>
            <span style={{ color: "var(--text)", fontSize: 14 }}>
              第 {currentPage} / {totalPages} 页
            </span>
            <button
              style={pageBtnStyle}
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
            >
              下一页
            </button>
          </div>
        </div>
      )}

      {/* 内联样式 */}
      <style>{`
        .inbox-page {
          padding: 24px;
          min-height: 100%;
        }
        @keyframes inbox-message-in {
          from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      `}</style>
    </div>
  );
}

// ========== 样式常量 ==========

const selectStyle: React.CSSProperties = {
  padding: "8px 12px",
  border: "1px solid var(--line)",
  borderRadius: 8,
  background: "white",
  color: "var(--text)",
  fontSize: 14,
  minWidth: 100,
  cursor: "pointer",
};

const inputStyle: React.CSSProperties = {
  padding: "8px 12px",
  border: "1px solid var(--line)",
  borderRadius: 8,
  fontSize: 14,
  background: "#fffdf8",
};

const searchBtnStyle: React.CSSProperties = {
  padding: "8px 16px",
  background: "var(--brand)",
  color: "white",
  border: "none",
  borderRadius: 8,
  fontSize: 14,
  fontWeight: 500,
  cursor: "pointer",
};

const batchBtnStyle: React.CSSProperties = {
  padding: "8px 16px",
  background: "var(--bg-2)",
  color: "var(--text)",
  border: "1px solid var(--line)",
  borderRadius: 8,
  fontSize: 14,
  fontWeight: 500,
  cursor: "pointer",
};

const actionBtnStyle: React.CSSProperties = {
  padding: "6px 12px",
  background: "var(--bg-2)",
  color: "var(--text)",
  border: "1px solid var(--line)",
  borderRadius: 6,
  fontSize: 12,
  fontWeight: 500,
  cursor: "pointer",
  whiteSpace: "nowrap",
};

const pageBtnStyle: React.CSSProperties = {
  padding: "6px 12px",
  background: "var(--panel)",
  color: "var(--text)",
  border: "1px solid var(--line)",
  borderRadius: 6,
  fontSize: 14,
  cursor: "pointer",
};
