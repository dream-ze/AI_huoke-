import { useState, useEffect, useCallback } from "react";
import { getKnowledgeLibraries, mvpListKnowledge, getKnowledgeChunks } from "../../lib/api";
import { KnowledgeLibraryStat, KnowledgeChunk } from "../../types";

// 分库类型配置
const LIBRARY_TYPES: Record<string, { label: string; icon: string; color: string }> = {
  hot_content: { label: "爆款内容库", icon: "🔥", color: "#E8A87C" },
  industry_phrases: { label: "行业话术库", icon: "💬", color: "#87CEEB" },
  platform_rules: { label: "平台规则库", icon: "📋", color: "#98D8C8" },
  audience_profile: { label: "人群画像库", icon: "👥", color: "#DDA0DD" },
  account_positioning: { label: "账号定位库", icon: "🎯", color: "#F0E68C" },
  prompt_templates: { label: "提示词库", icon: "🤖", color: "#B0C4DE" },
  compliance_rules: { label: "审核规则库", icon: "🛡️", color: "#F4A460" },
};

const PLATFORM_OPTIONS = [
  { value: "", label: "全部平台" },
  { value: "xiaohongshu", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
];

const TOPIC_OPTIONS = [
  { value: "", label: "全部主题" },
  { value: "loan", label: "贷款" },
  { value: "credit", label: "征信" },
  { value: "online_loan", label: "网贷" },
  { value: "housing_fund", label: "公积金" },
];

const AUDIENCE_OPTIONS = [
  { value: "", label: "全部人群" },
  { value: "bad_credit", label: "征信花" },
  { value: "high_debt", label: "负债高" },
  { value: "office_worker", label: "上班族" },
  { value: "self_employed", label: "个体户" },
];

const RISK_DISPLAY: Record<string, { icon: string; label: string; color: string }> = {
  low: { icon: "🟢", label: "低风险", color: "#4caf50" },
  medium: { icon: "🟡", label: "中风险", color: "#ff9800" },
  high: { icon: "🔴", label: "高风险", color: "#f44336" },
};

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function truncate(text: string, maxLen: number): string {
  if (!text) return "";
  return text.length > maxLen ? text.slice(0, maxLen) + "..." : text;
}

export default function KnowledgePage() {
  const [activeLibrary, setActiveLibrary] = useState<string>("hot_content");
  const [libraries, setLibraries] = useState<KnowledgeLibraryStat[]>([]);
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 筛选条件
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterTopic, setFilterTopic] = useState("");
  const [filterAudience, setFilterAudience] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");

  // 加载分库统计
  const fetchLibraries = useCallback(async () => {
    try {
      const data = await getKnowledgeLibraries();
      setLibraries(data || []);
    } catch (err) {
      console.error("加载分库统计失败:", err);
    }
  }, []);

  // 加载知识列表
  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {
        library_type: activeLibrary,
        page,
        page_size: pageSize,
      };
      if (filterPlatform) params.platform = filterPlatform;
      if (filterTopic) params.topic = filterTopic;
      if (filterAudience) params.audience = filterAudience;
      if (searchKeyword.trim()) params.keyword = searchKeyword.trim();

      const res = await mvpListKnowledge(params);
      const list = Array.isArray(res) ? res : res?.items || [];
      setItems(list);
      setTotal(res?.total ?? list.length);
    } catch (err) {
      console.error("加载知识列表失败:", err);
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [activeLibrary, filterPlatform, filterTopic, filterAudience, searchKeyword, page]);

  // 加载切块详情
  const fetchChunks = useCallback(async (knowledgeId: number) => {
    setChunksLoading(true);
    try {
      const data = await getKnowledgeChunks(knowledgeId);
      setChunks(data || []);
    } catch (err) {
      console.error("加载切块详情失败:", err);
      setChunks([]);
    } finally {
      setChunksLoading(false);
    }
  }, []);

  // 初始加载分库统计
  useEffect(() => {
    fetchLibraries();
  }, [fetchLibraries]);

  // Tab切换或筛选条件变化时重新加载列表
  useEffect(() => {
    setPage(1);
    fetchItems();
    setExpandedId(null);
    setChunks([]);
  }, [activeLibrary, filterPlatform, filterTopic, filterAudience, fetchItems]);

  // 页码变化时重新加载
  useEffect(() => {
    fetchItems();
  }, [page, fetchItems]);

  // 处理行点击展开
  const handleRowClick = async (item: any) => {
    if (expandedId === item.id) {
      setExpandedId(null);
      setChunks([]);
    } else {
      setExpandedId(item.id);
      await fetchChunks(item.id);
    }
  };

  // 处理搜索
  const handleSearch = () => {
    setPage(1);
    fetchItems();
  };

  // 获取分库数量
  const getLibraryCount = (type: string) => {
    const lib = libraries.find(l => l.library_type === type);
    return lib?.count || 0;
  };

  // 获取风险等级显示
  const getRiskDisplay = (level: string) => {
    return RISK_DISPLAY[level?.toLowerCase()] || RISK_DISPLAY.low;
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div style={styles.page}>
      {/* 页面标题 */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>知识库 - 智能知识管理</h2>
          <p style={styles.subtitle}>管理结构化知识资产，支持智能检索与内容生成</p>
        </div>
        <div style={styles.totalBadge}>
          总条目: {total}
        </div>
      </div>

      {/* 分库Tab切换 */}
      <div style={styles.tabContainer}>
        {Object.entries(LIBRARY_TYPES).map(([key, config]) => (
          <button
            key={key}
            onClick={() => setActiveLibrary(key)}
            style={{
              ...styles.tabButton,
              background: activeLibrary === key ? "#8B7355" : "#3A322C",
              color: activeLibrary === key ? "#FFF" : "#D4C5B2",
              borderColor: activeLibrary === key ? "#A0522D" : "#4A3F35",
            }}
          >
            <span style={styles.tabIcon}>{config.icon}</span>
            <span>{config.label}</span>
            <span style={styles.tabCount}>({getLibraryCount(key)})</span>
          </button>
        ))}
      </div>

      {/* 筛选栏 */}
      <div style={styles.filterBar}>
        <div style={styles.filterGroup}>
          <select
            value={filterPlatform}
            onChange={(e) => setFilterPlatform(e.target.value)}
            style={styles.select}
          >
            {PLATFORM_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select
            value={filterTopic}
            onChange={(e) => setFilterTopic(e.target.value)}
            style={styles.select}
          >
            {TOPIC_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select
            value={filterAudience}
            onChange={(e) => setFilterAudience(e.target.value)}
            style={styles.select}
          >
            {AUDIENCE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div style={styles.searchGroup}>
          <input
            type="text"
            placeholder="搜索关键词..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            style={styles.searchInput}
          />
          <button onClick={handleSearch} style={styles.searchButton}>
            🔍 搜索
          </button>
        </div>
      </div>

      {/* 分库统计卡片 */}
      <div style={styles.statsContainer}>
        {Object.entries(LIBRARY_TYPES).map(([key, config]) => (
          <div
            key={key}
            onClick={() => setActiveLibrary(key)}
            style={{
              ...styles.statCard,
              borderColor: activeLibrary === key ? config.color : "#4A3F35",
              background: activeLibrary === key ? "#3A322C" : "#2D2520",
            }}
          >
            <span style={{ ...styles.statIcon, color: config.color }}>{config.icon}</span>
            <div style={styles.statInfo}>
              <div style={styles.statLabel}>{config.label}</div>
              <div style={styles.statCount}>{getLibraryCount(key)}</div>
            </div>
          </div>
        ))}
      </div>

      {/* 列表表格 */}
      <div style={styles.tableContainer}>
        {loading ? (
          <div style={styles.loadingState}>加载中...</div>
        ) : items.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>📚</div>
            <div style={styles.emptyTitle}>暂无数据</div>
            <div style={styles.emptyDesc}>当前筛选条件下没有知识条目</div>
          </div>
        ) : (
          <>
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeader}>
                  <th style={styles.thTitle}>标题</th>
                  <th style={styles.thNormal}>平台</th>
                  <th style={styles.thNormal}>分库</th>
                  <th style={styles.thNormal}>层级</th>
                  <th style={styles.thNormal}>风险</th>
                  <th style={styles.thCount}>使用次数</th>
                  <th style={styles.thDate}>时间</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <>
                    <tr
                      key={item.id}
                      onClick={() => handleRowClick(item)}
                      style={{
                        ...styles.tableRow,
                        backgroundColor: expandedId === item.id ? "#3A322C" : "transparent",
                      }}
                    >
                      <td style={styles.tdTitle}>{truncate(item.title, 40)}</td>
                      <td style={styles.tdNormal}>{item.platform || "-"}</td>
                      <td style={styles.tdNormal}>
                        <span style={styles.libraryTag}>
                          {LIBRARY_TYPES[item.library_type]?.label || item.library_type}
                        </span>
                      </td>
                      <td style={styles.tdNormal}>{item.hierarchy || "-"}</td>
                      <td style={styles.tdNormal}>
                        <span style={{ color: getRiskDisplay(item.risk_level).color }}>
                          {getRiskDisplay(item.risk_level).icon}
                        </span>
                      </td>
                      <td style={styles.tdCount}>{item.use_count || 0}</td>
                      <td style={styles.tdDate}>{formatDate(item.created_at)}</td>
                    </tr>
                    {expandedId === item.id && (
                      <tr>
                        <td colSpan={7} style={styles.expandedCell}>
                          <div style={styles.expandedContent}>
                            <h4 style={styles.expandedTitle}>📋 内容预览</h4>
                            <div style={styles.contentSummary}>
                              <strong>摘要:</strong> {item.summary || truncate(item.content, 200)}
                            </div>
                            
                            {/* 结构化字段 */}
                            {item.structured_fields && (
                              <div style={styles.structuredFields}>
                                <div style={styles.fieldTitle}>结构化字段:</div>
                                <pre style={styles.fieldContent}>
                                  {JSON.stringify(item.structured_fields, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* 切块信息 */}
                            <div style={styles.chunksSection}>
                              <div style={styles.fieldTitle}>
                                切块详情 ({chunks.length} 个):
                              </div>
                              {chunksLoading ? (
                                <div style={styles.chunksLoading}>加载切块中...</div>
                              ) : chunks.length === 0 ? (
                                <div style={styles.noChunks}>暂无切块数据</div>
                              ) : (
                                <div style={styles.chunksList}>
                                  {chunks.map((chunk, idx) => (
                                    <div key={chunk.id} style={styles.chunkItem}>
                                      <div style={styles.chunkHeader}>
                                        <span style={styles.chunkIndex}>#{chunk.chunk_index + 1}</span>
                                        <span style={styles.chunkType}>{chunk.chunk_type}</span>
                                        <span style={styles.chunkTokens}>{chunk.token_count} tokens</span>
                                        {chunk.has_embedding && (
                                          <span style={styles.embeddingBadge}>✓ 已向量化</span>
                                        )}
                                      </div>
                                      <div style={styles.chunkContent}>
                                        {truncate(chunk.content, 150)}
                                      </div>
                                      {chunk.metadata_json && (
                                        <div style={styles.chunkMeta}>
                                          元数据: {chunk.metadata_json}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>

            {/* 分页控制 */}
            {totalPages > 1 && (
              <div style={styles.pagination}>
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  style={{
                    ...styles.pageButton,
                    opacity: page === 1 ? 0.5 : 1,
                    cursor: page === 1 ? "not-allowed" : "pointer",
                  }}
                >
                  上一页
                </button>
                <span style={styles.pageInfo}>
                  第 {page} / {totalPages} 页 (共 {total} 条)
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  style={{
                    ...styles.pageButton,
                    opacity: page === totalPages ? 0.5 : 1,
                    cursor: page === totalPages ? "not-allowed" : "pointer",
                  }}
                >
                  下一页
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    padding: "24px",
    minHeight: "calc(100vh - 48px)",
    background: "#2D2520",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "24px",
  },
  title: {
    fontSize: "24px",
    fontWeight: 700,
    color: "#E8DDD3",
    margin: "0 0 8px 0",
  },
  subtitle: {
    fontSize: "14px",
    color: "#9B8B7A",
    margin: 0,
  },
  totalBadge: {
    background: "#8B7355",
    color: "#FFF",
    padding: "8px 16px",
    borderRadius: "20px",
    fontSize: "14px",
    fontWeight: 600,
  },
  tabContainer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "12px",
    marginBottom: "24px",
  },
  tabButton: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "10px 16px",
    borderRadius: "8px",
    border: "1px solid",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: 500,
    transition: "all 0.2s ease",
  },
  tabIcon: {
    fontSize: "16px",
  },
  tabCount: {
    fontSize: "12px",
    opacity: 0.8,
  },
  filterBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "16px",
    marginBottom: "24px",
    padding: "16px",
    background: "#1E1A16",
    borderRadius: "12px",
    border: "1px solid #4A3F35",
  },
  filterGroup: {
    display: "flex",
    gap: "12px",
    flexWrap: "wrap",
  },
  select: {
    padding: "8px 12px",
    borderRadius: "6px",
    border: "1px solid #4A3F35",
    background: "#2D2520",
    color: "#E8DDD3",
    fontSize: "14px",
    minWidth: "120px",
  },
  searchGroup: {
    display: "flex",
    gap: "8px",
  },
  searchInput: {
    padding: "8px 12px",
    borderRadius: "6px",
    border: "1px solid #4A3F35",
    background: "#2D2520",
    color: "#E8DDD3",
    fontSize: "14px",
    width: "200px",
  },
  searchButton: {
    padding: "8px 16px",
    borderRadius: "6px",
    border: "none",
    background: "#A0522D",
    color: "#FFF",
    fontSize: "14px",
    cursor: "pointer",
  },
  statsContainer: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
    gap: "16px",
    marginBottom: "24px",
  },
  statCard: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "16px",
    borderRadius: "12px",
    border: "2px solid",
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
  statIcon: {
    fontSize: "24px",
  },
  statInfo: {
    display: "flex",
    flexDirection: "column",
  },
  statLabel: {
    fontSize: "12px",
    color: "#9B8B7A",
  },
  statCount: {
    fontSize: "20px",
    fontWeight: 700,
    color: "#E8DDD3",
  },
  tableContainer: {
    background: "#1E1A16",
    borderRadius: "12px",
    border: "1px solid #4A3F35",
    overflow: "hidden",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "14px",
  },
  tableHeader: {
    background: "#3A322C",
  },
  tableRow: {
    cursor: "pointer",
    transition: "background 0.15s ease",
    borderBottom: "1px solid #4A3F35",
  },
  thTitle: {
    padding: "12px 16px",
    textAlign: "left",
    color: "#BFA98E",
    fontWeight: 600,
    width: "35%",
  },
  thNormal: {
    padding: "12px 16px",
    textAlign: "left",
    color: "#BFA98E",
    fontWeight: 600,
  },
  thCount: {
    padding: "12px 16px",
    textAlign: "center",
    color: "#BFA98E",
    fontWeight: 600,
  },
  thDate: {
    padding: "12px 16px",
    textAlign: "left",
    color: "#BFA98E",
    fontWeight: 600,
    width: "100px",
  },
  tdTitle: {
    padding: "12px 16px",
    color: "#E8DDD3",
    fontWeight: 500,
  },
  tdNormal: {
    padding: "12px 16px",
    color: "#9B8B7A",
  },
  tdCount: {
    padding: "12px 16px",
    textAlign: "center",
    color: "#E8A87C",
    fontWeight: 600,
  },
  tdDate: {
    padding: "12px 16px",
    color: "#9B8B7A",
    fontSize: "12px",
  },
  libraryTag: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: "4px",
    background: "#3A322C",
    color: "#D4C5B2",
    fontSize: "12px",
  },
  expandedCell: {
    padding: 0,
    background: "#2D2520",
  },
  expandedContent: {
    padding: "20px",
    borderTop: "1px solid #4A3F35",
  },
  expandedTitle: {
    margin: "0 0 16px 0",
    color: "#E8DDD3",
    fontSize: "16px",
  },
  contentSummary: {
    color: "#D4C5B2",
    fontSize: "14px",
    lineHeight: 1.6,
    marginBottom: "16px",
    padding: "12px",
    background: "#1E1A16",
    borderRadius: "8px",
  },
  structuredFields: {
    marginBottom: "16px",
  },
  fieldTitle: {
    color: "#BFA98E",
    fontSize: "14px",
    marginBottom: "8px",
  },
  fieldContent: {
    background: "#1E1A16",
    padding: "12px",
    borderRadius: "8px",
    color: "#D4C5B2",
    fontSize: "12px",
    overflow: "auto",
    maxHeight: "150px",
    margin: 0,
  },
  chunksSection: {
    marginTop: "16px",
  },
  chunksLoading: {
    color: "#9B8B7A",
    fontSize: "14px",
    padding: "12px",
  },
  noChunks: {
    color: "#9B8B7A",
    fontSize: "14px",
    padding: "12px",
    fontStyle: "italic",
  },
  chunksList: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  chunkItem: {
    background: "#1E1A16",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #4A3F35",
  },
  chunkHeader: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "8px",
  },
  chunkIndex: {
    color: "#8B7355",
    fontWeight: 600,
    fontSize: "12px",
  },
  chunkType: {
    color: "#E8A87C",
    fontSize: "12px",
    padding: "2px 8px",
    background: "#3A322C",
    borderRadius: "4px",
  },
  chunkTokens: {
    color: "#9B8B7A",
    fontSize: "12px",
  },
  embeddingBadge: {
    color: "#4caf50",
    fontSize: "11px",
    marginLeft: "auto",
  },
  chunkContent: {
    color: "#D4C5B2",
    fontSize: "13px",
    lineHeight: 1.5,
  },
  chunkMeta: {
    color: "#9B8B7A",
    fontSize: "11px",
    marginTop: "8px",
    fontStyle: "italic",
  },
  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "16px",
    padding: "16px",
    borderTop: "1px solid #4A3F35",
  },
  pageButton: {
    padding: "8px 16px",
    borderRadius: "6px",
    border: "1px solid #4A3F35",
    background: "#3A322C",
    color: "#E8DDD3",
    cursor: "pointer",
    fontSize: "14px",
  },
  pageInfo: {
    color: "#9B8B7A",
    fontSize: "14px",
  },
  loadingState: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "60px",
    color: "#9B8B7A",
    fontSize: "14px",
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "60px",
    textAlign: "center",
  },
  emptyIcon: {
    fontSize: "64px",
    marginBottom: "16px",
  },
  emptyTitle: {
    fontSize: "18px",
    fontWeight: 600,
    color: "#E8DDD3",
    marginBottom: "8px",
  },
  emptyDesc: {
    fontSize: "14px",
    color: "#9B8B7A",
  },
};
