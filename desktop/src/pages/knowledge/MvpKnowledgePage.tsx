import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  mvpListKnowledge,
  mvpGetKnowledge,
  mvpSearchKnowledge,
  mvpBuildKnowledgeFromMaterial,
} from "../../lib/api";
import { MvpKnowledgeItem } from "../../types";

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

      {/* 顶部筛选区 */}
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

      {/* 主内容区 */}
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
};
