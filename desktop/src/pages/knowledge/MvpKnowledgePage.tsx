import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  mvpListKnowledge,
  mvpGetKnowledge,
  mvpSearchKnowledge,
  mvpBuildKnowledgeFromMaterial,
  getKnowledgeQualityRankings,
  getLearningSuggestions,
  applyWeightAdjustment,
  // 知识图谱 API
  buildKnowledgeGraph,
  getGraphStats,
  getKnowledgeGraph,
  getTopicClusters,
} from "../../lib/api";
import { MvpKnowledgeItem, KnowledgeQualityRankingItem, LearningSuggestionItem } from "../../types";

const PLATFORM_OPTIONS = [
  { value: "", label: "全部" },
  { value: "小红书", label: "小红书" },
  { value: "抖音", label: "抖音" },
  { value: "知乎", label: "知乎" },
  { value: "微博", label: "微博" },
];

const AUDIENCE_OPTIONS = [
  { value: "", label: "全部" },
  { value: "负债人群", label: "负债人群" },
  { value: "上班族", label: "上班族" },
  { value: "个体户/老板", label: "个体户/老板" },
  { value: "大学生", label: "大学生" },
];

const STYLE_OPTIONS = [
  { value: "", label: "全部" },
  { value: "专业型", label: "专业型" },
  { value: "口语型", label: "口语型" },
  { value: "种草型", label: "种草型" },
  { value: "避坑型", label: "避坑型" },
];

const CATEGORY_OPTIONS = [
  { value: "", label: "全部" },
  { value: "贷款知识", label: "贷款知识" },
  { value: "行业案例", label: "行业案例" },
  { value: "风险提示", label: "风险提示" },
  { value: "平台策略", label: "平台策略" },
];

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  贷款知识: { bg: "#e8f5e9", text: "#2e7d32" },
  行业案例: { bg: "#e3f2fd", text: "#1565c0" },
  风险提示: { bg: "#ffebee", text: "#c62828" },
  平台策略: { bg: "#fff3e0", text: "#e65100" },
};

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatFullDate(dateStr: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  const sec = String(d.getSeconds()).padStart(2, "0");
  return `${y}-${m}-${day} ${h}:${min}:${sec}`;
}

function truncate(text: string, maxLen: number): string {
  if (!text) return "";
  return text.length > maxLen ? text.slice(0, maxLen) + "..." : text;
}

