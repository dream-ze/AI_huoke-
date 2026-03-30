import { useState, useEffect, useCallback } from "react";
import { getKnowledgeLibraries, mvpListKnowledge, getKnowledgeChunks, listKnowledgeByLibrary, getKnowledgeQualityRankings, getLearningSuggestions, applyWeightAdjustment, getKnowledgeGraph, getGraphStats, getTopicClusters, buildKnowledgeGraph, getRelatedKnowledgeItems, enhancedKnowledgeSearch } from "../../lib/api";
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

  // 分库检索测试工具状态
  const [testSearchQuery, setTestSearchQuery] = useState("");
  const [testSearchLibrary, setTestSearchLibrary] = useState<string>("all");
  const [testSearchResults, setTestSearchResults] = useState<any[]>([]);
  const [testSearchLoading, setTestSearchLoading] = useState(false);

  // 质量排行和学习建议状态
  const [qualityRankings, setQualityRankings] = useState<any[]>([]);
  const [qualityRankingsLoading, setQualityRankingsLoading] = useState(false);
  const [learningSuggestions, setLearningSuggestions] = useState<any[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [adjustmentLoading, setAdjustmentLoading] = useState(false);
  const [adjustmentResult, setAdjustmentResult] = useState<any>(null);
  const [showQualityPanel, setShowQualityPanel] = useState(false);

  // 知识图谱状态
  const [graphStats, setGraphStats] = useState<any>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [buildLoading, setBuildLoading] = useState(false);
  const [buildResult, setBuildResult] = useState<any>(null);
  const [topicClusters, setTopicClusters] = useState<any[]>([]);
  const [clustersLoading, setClustersLoading] = useState(false);
  const [relatedItems, setRelatedItems] = useState<any[]>([]);
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [graphSearchQuery, setGraphSearchQuery] = useState("");
  const [graphSearchResults, setGraphSearchResults] = useState<any[]>([]);
  const [graphSearchLoading, setGraphSearchLoading] = useState(false);

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
        size: pageSize,
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

  // 分库检索测试
  const handleTestSearch = async () => {
    if (!testSearchQuery.trim()) return;
    setTestSearchLoading(true);
    try {
      const results: any[] = [];
      if (testSearchLibrary === "all") {
        // 搜索所有分库
        for (const libType of Object.keys(LIBRARY_TYPES)) {
          const res = await listKnowledgeByLibrary(libType, {
            keyword: testSearchQuery,
            page: 1,
            size: 5,
          });
          if (res.items) {
            results.push(...res.items.map((item: any) => ({ ...item, library_label: LIBRARY_TYPES[libType]?.label })));
          }
        }
      } else {
        // 搜索指定分库
        const res = await listKnowledgeByLibrary(testSearchLibrary, {
          keyword: testSearchQuery,
          page: 1,
          size: 10,
        });
        if (res.items) {
          results.push(...res.items.map((item: any) => ({ ...item, library_label: LIBRARY_TYPES[testSearchLibrary]?.label })));
        }
      }
      setTestSearchResults(results);
    } catch (err) {
      console.error("检索测试失败:", err);
      setTestSearchResults([]);
    } finally {
      setTestSearchLoading(false);
    }
  };

  // 加载质量排行
  const fetchQualityRankings = useCallback(async () => {
    setQualityRankingsLoading(true);
    try {
      const data = await getKnowledgeQualityRankings(10);
      setQualityRankings(data.items || []);
    } catch (err) {
      console.error("加载质量排行失败:", err);
      setQualityRankings([]);
    } finally {
      setQualityRankingsLoading(false);
    }
  }, []);

  // 加载学习建议
  const fetchLearningSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    try {
      const data = await getLearningSuggestions();
      setLearningSuggestions(data.suggestions || []);
    } catch (err) {
      console.error("加载学习建议失败:", err);
      setLearningSuggestions([]);
    } finally {
      setSuggestionsLoading(false);
    }
  }, []);

  // 应用权重调整
  const handleApplyAdjustment = async () => {
    setAdjustmentLoading(true);
    try {
      const result = await applyWeightAdjustment();
      setAdjustmentResult(result);
      // 刷新排行
      await fetchQualityRankings();
    } catch (err) {
      console.error("权重调整失败:", err);
    } finally {
      setAdjustmentLoading(false);
    }
  };

  // 展开质量面板时加载数据
  useEffect(() => {
    if (showQualityPanel) {
      fetchQualityRankings();
      fetchLearningSuggestions();
    }
  }, [showQualityPanel, fetchQualityRankings, fetchLearningSuggestions]);

  // 知识图谱相关函数
  const fetchGraphStats = useCallback(async () => {
    setGraphLoading(true);
    try {
      const data = await getGraphStats();
      setGraphStats(data);
    } catch (err) {
      console.error("加载图谱统计失败:", err);
    } finally {
      setGraphLoading(false);
    }
  }, []);

  const handleBuildGraph = async () => {
    setBuildLoading(true);
    setBuildResult(null);
    try {
      const result = await buildKnowledgeGraph();
      setBuildResult(result);
      // 刷新统计
      await fetchGraphStats();
      await fetchClusters();
    } catch (err) {
      console.error("构建关系失败:", err);
      setBuildResult({ error: String(err) });
    } finally {
      setBuildLoading(false);
    }
  };

  const fetchClusters = useCallback(async () => {
    setClustersLoading(true);
    try {
      const data = await getTopicClusters(2);
      setTopicClusters(data.clusters || []);
    } catch (err) {
      console.error("加载主题聚类失败:", err);
      setTopicClusters([]);
    } finally {
      setClustersLoading(false);
    }
  }, []);

  const fetchRelatedItems = async (knowledgeId: number) => {
    setRelatedLoading(true);
    setSelectedNodeId(knowledgeId);
    try {
      const data = await getRelatedKnowledgeItems(knowledgeId, { limit: 10 });
      setRelatedItems(data.items || []);
    } catch (err) {
      console.error("加载关联条目失败:", err);
      setRelatedItems([]);
    } finally {
      setRelatedLoading(false);
    }
  };

  const handleGraphSearch = async () => {
    if (!graphSearchQuery.trim()) return;
    setGraphSearchLoading(true);
    try {
      const data = await enhancedKnowledgeSearch(graphSearchQuery, { top_k: 5, expand_limit: 3 });
      setGraphSearchResults(data.results || []);
    } catch (err) {
      console.error("图增强检索失败:", err);
      setGraphSearchResults([]);
    } finally {
      setGraphSearchLoading(false);
    }
  };

  // 切换到知识图谱Tab时加载数据
  useEffect(() => {
    if (activeLibrary === "__graph__") {
      fetchGraphStats();
      fetchClusters();
    }
  }, [activeLibrary, fetchGraphStats, fetchClusters]);

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
        {/* 知识图谱 Tab */}
        <button
          onClick={() => setActiveLibrary("__graph__")}
          style={{
            ...styles.tabButton,
            background: activeLibrary === "__graph__" ? "#6B5B95" : "#3A322C",
            color: activeLibrary === "__graph__" ? "#FFF" : "#D4C5B2",
            borderColor: activeLibrary === "__graph__" ? "#8B7BA5" : "#4A3F35",
          }}
        >
          <span style={styles.tabIcon}>🔗</span>
          <span>知识图谱</span>
        </button>
      </div>

      {/* 筛选栏 */}
      {activeLibrary !== "__graph__" && (
        <>
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

      {/* 分库检索测试工具 */}
      <div style={styles.testSearchContainer}>
        <h3 style={styles.testSearchTitle}>🔍 分库检索测试工具</h3>
        <div style={styles.testSearchForm}>
          <input
            type="text"
            placeholder="输入查询文本..."
            value={testSearchQuery}
            onChange={(e) => setTestSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleTestSearch()}
            style={styles.testSearchInput}
          />
          <select
            value={testSearchLibrary}
            onChange={(e) => setTestSearchLibrary(e.target.value)}
            style={styles.testSearchSelect}
          >
            <option value="all">全部分库</option>
            {Object.entries(LIBRARY_TYPES).map(([key, config]) => (
              <option key={key} value={key}>{config.label}</option>
            ))}
          </select>
          <button onClick={handleTestSearch} style={styles.testSearchButton}>
            {testSearchLoading ? "检索中..." : "检索测试"}
          </button>
        </div>
        
        {/* 检索结果 */}
        {testSearchResults.length > 0 && (
          <div style={styles.testSearchResults}>
            <div style={styles.testSearchResultHeader}>
              检索结果 ({testSearchResults.length} 条)
            </div>
            <div style={styles.testSearchResultList}>
              {testSearchResults.map((item) => (
                <div key={`${item.library_type}-${item.id}`} style={styles.testSearchResultItem}>
                  <div style={styles.testSearchResultMeta}>
                    <span style={styles.testSearchResultLibrary}>{item.library_label}</span>
                    <span style={styles.testSearchResultPlatform}>{item.platform || "-"}</span>
                  </div>
                  <div style={styles.testSearchResultTitle}>{item.title}</div>
                  <div style={styles.testSearchResultContent}>{truncate(item.content, 100)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {testSearchQuery && !testSearchLoading && testSearchResults.length === 0 && (
          <div style={styles.testSearchEmpty}>未找到匹配结果</div>
        )}
      </div>

      {/* 质量排行和学习建议面板 */}
      <div style={styles.qualityPanel}>
        <div 
          style={styles.qualityPanelHeader}
          onClick={() => setShowQualityPanel(!showQualityPanel)}
        >
          <h3 style={styles.qualityPanelTitle}>📊 知识质量分析</h3>
          <span style={styles.qualityPanelToggle}>{showQualityPanel ? "▼" : "▶"}</span>
        </div>
        
        {showQualityPanel && (
          <div style={styles.qualityPanelContent}>
            {/* 质量排行 */}
            <div style={styles.rankingSection}>
              <h4 style={styles.sectionTitle}>🏆 质量排行榜 TOP 10</h4>
              {qualityRankingsLoading ? (
                <div style={styles.loadingText}>加载中...</div>
              ) : qualityRankings.length === 0 ? (
                <div style={styles.emptyText}>暂无数据</div>
              ) : (
                <div style={styles.rankingList}>
                  {qualityRankings.map((item, idx) => (
                    <div key={item.knowledge_id} style={styles.rankingItem}>
                      <span style={styles.rankingIndex}>#{idx + 1}</span>
                      <span style={styles.rankingTitle}>{truncate(item.title, 30)}</span>
                      <span style={styles.rankingScore}>{(item.quality_score * 100).toFixed(0)}%</span>
                      <span style={styles.rankingRefs}>引用{item.reference_count}次</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* 学习建议 */}
            <div style={styles.suggestionsSection}>
              <h4 style={styles.sectionTitle}>💡 学习建议</h4>
              {suggestionsLoading ? (
                <div style={styles.loadingText}>加载中...</div>
              ) : learningSuggestions.length === 0 ? (
                <div style={styles.emptyText}>暂无建议</div>
              ) : (
                <div style={styles.suggestionsList}>
                  {learningSuggestions.slice(0, 5).map((sug, idx) => (
                    <div key={idx} style={{
                      ...styles.suggestionItem,
                      borderLeftColor: sug.priority === 'high' ? '#f44336' : sug.priority === 'medium' ? '#ff9800' : '#4caf50'
                    }}>
                      <div style={styles.suggestionHeader}>
                        <span style={{
                          ...styles.suggestionType,
                          background: sug.type === 'boost' ? '#e8f5e9' : sug.type === 'downgrade' ? '#fff3e0' : '#ffebee'
                        }}>
                          {sug.type === 'boost' ? '⬆️ 提升' : sug.type === 'downgrade' ? '⬇️ 降权' : sug.type === 'remove' ? '🗑️ 移除' : '⚙️ 调整'}
                        </span>
                        <span style={styles.suggestionTitle}>{sug.title}</span>
                      </div>
                      <div style={styles.suggestionContent}>{sug.suggestion}</div>
                      <div style={styles.suggestionReason}>{sug.reason}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* 权重调整按钮 */}
            <div style={styles.adjustmentSection}>
              <button
                onClick={handleApplyAdjustment}
                disabled={adjustmentLoading}
                style={{
                  ...styles.adjustButton,
                  opacity: adjustmentLoading ? 0.7 : 1,
                }}
              >
                {adjustmentLoading ? "调整中..." : "🔧 应用权重调整"}
              </button>
              {adjustmentResult && (
                <div style={styles.adjustmentResult}>
                  <div style={styles.adjustmentMessage}>{adjustmentResult.message}</div>
                  <div style={styles.adjustmentDetails}>
                    提升: {adjustmentResult.boosted_count} | 
                    降权: {adjustmentResult.downgraded_count} | 
                    冷标记: {adjustmentResult.cold_marked_count}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
        </>
      )}
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
  // 分库检索测试工具样式
  testSearchContainer: {
    marginTop: "32px",
    padding: "20px",
    background: "#1E1A16",
    borderRadius: "12px",
    border: "1px solid #4A3F35",
  },
  testSearchTitle: {
    margin: "0 0 16px 0",
    color: "#E8DDD3",
    fontSize: "16px",
    fontWeight: 600,
  },
  testSearchForm: {
    display: "flex",
    gap: "12px",
    flexWrap: "wrap" as const,
    marginBottom: "16px",
  },
  testSearchInput: {
    flex: 1,
    minWidth: "200px",
    padding: "10px 14px",
    borderRadius: "8px",
    border: "1px solid #4A3F35",
    background: "#2D2520",
    color: "#E8DDD3",
    fontSize: "14px",
  },
  testSearchSelect: {
    padding: "10px 14px",
    borderRadius: "8px",
    border: "1px solid #4A3F35",
    background: "#2D2520",
    color: "#E8DDD3",
    fontSize: "14px",
    minWidth: "140px",
  },
  testSearchButton: {
    padding: "10px 20px",
    borderRadius: "8px",
    border: "none",
    background: "#8B7355",
    color: "#FFF",
    fontSize: "14px",
    fontWeight: 500,
    cursor: "pointer",
  },
  testSearchResults: {
    marginTop: "16px",
    padding: "16px",
    background: "#2D2520",
    borderRadius: "8px",
  },
  testSearchResultHeader: {
    color: "#BFA98E",
    fontSize: "14px",
    marginBottom: "12px",
    paddingBottom: "8px",
    borderBottom: "1px solid #4A3F35",
  },
  testSearchResultList: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "12px",
  },
  testSearchResultItem: {
    padding: "12px",
    background: "#1E1A16",
    borderRadius: "8px",
    border: "1px solid #4A3F35",
  },
  testSearchResultMeta: {
    display: "flex",
    gap: "8px",
    marginBottom: "8px",
  },
  testSearchResultLibrary: {
    padding: "2px 8px",
    background: "#3A322C",
    color: "#E8A87C",
    fontSize: "12px",
    borderRadius: "4px",
  },
  testSearchResultPlatform: {
    padding: "2px 8px",
    background: "#3A322C",
    color: "#9B8B7A",
    fontSize: "12px",
    borderRadius: "4px",
  },
  testSearchResultTitle: {
    color: "#E8DDD3",
    fontSize: "14px",
    fontWeight: 500,
    marginBottom: "4px",
  },
  testSearchResultContent: {
    color: "#9B8B7A",
    fontSize: "13px",
    lineHeight: 1.5,
  },
  testSearchEmpty: {
    color: "#9B8B7A",
    fontSize: "14px",
    textAlign: "center" as const,
    padding: "20px",
  },
  // 质量分析面板样式
  qualityPanel: {
    marginTop: "32px",
    background: "#1E1A16",
    borderRadius: "12px",
    border: "1px solid #4A3F35",
    overflow: "hidden",
  },
  qualityPanelHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "16px 20px",
    cursor: "pointer",
    borderBottom: "1px solid #4A3F35",
  },
  qualityPanelTitle: {
    margin: 0,
    color: "#E8DDD3",
    fontSize: "16px",
    fontWeight: 600,
  },
  qualityPanelToggle: {
    color: "#9B8B7A",
    fontSize: "14px",
  },
  qualityPanelContent: {
    padding: "20px",
  },
  rankingSection: {
    marginBottom: "24px",
  },
  sectionTitle: {
    margin: "0 0 12px 0",
    color: "#BFA98E",
    fontSize: "14px",
    fontWeight: 600,
  },
  loadingText: {
    color: "#9B8B7A",
    fontSize: "13px",
    textAlign: "center",
    padding: "16px",
  },
  emptyText: {
    color: "#9B8B7A",
    fontSize: "13px",
    textAlign: "center",
    padding: "16px",
    fontStyle: "italic",
  },
  rankingList: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "8px",
  },
  rankingItem: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "10px 12px",
    background: "#2D2520",
    borderRadius: "8px",
  },
  rankingIndex: {
    color: "#8B7355",
    fontWeight: 600,
    fontSize: "12px",
    minWidth: "24px",
  },
  rankingTitle: {
    flex: 1,
    color: "#E8DDD3",
    fontSize: "13px",
  },
  rankingScore: {
    color: "#4caf50",
    fontWeight: 600,
    fontSize: "12px",
    padding: "2px 8px",
    background: "#1b3a1b",
    borderRadius: "4px",
  },
  rankingRefs: {
    color: "#9B8B7A",
    fontSize: "11px",
  },
  suggestionsSection: {
    marginBottom: "24px",
  },
  suggestionsList: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "12px",
  },
  suggestionItem: {
    padding: "12px",
    background: "#2D2520",
    borderRadius: "8px",
    borderLeft: "3px solid",
  },
  suggestionHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "8px",
  },
  suggestionType: {
    padding: "2px 8px",
    borderRadius: "4px",
    fontSize: "11px",
    color: "#E8DDD3",
  },
  suggestionTitle: {
    color: "#E8DDD3",
    fontSize: "13px",
    fontWeight: 500,
  },
  suggestionContent: {
    color: "#D4C5B2",
    fontSize: "12px",
    marginBottom: "4px",
  },
  suggestionReason: {
    color: "#9B8B7A",
    fontSize: "11px",
  },
  adjustmentSection: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "12px",
  },
  adjustButton: {
    padding: "12px 20px",
    borderRadius: "8px",
    border: "none",
    background: "#8B7355",
    color: "#FFF",
    fontSize: "14px",
    fontWeight: 500,
    cursor: "pointer",
  },
  adjustmentResult: {
    padding: "12px",
    background: "#1b3a1b",
    borderRadius: "8px",
    border: "1px solid #4caf50",
  },
  adjustmentMessage: {
    color: "#4caf50",
    fontSize: "13px",
    fontWeight: 500,
    marginBottom: "4px",
  },
  adjustmentDetails: {
    color: "#9B8B7A",
    fontSize: "12px",
  },
};