export default function MvpKnowledgePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [items, setItems] = useState<MvpKnowledgeItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<MvpKnowledgeItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });

  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterAudience, setFilterAudience] = useState("");
  const [filterStyle, setFilterStyle] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [isSearchMode, setIsSearchMode] = useState(false);

  // 质量面板状态
  const [showQualityPanel, setShowQualityPanel] = useState(false);
  const [qualityRankings, setQualityRankings] = useState<KnowledgeQualityRankingItem[]>([]);
  const [learningSuggestions, setLearningSuggestions] = useState<LearningSuggestionItem[]>([]);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [adjustLoading, setAdjustLoading] = useState(false);
  const [suggestionStats, setSuggestionStats] = useState({
    boost_candidates: 0,
    downgrade_candidates: 0,
    remove_candidates: 0,
  });

  // 知识图谱状态
  const [activeTab, setActiveTab] = useState<'list' | 'graph'>('list');
  const [graphStats, setGraphStats] = useState<{
    node_count: number;
    edge_count: number;
    avg_degree: number;
    nodes_with_relations: number;
    nodes_with_embedding: number;
    relation_type_stats: Record<string, number>;
    connectivity_ratio: number;
  } | null>(null);
  const [graphData, setGraphData] = useState<{
    nodes: any[];
    edges: any[];
    stats: any;
  } | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [buildLoading, setBuildLoading] = useState(false);
  const [topicClusters, setTopicClusters] = useState<any[]>([]);

  const fetchList = useCallback(async () => {
    setLoading(true);
    setMessage({ text: "", type: "" });
    try {
      const params: Record<string, any> = {};
      if (filterPlatform) params.platform = filterPlatform;
      if (filterAudience) params.audience = filterAudience;
      if (filterStyle) params.style = filterStyle;
      if (filterCategory) params.category = filterCategory;

      const res = await mvpListKnowledge(params);
      const list = Array.isArray(res) ? res : res?.items || [];
      setItems(list);
      setTotal(res?.total ?? list.length);
    } catch (err: any) {
      console.error(err);
      setMessage({ text: "加载知识列表失败", type: "error" });
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [filterPlatform, filterAudience, filterStyle, filterCategory]);

  const handleSearch = useCallback(async () => {
    if (!searchKeyword.trim()) {
      setIsSearchMode(false);
      fetchList();
      return;
    }
    setLoading(true);
    setIsSearchMode(true);
    setMessage({ text: "", type: "" });
    try {
      const res = await mvpSearchKnowledge({
        query: searchKeyword.trim(),
        platform: filterPlatform || undefined,
        audience: filterAudience || undefined,
      });
      const list = Array.isArray(res) ? res : res?.items || [];
      setItems(list);
      setTotal(list.length);
    } catch (err: any) {
      console.error(err);
      setMessage({ text: "搜索知识失败", type: "error" });
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [searchKeyword, filterPlatform, filterAudience, fetchList]);

  const fetchDetail = useCallback(async (id: number) => {
    setDetailLoading(true);
    try {
      const res = await mvpGetKnowledge(id);
      setDetail(res);
    } catch (err: any) {
      console.error(err);
      setMessage({ text: "加载知识详情失败", type: "error" });
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isSearchMode) {
      fetchList();
    }
  }, [fetchList, isSearchMode]);

  useEffect(() => {
    const preselect = searchParams.get("id");
    if (preselect) {
      const id = parseInt(preselect, 10);
      if (!isNaN(id)) {
        setSelectedId(id);
        fetchDetail(id);
      }
    }
  }, [searchParams, fetchDetail]);

  const handleRowClick = (item: MvpKnowledgeItem) => {
    setSelectedId(item.id);
    fetchDetail(item.id);
  };

  const handleRebuild = async () => {
    if (!detail?.source_material_id) return;
    setMessage({ text: "", type: "" });
    try {
      await mvpBuildKnowledgeFromMaterial({ material_id: detail.source_material_id });
      setMessage({ text: "重新构建成功", type: "success" });
      fetchDetail(detail.id);
      fetchList();
    } catch (err: any) {
      console.error(err);
      setMessage({ text: "重新构建失败: " + (err?.response?.data?.detail || err.message), type: "error" });
    }
  };

  const handleGoWorkbench = () => {
    if (!detail) return;
    navigate(`/mvp-workbench?source_type=knowledge&source_id=${detail.id}`);
  };

  const handleGoMaterial = () => {
    navigate("/mvp-materials");
  };

  // 获取质量排行榜
  const fetchQualityRankings = useCallback(async () => {
    setQualityLoading(true);
    try {
      const data = await getKnowledgeQualityRankings(20, 'desc');
      setQualityRankings(data.items || []);
    } catch (err) {
      console.error('获取质量排行失败:', err);
    } finally {
      setQualityLoading(false);
    }
  }, []);

  // 获取学习建议
  const fetchLearningSuggestions = useCallback(async () => {
    try {
      const data = await getLearningSuggestions();
      setLearningSuggestions(data.suggestions || []);
      setSuggestionStats({
        boost_candidates: data.boost_candidates || 0,
        downgrade_candidates: data.downgrade_candidates || 0,
        remove_candidates: data.remove_candidates || 0,
      });
    } catch (err) {
      console.error('获取学习建议失败:', err);
    }
  }, []);

  // 应用权重调整
  const handleApplyAdjustment = async () => {
    setAdjustLoading(true);
    try {
      const result = await applyWeightAdjustment();
      setMessage({
        text: result.message || `调整完成：提升 ${result.boosted_count} 条，降权 ${result.downgraded_count} 条，冷标记 ${result.cold_marked_count} 条`,
        type: 'success',
      });
      // 刷新质量数据
      await fetchQualityRankings();
      await fetchLearningSuggestions();
    } catch (err: any) {
      setMessage({
        text: '权重调整失败: ' + (err?.response?.data?.detail || err.message),
        type: 'error',
      });
    } finally {
      setAdjustLoading(false);
    }
  };

  // 切换质量面板
  const toggleQualityPanel = () => {
    const newShow = !showQualityPanel;
    setShowQualityPanel(newShow);
    if (newShow) {
      fetchQualityRankings();
      fetchLearningSuggestions();
    }
  };

  // 获取知识图谱统计数据
  const fetchGraphStats = useCallback(async () => {
    setGraphLoading(true);
    try {
      const stats = await getGraphStats();
      setGraphStats(stats);
      // 同时获取图数据
      const data = await getKnowledgeGraph({ limit: 100 });
      setGraphData(data);
      // 获取主题聚类
      const clusters = await getTopicClusters(2);
      setTopicClusters(clusters.clusters || []);
    } catch (err) {
      console.error('获取图谱数据失败:', err);
      setMessage({ text: '获取图谱数据失败', type: 'error' });
    } finally {
      setGraphLoading(false);
    }
  }, []);

  // 构建知识图谱关系
  const handleBuildGraph = async () => {
    setBuildLoading(true);
    setMessage({ text: '', type: '' });
    try {
      const result = await buildKnowledgeGraph();
      setMessage({
        text: result.message || `构建完成: 处理 ${result.processed} 条, 创建 ${result.relations_created} 条关系`,
        type: 'success',
      });
      // 刷新图谱数据
      await fetchGraphStats();
    } catch (err: any) {
      setMessage({
        text: '构建失败: ' + (err?.response?.data?.detail || err.message),
        type: 'error',
      });
    } finally {
      setBuildLoading(false);
    }
  };

  // 切换到图谱Tab时加载数据
  useEffect(() => {
    if (activeTab === 'graph' && !graphStats) {
      fetchGraphStats();
    }
  }, [activeTab, graphStats, fetchGraphStats]);

  const getCategoryStyle = (category?: string) => {
    if (!category) return { backgroundColor: "#f5f5f5", color: "#666" };
    const c = CATEGORY_COLORS[category];
    return c ? { backgroundColor: c.bg, color: c.text } : { backgroundColor: "#f5f5f5", color: "#666" };
  };

  const renderContent = (content: string) => {
    if (!content) return null;
    const paragraphs = content.split(/\n{2,}|\r\n{2,}/);
    if (paragraphs.length <= 1) {
      return content.split(/\n|\r\n/).map((line, i) => (
        <p key={i} style={{ margin: "0 0 8px", lineHeight: 1.7 }}>{line}</p>
      ));
    }
    return paragraphs.map((para, i) => (
      <div key={i} style={{ marginBottom: 16 }}>
        {para.split(/\n|\r\n/).map((line, j) => (
          <p key={j} style={{ margin: "0 0 4px", lineHeight: 1.7 }}>{line}</p>
        ))}
      </div>
    ));
  };

  return (
    <div className="page" style={styles.page}>
      {/* 页面标题区 */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <h2 style={styles.title}>📚 知识库 - AI的大脑</h2>
        </div>
        <div style={styles.headerRight}>
          {/* Tab 切换按钮 */}
          <div style={styles.tabGroup}>
            <button
              onClick={() => setActiveTab('list')}
              style={{
                ...styles.tabBtn,
                background: activeTab === 'list' ? 'linear-gradient(90deg, var(--brand), #d45b39)' : 'var(--panel)',
                color: activeTab === 'list' ? '#fff' : 'var(--text)',
              }}
            >
              📋 知识列表
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              style={{
                ...styles.tabBtn,
                background: activeTab === 'graph' ? 'linear-gradient(90deg, var(--brand), #d45b39)' : 'var(--panel)',
                color: activeTab === 'graph' ? '#fff' : 'var(--text)',
              }}
            >
              🔗 知识图谱
            </button>
          </div>
          {activeTab === 'list' && (
            <button
              onClick={toggleQualityPanel}
              style={{
                ...styles.qualityBtn,
                background: showQualityPanel ? 'linear-gradient(90deg, var(--brand), #d45b39)' : 'var(--panel)',
                color: showQualityPanel ? '#fff' : 'var(--text)',
              }}
            >
              📊 质量面板
            </button>
          )}
          <span style={styles.totalBadge}>共 {total} 条</span>
        </div>
      </div>

      {/* 消息提示 */}
      {message.text && (
        <div style={{
          ...styles.message,
          backgroundColor: message.type === "error" ? "#ffebee" : "#e8f5e9",
          color: message.type === "error" ? "#c62828" : "#2e7d32",
        }}>
          {message.text}
        </div>
      )}

      {/* 质量面板 */}
      {activeTab === 'list' && showQualityPanel && (
        <div className="card" style={styles.qualityPanel}>
          <div style={styles.qualityPanelHeader}>
            <h3 style={styles.qualityPanelTitle}>📊 知识库质量分析</h3>
            <button
              onClick={handleApplyAdjustment}
              disabled={adjustLoading}
              style={styles.adjustBtn}
            >
              {adjustLoading ? '⏳ 调整中...' : '⚡ 应用权重调整'}
            </button>
          </div>

          {/* 建议统计 */}
          <div style={styles.suggestionStats}>
            <div style={{ ...styles.suggestionStatItem, background: '#e8f5e9' }}>
              <span style={{ ...styles.suggestionStatNumber, color: '#2e7d32' }}>
                {suggestionStats.boost_candidates}
              </span>
              <span style={styles.suggestionStatLabel}>建议提升</span>
            </div>
            <div style={{ ...styles.suggestionStatItem, background: '#fff3e0' }}>
              <span style={{ ...styles.suggestionStatNumber, color: '#e65100' }}>
                {suggestionStats.downgrade_candidates}
              </span>
              <span style={styles.suggestionStatLabel}>建议降权</span>
            </div>
            <div style={{ ...styles.suggestionStatItem, background: '#ffebee' }}>
              <span style={{ ...styles.suggestionStatNumber, color: '#c62828' }}>
                {suggestionStats.remove_candidates}
              </span>
              <span style={styles.suggestionStatLabel}>冷数据</span>
            </div>
          </div>

          {/* 学习建议列表 */}
          {learningSuggestions.length > 0 && (
            <div style={styles.suggestionsSection}>
              <h4 style={styles.sectionTitle}>💡 持续学习建议</h4>
              <div style={styles.suggestionsList}>
                {learningSuggestions.slice(0, 5).map((suggestion, idx) => (
                  <div
                    key={idx}
                    style={{
                      ...styles.suggestionItem,
                      borderLeftColor:
                        suggestion.type === 'boost' ? '#4caf50' :
                        suggestion.type === 'downgrade' ? '#ff9800' :
                        suggestion.type === 'remove' ? '#f44336' : '#2196f3',
                    }}
                  >
                    <div style={styles.suggestionHeader}>
                      <span style={{
                        ...styles.suggestionType,
                        background:
                          suggestion.type === 'boost' ? '#e8f5e9' :
                          suggestion.type === 'downgrade' ? '#fff3e0' :
                          suggestion.type === 'remove' ? '#ffebee' : '#e3f2fd',
                        color:
                          suggestion.type === 'boost' ? '#2e7d32' :
                          suggestion.type === 'downgrade' ? '#e65100' :
                          suggestion.type === 'remove' ? '#c62828' : '#1565c0',
                      }}>
                        {suggestion.type === 'boost' ? '提升' :
                         suggestion.type === 'downgrade' ? '降权' :
                         suggestion.type === 'remove' ? '冷数据' : '调整'}
                      </span>
                      <span style={{
                        ...styles.suggestionPriority,
                        background:
                          suggestion.priority === 'high' ? '#ffebee' :
                          suggestion.priority === 'medium' ? '#fff3e0' : '#f5f5f5',
                        color:
                          suggestion.priority === 'high' ? '#c62828' :
                          suggestion.priority === 'medium' ? '#e65100' : '#666',
                      }}>
                        {suggestion.priority === 'high' ? '高' :
                         suggestion.priority === 'medium' ? '中' : '低'}
                      </span>
                    </div>
                    <div style={styles.suggestionTitle}>{suggestion.title}</div>
                    <div style={styles.suggestionText}>{suggestion.suggestion}</div>
                    <div style={styles.suggestionReason}>{suggestion.reason}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 质量排行榜 */}
          <div style={styles.rankingsSection}>
            <h4 style={styles.sectionTitle}>🏆 知识质量排行 TOP20</h4>
            {qualityLoading ? (
              <div style={styles.loadingText}>加载中...</div>
            ) : qualityRankings.length === 0 ? (
              <div style={styles.emptyText}>暂无质量数据</div>
            ) : (
              <table style={styles.rankingsTable}>
                <thead>
                  <tr>
                    <th style={styles.rankingTh}>排名</th>
                    <th style={styles.rankingThTitle}>标题</th>
                    <th style={styles.rankingTh}>质量分</th>
                    <th style={styles.rankingTh}>引用</th>
                    <th style={styles.rankingTh}>权重</th>
                  </tr>
                </thead>
                <tbody>
                  {qualityRankings.map((item, idx) => (
                    <tr
                      key={item.knowledge_id}
                      style={{
                        ...styles.rankingRow,
                        background: idx < 3 ? 'rgba(255, 215, 0, 0.1)' : 'transparent',
                      }}
                    >
                      <td style={styles.rankingTd}>
                        <span style={{
                          ...styles.rankingBadge,
                          background:
                            idx === 0 ? '#ffd700' :
                            idx === 1 ? '#c0c0c0' :
                            idx === 2 ? '#cd7f32' : '#f5f5f5',
                          color: idx < 3 ? '#fff' : '#666',
                        }}>
                          {idx + 1}
                        </span>
                      </td>
                      <td style={styles.rankingTdTitle} title={item.title}>
                        {item.title.length > 30 ? item.title.slice(0, 30) + '...' : item.title}
                      </td>
                      <td style={styles.rankingTd}>
                        <span style={{
                          ...styles.qualityScore,
                          color:
                            item.quality_score >= 0.8 ? '#4caf50' :
                            item.quality_score >= 0.5 ? '#ff9800' : '#f44336',
                        }}>
                          {(item.quality_score * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td style={styles.rankingTd}>
                        <span style={styles.referenceCount}>{item.reference_count}</span>
                        {item.positive_feedback > 0 && (
                          <span style={styles.positiveBadge}>+{item.positive_feedback}</span>
                        )}
                      </td>
                      <td style={styles.rankingTd}>
                        <span style={{
                          ...styles.weightBadge,
                          background:
                            item.weight_boost >= 1.5 ? '#e8f5e9' :
                            item.weight_boost <= 0.5 ? '#ffebee' : '#f5f5f5',
                          color:
                            item.weight_boost >= 1.5 ? '#2e7d32' :
                            item.weight_boost <= 0.5 ? '#c62828' : '#666',
                        }}>
                          {item.weight_boost.toFixed(1)}x
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* 顶部筛选区 */}
      {activeTab === 'list' && (
        <div className="card" style={styles.filterCard}>
          <div style={styles.filterRow}>
          <div style={styles.filterItem}>
            <label style={styles.filterLabel}>平台</label>
            <select
              value={filterPlatform}
              onChange={(e) => { setFilterPlatform(e.target.value); setIsSearchMode(false); }}
              style={styles.select}
            >
              {PLATFORM_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div style={styles.filterItem}>
            <label style={styles.filterLabel}>人群</label>
            <select
              value={filterAudience}
              onChange={(e) => { setFilterAudience(e.target.value); setIsSearchMode(false); }}
              style={styles.select}
            >
              {AUDIENCE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div style={styles.filterItem}>
            <label style={styles.filterLabel}>风格</label>
            <select
              value={filterStyle}
              onChange={(e) => { setFilterStyle(e.target.value); setIsSearchMode(false); }}
              style={styles.select}
            >
              {STYLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div style={styles.filterItem}>
            <label style={styles.filterLabel}>分类</label>
            <select
              value={filterCategory}
              onChange={(e) => { setFilterCategory(e.target.value); setIsSearchMode(false); }}
              style={styles.select}
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div style={styles.searchGroup}>
            <input
              type="text"
              placeholder="搜索标题/内容..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              style={styles.searchInput}
            />
            <button className="primary" onClick={handleSearch} style={styles.searchBtn}>
              🔍 搜索
            </button>
          </div>
        </div>
        </div>
      )}

      {/* 主内容区 */}
      {activeTab === 'list' && (
      <div style={styles.mainContent}>
        {/* 左侧：知识条目列表 */}
        <div style={styles.listPanel}>
          {loading ? (
            <div style={styles.loadingState}>加载中...</div>
          ) : items.length === 0 ? (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>📚</div>
              <div style={styles.emptyTitle}>知识库为空</div>
              <div style={styles.emptyDesc}>
                知识需要从素材构建，请先到素材库选择素材并点击"构建知识"
              </div>
              <button className="primary" onClick={handleGoMaterial} style={{ marginTop: 16 }}>
                去素材库 →
              </button>
            </div>
          ) : (
            <table className="table" style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.thTitle}>标题/摘要</th>
                  <th style={styles.thCategory}>分类</th>
                  <th style={styles.thNormal}>平台</th>
                  <th style={styles.thNormal}>人群</th>
                  <th style={styles.thCount}>使用次数</th>
                  <th style={styles.thDate}>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => handleRowClick(item)}
                    style={{
                      ...styles.tableRow,
                      backgroundColor: selectedId === item.id ? "rgba(182, 61, 31, 0.08)" : "transparent",
                    }}
                  >
                    <td style={styles.tdTitle}>{truncate(item.title, 50)}</td>
                    <td>
                      <span style={{ ...styles.categoryTag, ...getCategoryStyle(item.category) }}>
                        {item.category || "-"}
                      </span>
                    </td>
                    <td style={styles.tdNormal}>{item.platform || "-"}</td>
                    <td style={styles.tdNormal}>{item.audience || "-"}</td>
                    <td style={styles.tdCount}>{item.use_count}</td>
                    <td style={styles.tdDate}>{formatDate(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* 右侧：知识详情面板 */}
        <div style={styles.detailPanel}>
          {detailLoading ? (
            <div style={styles.loadingState}>加载详情中...</div>
          ) : !detail ? (
            <div style={styles.detailEmpty}>
              <div style={styles.detailEmptyIcon}>📋</div>
              <div style={styles.detailEmptyText}>请选择一条知识条目查看详情</div>
            </div>
          ) : (
            <div style={styles.detailContent}>
              {/* 卡片1: 基本信息 */}
              <div style={styles.detailCard}>
                <h3 style={styles.detailTitle}>{detail.title}</h3>
                <div style={styles.detailMeta}>
                  <span style={{ ...styles.categoryTag, ...getCategoryStyle(detail.category) }}>
                    {detail.category || "未分类"}
                  </span>
                  {detail.platform && <span style={styles.metaItem}>📱 {detail.platform}</span>}
                  {detail.audience && <span style={styles.metaItem}>👥 {detail.audience}</span>}
                  {detail.style && <span style={styles.metaItem}>🎨 {detail.style}</span>}
                </div>
              </div>

              {/* 卡片2: 知识内容 */}
              <div style={styles.detailCard}>
                <h4 style={styles.cardTitle}>📝 知识内容</h4>
                <div style={styles.contentArea}>
                  {renderContent(detail.content)}
                </div>
              </div>

              {/* 卡片3: 元数据 */}
              <div style={styles.detailCard}>
                <h4 style={styles.cardTitle}>📊 元数据</h4>
                <div style={styles.metaGrid}>
                  <div style={styles.metaRow}>
                    <span style={styles.metaLabel}>来源素材ID</span>
                    <span style={styles.metaValue}>
                      {detail.source_material_id ? (
                        <a
                          href="#"
                          onClick={(e) => { e.preventDefault(); handleGoMaterial(); }}
                          style={styles.metaLink}
                        >
                          #{detail.source_material_id} 查看来源素材 →
                        </a>
                      ) : (
                        "-"
                      )}
                    </span>
                  </div>
                  <div style={styles.metaRow}>
                    <span style={styles.metaLabel}>使用次数</span>
                    <span style={styles.metaValue}>{detail.use_count} 次</span>
                  </div>
                  <div style={styles.metaRow}>
                    <span style={styles.metaLabel}>创建时间</span>
                    <span style={styles.metaValue}>{formatFullDate(detail.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* 卡片4: 操作按钮区 */}
              <div style={styles.detailCard}>
                <h4 style={styles.cardTitle}>⚡ 操作</h4>
                <div style={styles.actionButtons}>
                  <button className="primary" onClick={handleGoWorkbench} style={styles.actionBtn}>
                    ✨ 去AI工作台生成
                  </button>
                  {detail.source_material_id && (
                    <>
                      <button className="ghost" onClick={handleGoMaterial} style={styles.actionBtn}>
                        📦 查看来源素材
                      </button>
                      <button className="ghost" onClick={handleRebuild} style={styles.actionBtn}>
                        🔄 重新构建
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      )}

      {/* 知识图谱Tab内容 */}
      {activeTab === 'graph' && (
        <div className="card" style={styles.graphPanel}>
          {/* 图谱统计卡片 */}
          <div style={styles.graphStatsRow}>
            <div style={{ ...styles.graphStatCard, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <div style={styles.graphStatIcon}>📊</div>
              <div style={styles.graphStatValue}>{graphStats?.node_count || 0}</div>
              <div style={styles.graphStatLabel}>知识节点</div>
            </div>
            <div style={{ ...styles.graphStatCard, background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
              <div style={styles.graphStatIcon}>🔗</div>
              <div style={styles.graphStatValue}>{graphStats?.edge_count || 0}</div>
              <div style={styles.graphStatLabel}>关系边</div>
            </div>
            <div style={{ ...styles.graphStatCard, background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
              <div style={styles.graphStatIcon}>📈</div>
              <div style={styles.graphStatValue}>{graphStats?.avg_degree?.toFixed(2) || '0.00'}</div>
              <div style={styles.graphStatLabel}>平均度</div>
            </div>
            <div style={{ ...styles.graphStatCard, background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' }}>
              <div style={styles.graphStatIcon}>✅</div>
              <div style={styles.graphStatValue}>{((graphStats?.connectivity_ratio || 0) * 100).toFixed(0)}%</div>
              <div style={styles.graphStatLabel}>连通率</div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div style={styles.graphActions}>
            <button
              className="primary"
              onClick={handleBuildGraph}
              disabled={buildLoading}
              style={styles.buildBtn}
            >
              {buildLoading ? '⏳ 构建中...' : '🔄 构建关系'}
            </button>
            <button
              className="ghost"
              onClick={fetchGraphStats}
              disabled={graphLoading}
              style={styles.refreshBtn}
            >
              {graphLoading ? '⏳ 刷新中...' : '🔃 刷新数据'}
            </button>
          </div>

          {/* 关系类型分布 */}
          {graphStats?.relation_type_stats && Object.keys(graphStats.relation_type_stats).length > 0 && (
            <div style={styles.relationTypesSection}>
              <h4 style={styles.sectionTitle}>📊 关系类型分布</h4>
              <div style={styles.relationTypesList}>
                {Object.entries(graphStats.relation_type_stats).map(([type, count]) => (
                  <div key={type} style={styles.relationTypeItem}>
                    <span style={styles.relationTypeName}>{type}</span>
                    <span style={styles.relationTypeCount}>{count} 条</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 主题聚类 */}
          {topicClusters.length > 0 && (
            <div style={styles.clustersSection}>
              <h4 style={styles.sectionTitle}>🎯 主题聚类</h4>
              <div style={styles.clustersList}>
                {topicClusters.slice(0, 10).map((cluster, idx) => (
                  <div key={idx} style={styles.clusterItem}>
                    <div style={styles.clusterHeader}>
                      <span style={styles.clusterTopic}>{cluster.topic || '未分类'}</span>
                      <span style={styles.clusterCount}>{cluster.count} 条</span>
                    </div>
                    <div style={styles.clusterItems}>
                      {cluster.items?.slice(0, 3).map((item: any) => (
                        <span key={item.id} style={styles.clusterItemTag} title={item.title}>
                          {item.title?.length > 20 ? item.title.slice(0, 20) + '...' : item.title}
                        </span>
                      ))}
                      {cluster.count > 3 && (
                        <span style={styles.clusterMore}>+{cluster.count - 3} 更多</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 关系列表 */}
          {graphData?.edges && graphData.edges.length > 0 && (
            <div style={styles.relationsSection}>
              <h4 style={styles.sectionTitle}>🔗 最近关系 (前20条)</h4>
              <div style={styles.relationsList}>
                {graphData.edges.slice(0, 20).map((edge, idx) => {
                  const sourceNode = graphData.nodes.find(n => n.id === edge.source);
                  const targetNode = graphData.nodes.find(n => n.id === edge.target);
                  return (
                    <div key={idx} style={styles.relationItem}>
                      <div style={styles.relationNode} title={sourceNode?.title}>
                        {sourceNode?.title?.length > 15 ? sourceNode.title.slice(0, 15) + '...' : sourceNode?.title || `#${edge.source}`}
                      </div>
                      <div style={styles.relationArrow}>
                        <span style={styles.relationType}>{edge.type}</span>
                        <span style={styles.relationWeight}>{edge.weight.toFixed(2)}</span>
                      </div>
                      <div style={styles.relationNode} title={targetNode?.title}>
                        {targetNode?.title?.length > 15 ? targetNode.title.slice(0, 15) + '...' : targetNode?.title || `#${edge.target}`}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 空状态 */}
          {graphLoading ? (
            <div style={styles.loadingState}>加载图谱数据中...</div>
          ) : (
            !graphStats?.edge_count && (
              <div style={styles.emptyGraphState}>
                <div style={styles.emptyIcon}>🔗</div>
                <div style={styles.emptyTitle}>暂无图谱数据</div>
                <div style={styles.emptyDesc}>
                  点击"构建关系"按钮，系统将基于向量相似度自动发现知识条目间的关系
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
    minHeight: "calc(100vh - 48px)",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    margin: 0,
  },
  totalBadge: {
    background: "linear-gradient(90deg, var(--brand-2), #33a1b0)",
    color: "#fff",
    fontSize: 13,
    fontWeight: 600,
    padding: "6px 14px",
    borderRadius: 20,
  },
  message: {
    padding: "10px 16px",
    borderRadius: 8,
    fontSize: 14,
  },
  filterCard: {
    padding: 16,
  },
  filterRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 16,
    alignItems: "flex-end",
  },
  filterItem: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
    minWidth: 120,
  },
  filterLabel: {
    fontSize: 12,
    color: "var(--muted)",
    fontWeight: 500,
  },
  select: {
    width: 140,
    padding: "8px 10px",
    fontSize: 13,
  },
  searchGroup: {
    display: "flex",
    gap: 8,
    flex: 1,
    minWidth: 200,
    marginLeft: "auto",
  },
  searchInput: {
    flex: 1,
    minWidth: 160,
    padding: "8px 12px",
    fontSize: 13,
  },
  searchBtn: {
    whiteSpace: "nowrap",
    padding: "8px 16px",
  },
  mainContent: {
    display: "grid",
    gridTemplateColumns: "2fr 1fr",
    gap: 16,
    flex: 1,
  },
  listPanel: {
    background: "var(--panel)",
    border: "1px solid var(--line)",
    borderRadius: "var(--radius)",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  detailPanel: {
    background: "var(--panel)",
    border: "1px solid var(--line)",
    borderRadius: "var(--radius)",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  loadingState: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 60,
    color: "var(--muted)",
    fontSize: 14,
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: 60,
    textAlign: "center",
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 600,
    marginBottom: 8,
  },
  emptyDesc: {
    fontSize: 14,
    color: "var(--muted)",
    maxWidth: 280,
    lineHeight: 1.6,
  },
  table: {
    fontSize: 13,
  },
  thTitle: {
    width: "35%",
    minWidth: 200,
  },
  thCategory: {
    width: 90,
  },
  thNormal: {
    width: 70,
  },
  thCount: {
    width: 70,
    textAlign: "center",
  },
  thDate: {
    width: 100,
  },
  tableRow: {
    cursor: "pointer",
    transition: "background 0.15s ease",
  },
  tdTitle: {
    fontWeight: 500,
    color: "var(--text)",
  },
  tdNormal: {
    color: "var(--muted)",
    fontSize: 12,
  },
  tdCount: {
    textAlign: "center",
    fontWeight: 600,
    color: "var(--brand)",
  },
  tdDate: {
    color: "var(--muted)",
    fontSize: 12,
  },
  categoryTag: {
    display: "inline-block",
    padding: "3px 10px",
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 600,
  },
  detailEmpty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: 60,
    color: "var(--muted)",
    textAlign: "center",
  },
  detailEmptyIcon: {
    fontSize: 48,
    marginBottom: 12,
    opacity: 0.6,
  },
  detailEmptyText: {
    fontSize: 14,
  },
  detailContent: {
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 16,
    overflowY: "auto",
    maxHeight: "calc(100vh - 200px)",
  },
  detailCard: {
    background: "rgba(255, 255, 255, 0.6)",
    border: "1px solid var(--line)",
    borderRadius: 12,
    padding: 16,
  },
  detailTitle: {
    fontSize: 18,
    fontWeight: 700,
    margin: "0 0 12px",
    lineHeight: 1.4,
  },
  detailMeta: {
    display: "flex",
    flexWrap: "wrap",
    gap: 10,
    alignItems: "center",
  },
  metaItem: {
    fontSize: 12,
    color: "var(--muted)",
    background: "rgba(0,0,0,0.04)",
    padding: "4px 10px",
    borderRadius: 6,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: 600,
    margin: "0 0 12px",
    color: "var(--text)",
  },
  contentArea: {
    background: "rgba(243, 239, 230, 0.5)",
    borderRadius: 8,
    padding: 16,
    maxHeight: 400,
    overflowY: "auto",
    fontSize: 14,
    lineHeight: 1.7,
    color: "var(--text)",
  },
  metaGrid: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  metaRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 0",
    borderBottom: "1px solid var(--line)",
  },
  metaLabel: {
    fontSize: 13,
    color: "var(--muted)",
  },
  metaValue: {
    fontSize: 13,
    fontWeight: 500,
    color: "var(--text)",
  },
  metaLink: {
    color: "var(--brand-2)",
    textDecoration: "none",
    fontWeight: 500,
  },
  actionButtons: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  actionBtn: {
    width: "100%",
    padding: "10px 14px",
    fontSize: 13,
  },
  // 质量面板样式
  qualityBtn: {
    padding: "6px 14px",
    borderRadius: 20,
    border: "1px solid var(--line)",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
  qualityPanel: {
    padding: 20,
    marginBottom: 16,
  },
  qualityPanelHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  qualityPanelTitle: {
    fontSize: 18,
    fontWeight: 700,
    margin: 0,
  },
  adjustBtn: {
    padding: "8px 16px",
    borderRadius: 6,
    border: "none",
    background: "linear-gradient(90deg, var(--brand), #d45b39)",
    color: "#fff",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  },
  suggestionStats: {
    display: "flex",
    gap: 16,
    marginBottom: 24,
  },
  suggestionStatItem: {
    flex: 1,
    padding: "16px 20px",
    borderRadius: 12,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  suggestionStatNumber: {
    fontSize: 28,
    fontWeight: 700,
    marginBottom: 4,
  },
  suggestionStatLabel: {
    fontSize: 13,
    color: "#666",
  },
  suggestionsSection: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: 600,
    margin: "0 0 12px",
    color: "var(--text)",
  },
  suggestionsList: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  suggestionItem: {
    padding: 12,
    background: "var(--panel)",
    borderRadius: 8,
    borderLeft: "4px solid",
  },
  suggestionHeader: {
    display: "flex",
    gap: 8,
    marginBottom: 8,
  },
  suggestionType: {
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
  },
  suggestionPriority: {
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
  },
  suggestionTitle: {
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 4,
    color: "var(--text)",
  },
  suggestionText: {
    fontSize: 13,
    color: "var(--brand)",
    marginBottom: 4,
  },
  suggestionReason: {
    fontSize: 12,
    color: "var(--muted)",
  },
  rankingsSection: {
    marginTop: 20,
  },
  rankingsTable: {
    width: "100%",
    fontSize: 13,
    borderCollapse: "collapse",
  },
  rankingTh: {
    padding: "10px 8px",
    textAlign: "center" as const,
    fontWeight: 600,
    color: "var(--muted)",
    borderBottom: "1px solid var(--line)",
  },
  rankingThTitle: {
    padding: "10px 8px",
    textAlign: "left" as const,
    fontWeight: 600,
    color: "var(--muted)",
    borderBottom: "1px solid var(--line)",
  },
  rankingRow: {
    transition: "background 0.15s ease",
  },
  rankingTd: {
    padding: "10px 8px",
    textAlign: "center" as const,
    borderBottom: "1px solid var(--line)",
  },
  rankingTdTitle: {
    padding: "10px 8px",
    textAlign: "left" as const,
    borderBottom: "1px solid var(--line)",
    maxWidth: 300,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
  },
  rankingBadge: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: 24,
    height: 24,
    borderRadius: "50%",
    fontSize: 12,
    fontWeight: 700,
  },
  qualityScore: {
    fontWeight: 700,
  },
  referenceCount: {
    fontWeight: 600,
  },
  positiveBadge: {
    marginLeft: 4,
    padding: "1px 4px",
    background: "#e8f5e9",
    color: "#2e7d32",
    borderRadius: 4,
    fontSize: 10,
  },
  weightBadge: {
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
  },
  loadingText: {
    textAlign: "center" as const,
    padding: 40,
    color: "var(--muted)",
  },
  emptyText: {
    textAlign: "center" as const,
    padding: 40,
    color: "var(--muted)",
  },
  // Tab 切换样式
  tabGroup: {
    display: 'flex',
    gap: 4,
    background: 'var(--panel)',
    padding: 4,
    borderRadius: 8,
  border: '1px solid var(--line)',
  },
  tabBtn: {
    padding: '6px 16px',
    borderRadius: 6,
    border: 'none',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  // 知识图谱样式
  graphPanel: {
    padding: 20,
  display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  graphStatsRow: {
    display: 'flex',
    gap: 16,
    flexWrap: 'wrap',
  },
  graphStatCard: {
    flex: 1,
    minWidth: 140,
    padding: '20px 16px',
    borderRadius: 12,
    color: '#fff',
    textAlign: 'center',
  },
  graphStatIcon: {
    fontSize: 24,
    marginBottom: 8,
  },
  graphStatValue: {
    fontSize: 28,
    fontWeight: 700,
    marginBottom: 4,
  },
  graphStatLabel: {
    fontSize: 12,
    opacity: 0.9,
  },
  graphActions: {
    display: 'flex',
    gap: 12,
    flexWrap: 'wrap',
  },
  buildBtn: {
    padding: '10px 24px',
    fontSize: 14,
    fontWeight: 600,
  },
  refreshBtn: {
    padding: '10px 24px',
    fontSize: 14,
  },
  relationTypesSection: {
    background: 'rgba(0,0,0,0.02)',
    borderRadius: 8,
    padding: 16,
  },
  relationTypesList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
  },
  relationTypeItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: 'var(--panel)',
    padding: '6px 12px',
    borderRadius: 6,
    border: '1px solid var(--line)',
  },
  relationTypeName: {
    fontSize: 13,
    color: 'var(--text)',
  },
  relationTypeCount: {
    fontSize: 12,
    color: 'var(--muted)',
    background: 'rgba(0,0,0,0.06)',
    padding: '2px 8px',
    borderRadius: 4,
  },
  clustersSection: {
    background: 'rgba(0,0,0,0.02)',
    borderRadius: 8,
    padding: 16,
  },
  clustersList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  clusterItem: {
    background: 'var(--panel)',
    borderRadius: 8,
    padding: 12,
    border: '1px solid var(--line)',
  },
  clusterHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  clusterTopic: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--text)',
  },
  clusterCount: {
    fontSize: 12,
    color: 'var(--brand)',
    fontWeight: 600,
  },
  clusterItems: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  clusterItemTag: {
    fontSize: 11,
    background: 'rgba(0,0,0,0.04)',
    padding: '3px 8px',
    borderRadius: 4,
    color: 'var(--muted)',
  },
  clusterMore: {
    fontSize: 11,
    color: 'var(--brand)',
    fontStyle: 'italic',
  },
  relationsSection: {
    background: 'rgba(0,0,0,0.02)',
    borderRadius: 8,
    padding: 16,
  },
  relationsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  relationItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    background: 'var(--panel)',
    padding: '10px 14px',
    borderRadius: 8,
    border: '1px solid var(--line)',
  },
  relationNode: {
    flex: 1,
    fontSize: 13,
    color: 'var(--text)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  relationArrow: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 2,
  },
  relationType: {
    fontSize: 11,
    color: 'var(--brand)',
    fontWeight: 600,
  },
  relationWeight: {
    fontSize: 10,
    color: 'var(--muted)',
  },
  emptyGraphState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 60,
    textAlign: 'center',
  },
};
