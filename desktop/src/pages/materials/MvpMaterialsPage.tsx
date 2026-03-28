import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { mvpListMaterials, mvpGetMaterial, mvpBuildKnowledge, mvpUpdateTags, mvpListTags } from "../../lib/api";
import { MvpMaterialItem, MvpTag } from "../../types";

const PLATFORMS = [
  { value: "", label: "全部" },
  { value: "xiaohongshu", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
  { value: "weibo", label: "微博" },
];

const AUDIENCES = [
  { value: "", label: "全部" },
  { value: "负债人群", label: "负债人群" },
  { value: "上班族", label: "上班族" },
  { value: "个体户/老板", label: "个体户/老板" },
  { value: "大学生", label: "大学生" },
  { value: "宝妈群体", label: "宝妈群体" },
];

const STYLES = [
  { value: "", label: "全部" },
  { value: "专业型", label: "专业型" },
  { value: "口语型", label: "口语型" },
  { value: "种草型", label: "种草型" },
  { value: "避坑型", label: "避坑型" },
  { value: "故事型", label: "故事型" },
];

const HOT_OPTIONS = [
  { value: "", label: "全部" },
  { value: "true", label: "是" },
  { value: "false", label: "否" },
];

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function truncate(text: string, max: number): string {
  if (!text) return "-";
  return text.length > max ? text.slice(0, max) + "..." : text;
}

function getPlatformLabel(platform: string): string {
  const map: Record<string, string> = {
    xiaohongshu: "小红书",
    douyin: "抖音",
    zhihu: "知乎",
    weibo: "微博",
  };
  return map[platform] || platform;
}

function getRiskColor(level: string): string {
  if (level === "high" || level === "danger") return "var(--danger)";
  if (level === "medium" || level === "warn") return "var(--warn)";
  return "var(--ok)";
}

function extractHotStructure(item: MvpMaterialItem) {
  const title = item.title || "";
  const content = item.content || "";
  const sentences = content.split(/[。！？\n]/).filter((s) => s.trim());
  const hook = title.slice(0, 10) + (title.length > 10 ? "..." : "");
  const firstSentence = sentences[0] || "";
  const painKeywords = ["痛苦", "困扰", "烦恼", "难", "焦虑", "担心", "害怕", "压力"];
  const solutionKeywords = ["解决", "方法", "技巧", "推荐", "建议", "秘诀", "攻略", "教你"];
  let painSentence = "";
  let solutionSentence = "";
  for (const s of sentences) {
    if (!painSentence && painKeywords.some((k) => s.includes(k))) painSentence = s;
    if (!solutionSentence && solutionKeywords.some((k) => s.includes(k))) solutionSentence = s;
    if (painSentence && solutionSentence) break;
  }
  return { hook, firstSentence, painSentence, solutionSentence };
}

export default function MvpMaterialsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<MvpMaterialItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<MvpMaterialItem | null>(null);
  const [allTags, setAllTags] = useState<MvpTag[]>([]);
  const [editingTags, setEditingTags] = useState(false);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState("");
  const [message, setMessage] = useState({ text: "", type: "" });
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterTag, setFilterTag] = useState("");
  const [filterAudience, setFilterAudience] = useState("");
  const [filterStyle, setFilterStyle] = useState("");
  const [filterHot, setFilterHot] = useState("");
  const [filterKeyword, setFilterKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const showMessage = (text: string, type: "success" | "error") => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: "", type: "" }), 3000);
  };

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {};
      if (filterPlatform) params.platform = filterPlatform;
      if (filterTag) params.tag_id = filterTag;
      if (filterAudience) params.audience = filterAudience;
      if (filterStyle) params.style = filterStyle;
      if (filterHot) params.is_hot = filterHot === "true";
      if (filterKeyword) params.keyword = filterKeyword;
      const res = await mvpListMaterials(params);
      const list = Array.isArray(res) ? res : res?.items || [];
      setItems(list);
      setTotal(res?.total ?? list.length);
    } catch (e) {
      console.error(e);
      showMessage("加载素材列表失败", "error");
    } finally {
      setLoading(false);
    }
  }, [filterPlatform, filterTag, filterAudience, filterStyle, filterHot, filterKeyword]);

  const fetchTags = useCallback(async () => {
    try {
      const res = await mvpListTags();
      const list = Array.isArray(res) ? res : res?.items || [];
      setAllTags(list);
    } catch (e) {
      console.error(e);
    }
  }, []);

  const fetchDetail = useCallback(async (id: number) => {
    try {
      const res = await mvpGetMaterial(id);
      setDetail(res);
      setSelectedTagIds((res.tags || []).map((t: MvpTag) => t.id));
    } catch (e) {
      console.error(e);
      showMessage("加载详情失败", "error");
    }
  }, []);

  useEffect(() => {
    fetchList();
    fetchTags();
  }, [fetchList, fetchTags]);

  useEffect(() => {
    if (selectedId !== null) fetchDetail(selectedId);
    else {
      setDetail(null);
      setEditingTags(false);
    }
  }, [selectedId, fetchDetail]);

  const handleSearch = () => {
    setFilterKeyword(searchInput);
  };

  const handleRowClick = (id: number) => {
    setSelectedId(id === selectedId ? null : id);
    setEditingTags(false);
  };

  const handleBuildKnowledge = async () => {
    if (!detail) return;
    setActionLoading("knowledge");
    try {
      await mvpBuildKnowledge(detail.id);
      showMessage("知识构建成功，可前往知识库查看", "success");
    } catch (e) {
      console.error(e);
      showMessage("知识构建失败", "error");
    } finally {
      setActionLoading("");
    }
  };

  const handleToggleHot = async () => {
    if (!detail) return;
    setActionLoading("hot");
    try {
      const newTags = detail.is_hot
        ? selectedTagIds.filter((id) => allTags.find((t) => t.id === id)?.name !== "爆款")
        : [...selectedTagIds];
      await mvpUpdateTags(detail.id, newTags);
      await fetchDetail(detail.id);
      await fetchList();
      showMessage(detail.is_hot ? "已取消爆款标记" : "已标记为爆款", "success");
    } catch (e) {
      console.error(e);
      showMessage("操作失败", "error");
    } finally {
      setActionLoading("");
    }
  };

  const handleSaveTags = async () => {
    if (!detail) return;
    setActionLoading("tags");
    try {
      await mvpUpdateTags(detail.id, selectedTagIds);
      await fetchDetail(detail.id);
      await fetchList();
      setEditingTags(false);
      showMessage("标签保存成功", "success");
    } catch (e) {
      console.error(e);
      showMessage("保存标签失败", "error");
    } finally {
      setActionLoading("");
    }
  };

  const toggleTagSelection = (tagId: number) => {
    setSelectedTagIds((prev) =>
      prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]
    );
  };

  const groupedTags = allTags.reduce<Record<string, MvpTag[]>>((acc, tag) => {
    const type = tag.type || "其他";
    if (!acc[type]) acc[type] = [];
    acc[type].push(tag);
    return acc;
  }, {});

  const hotStructure = detail?.is_hot ? extractHotStructure(detail) : null;

  return (
    <div className="page">
      <style>{`
        .mat-header { display: flex; align-items: baseline; gap: 16px; margin-bottom: 16px; }
        .mat-header h2 { font-size: 22px; }
        .mat-header .total { color: var(--muted); font-size: 14px; }
        .mat-filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 16px; padding: 16px; }
        .mat-filters select, .mat-filters input { min-width: 120px; padding: 8px 12px; font-size: 13px; }
        .mat-filters input { flex: 1; min-width: 180px; }
        .mat-filters button { padding: 8px 16px; }
        .mat-main { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
        .mat-list-wrap { overflow: auto; max-height: calc(100vh - 240px); }
        .mat-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .mat-table th, .mat-table td { padding: 10px 8px; border-bottom: 1px solid var(--line); text-align: left; }
        .mat-table th { background: var(--bg-2); font-weight: 600; position: sticky; top: 0; z-index: 1; }
        .mat-table tr { cursor: pointer; transition: background 0.15s; }
        .mat-table tr:hover { background: rgba(182, 61, 31, 0.04); }
        .mat-table tr.selected { background: linear-gradient(90deg, rgba(248, 216, 191, 0.4), rgba(192, 237, 243, 0.3)); }
        .mat-tag { display: inline-block; background: rgba(15, 109, 122, 0.12); color: var(--brand-2); padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-right: 4px; }
        .mat-tag.more { background: var(--bg-2); color: var(--muted); }
        .mat-hot { color: #d4a017; }
        .mat-risk { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .mat-detail { position: sticky; top: 0; max-height: calc(100vh - 240px); overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
        .mat-detail-card { border: 1px solid var(--line); border-radius: 12px; background: var(--panel); padding: 16px; }
        .mat-detail-card h4 { margin: 0 0 12px; font-size: 14px; color: var(--muted); }
        .mat-detail-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
        .mat-detail-meta { font-size: 13px; color: var(--muted); margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 12px; }
        .mat-detail-stats { display: flex; gap: 16px; font-size: 13px; margin-bottom: 8px; }
        .mat-content-box { max-height: 250px; overflow-y: auto; background: #fffdf8; padding: 12px; border-radius: 8px; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
        .mat-tags-display { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
        .mat-tag-edit-panel { margin-top: 12px; padding-top: 12px; border-top: 1px dashed var(--line); }
        .mat-tag-group { margin-bottom: 12px; }
        .mat-tag-group-title { font-size: 12px; font-weight: 600; color: var(--muted); margin-bottom: 8px; }
        .mat-tag-options { display: flex; flex-wrap: wrap; gap: 8px; }
        .mat-tag-option { display: flex; align-items: center; gap: 4px; padding: 6px 12px; border-radius: 16px; font-size: 12px; cursor: pointer; border: 1px solid var(--line); background: #fff; transition: all 0.15s; }
        .mat-tag-option:hover { border-color: var(--brand-2); }
        .mat-tag-option.selected { background: rgba(15, 109, 122, 0.15); border-color: var(--brand-2); color: var(--brand-2); }
        .mat-tag-option input { display: none; }
        .mat-tag-actions { display: flex; gap: 8px; margin-top: 12px; }
        .mat-hot-card { border: 2px solid #d4a017; background: linear-gradient(135deg, #fffbf0, #fff8e8); }
        .mat-hot-card h4 { color: #b08a00; }
        .mat-hot-item { margin-bottom: 10px; }
        .mat-hot-label { font-size: 12px; font-weight: 600; color: var(--muted); margin-bottom: 4px; }
        .mat-hot-value { font-size: 14px; line-height: 1.5; background: #fffdf8; padding: 8px; border-radius: 6px; }
        .mat-actions { display: flex; flex-direction: column; gap: 10px; }
        .mat-actions button { width: 100%; justify-content: center; }
        .mat-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; text-align: center; color: var(--muted); }
        .mat-empty .icon { font-size: 48px; margin-bottom: 16px; }
        .mat-empty p { margin: 8px 0; }
        .mat-empty a { color: var(--brand); text-decoration: none; font-weight: 600; }
        .mat-detail-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: var(--muted); text-align: center; }
        .mat-detail-empty .icon { font-size: 40px; margin-bottom: 12px; }
        .mat-message { position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; z-index: 1000; animation: slideIn 0.3s ease; }
        .mat-message.success { background: #d4edda; color: #155724; }
        .mat-message.error { background: #f8d7da; color: #721c24; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .mat-loading { text-align: center; padding: 40px; color: var(--muted); }
      `}</style>

      {message.text && <div className={`mat-message ${message.type}`}>{message.text}</div>}

      <div className="mat-header">
        <h2>素材库 - 素材资产池</h2>
        <span className="total">共 {total} 条</span>
      </div>

      <div className="card mat-filters">
        <select value={filterPlatform} onChange={(e) => setFilterPlatform(e.target.value)}>
          {PLATFORMS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        <select value={filterTag} onChange={(e) => setFilterTag(e.target.value)}>
          <option value="">全部标签</option>
          {allTags.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <select value={filterAudience} onChange={(e) => setFilterAudience(e.target.value)}>
          {AUDIENCES.map((a) => (
            <option key={a.value} value={a.value}>{a.label}</option>
          ))}
        </select>
        <select value={filterStyle} onChange={(e) => setFilterStyle(e.target.value)}>
          {STYLES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
        <select value={filterHot} onChange={(e) => setFilterHot(e.target.value)}>
          {HOT_OPTIONS.map((h) => (
            <option key={h.value} value={h.value}>{h.label}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="搜索标题或内容..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button className="primary" onClick={handleSearch}>搜索</button>
      </div>

      {items.length === 0 && !loading ? (
        <div className="card mat-empty">
          <div className="icon">📦</div>
          <h3>素材库为空</h3>
          <p>请先从收件箱将内容入库</p>
          <a href="#" onClick={(e) => { e.preventDefault(); navigate("/mvp-inbox"); }}>去收件箱 →</a>
        </div>
      ) : (
        <div className="mat-main">
          <div className="card mat-list-wrap">
            {loading ? (
              <div className="mat-loading">加载中...</div>
            ) : (
              <table className="mat-table">
                <thead>
                  <tr>
                    <th style={{ width: "35%" }}>标题</th>
                    <th style={{ width: "10%" }}>平台</th>
                    <th style={{ width: "18%" }}>标签</th>
                    <th style={{ width: "6%" }}>爆款</th>
                    <th style={{ width: "8%" }}>使用次数</th>
                    <th style={{ width: "8%" }}>风险</th>
                    <th style={{ width: "12%" }}>创建时间</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className={selectedId === item.id ? "selected" : ""}
                      onClick={() => handleRowClick(item.id)}
                    >
                      <td>{truncate(item.title, 40)}</td>
                      <td>{getPlatformLabel(item.platform)}</td>
                      <td>
                        {(item.tags || []).slice(0, 3).map((t) => (
                          <span key={t.id} className="mat-tag">{t.name}</span>
                        ))}
                        {(item.tags || []).length > 3 && (
                          <span className="mat-tag more">+{item.tags.length - 3}</span>
                        )}
                      </td>
                      <td className={item.is_hot ? "mat-hot" : ""}>{item.is_hot ? "🔥" : "-"}</td>
                      <td>{item.use_count}</td>
                      <td>
                        <span className="mat-risk" style={{ background: `${getRiskColor(item.risk_level)}20`, color: getRiskColor(item.risk_level) }}>
                          {item.risk_level || "low"}
                        </span>
                      </td>
                      <td>{formatDate(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="mat-detail">
            {!detail ? (
              <div className="card mat-detail-empty">
                <div className="icon">📄</div>
                <p>请选择一条素材查看详情</p>
              </div>
            ) : (
              <>
                <div className="mat-detail-card">
                  <h4>基本信息</h4>
                  <div className="mat-detail-title">{detail.title}</div>
                  <div className="mat-detail-meta">
                    <span>{getPlatformLabel(detail.platform)}</span>
                    {detail.author && <span>作者: {detail.author}</span>}
                    {detail.source_url && (
                      <a href={detail.source_url} target="_blank" rel="noreferrer" style={{ color: "var(--brand-2)" }}>
                        查看原文
                      </a>
                    )}
                  </div>
                  <div className="mat-detail-stats">
                    <span>👍 {detail.like_count}</span>
                    <span>💬 {detail.comment_count}</span>
                  </div>
                  <span className="mat-risk" style={{ background: `${getRiskColor(detail.risk_level)}20`, color: getRiskColor(detail.risk_level) }}>
                    风险: {detail.risk_level || "low"}
                  </span>
                </div>

                <div className="mat-detail-card">
                  <h4>正文内容</h4>
                  <div className="mat-content-box">{detail.content || "暂无内容"}</div>
                </div>

                <div className="mat-detail-card">
                  <h4>标签信息</h4>
                  <div className="mat-tags-display">
                    {(detail.tags || []).length === 0 ? (
                      <span style={{ color: "var(--muted)", fontSize: 13 }}>暂无标签</span>
                    ) : (
                      detail.tags.map((t) => (
                        <span key={t.id} className="mat-tag">{t.name}</span>
                      ))
                    )}
                  </div>
                  {!editingTags ? (
                    <button className="ghost" onClick={() => setEditingTags(true)}>编辑标签</button>
                  ) : (
                    <div className="mat-tag-edit-panel">
                      {Object.entries(groupedTags).map(([type, tags]) => (
                        <div key={type} className="mat-tag-group">
                          <div className="mat-tag-group-title">[{type}]</div>
                          <div className="mat-tag-options">
                            {tags.map((tag) => (
                              <label
                                key={tag.id}
                                className={`mat-tag-option ${selectedTagIds.includes(tag.id) ? "selected" : ""}`}
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedTagIds.includes(tag.id)}
                                  onChange={() => toggleTagSelection(tag.id)}
                                />
                                {selectedTagIds.includes(tag.id) ? "☑" : "☐"} {tag.name}
                              </label>
                            ))}
                          </div>
                        </div>
                      ))}
                      <div className="mat-tag-actions">
                        <button
                          className="primary"
                          onClick={handleSaveTags}
                          disabled={actionLoading === "tags"}
                        >
                          {actionLoading === "tags" ? "保存中..." : "保存标签"}
                        </button>
                        <button className="ghost" onClick={() => { setEditingTags(false); setSelectedTagIds((detail.tags || []).map((t) => t.id)); }}>
                          取消
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {detail.is_hot && hotStructure && (
                  <div className="mat-detail-card mat-hot-card">
                    <h4>🔥 爆款结构拆解</h4>
                    <div className="mat-hot-item">
                      <div className="mat-hot-label">标题套路（钩子分析）</div>
                      <div className="mat-hot-value">{hotStructure.hook || "-"}</div>
                    </div>
                    <div className="mat-hot-item">
                      <div className="mat-hot-label">钩子句（正文第一句）</div>
                      <div className="mat-hot-value">{hotStructure.firstSentence || "-"}</div>
                    </div>
                    <div className="mat-hot-item">
                      <div className="mat-hot-label">痛点句</div>
                      <div className="mat-hot-value">{hotStructure.painSentence || "未检测到明显痛点句"}</div>
                    </div>
                    <div className="mat-hot-item">
                      <div className="mat-hot-label">解决方案句</div>
                      <div className="mat-hot-value">{hotStructure.solutionSentence || "未检测到明显方案句"}</div>
                    </div>
                    <button
                      className="secondary"
                      style={{ marginTop: 12 }}
                      onClick={() => navigate(`/mvp-workbench?source_type=material&source_id=${detail.id}&enable_rewrite=true`)}
                    >
                      ✍️ 可仿写
                    </button>
                  </div>
                )}

                <div className="mat-detail-card">
                  <h4>操作</h4>
                  <div className="mat-actions">
                    <button
                      className="primary"
                      onClick={() => navigate('/ai-workbench', { 
                        state: { 
                          materialId: detail.id, 
                          materialTitle: detail.title, 
                          materialContent: detail.content, 
                          materialPlatform: detail.platform 
                        } 
                      })}
                    >
                      🤖 AI改写
                    </button>
                    <button
                      className="primary"
                      onClick={() => navigate('/mvp-workbench', { 
                        state: { 
                          source_content: detail.content, 
                          platform: detail.platform,
                          source_title: detail.title
                        } 
                      })}
                    >
                      ✍️ 转入改写
                    </button>
                    <button
                      className="primary"
                      onClick={() => navigate(`/mvp-workbench?source_type=material&source_id=${detail.id}`)}
                    >
                      ✨ 进入AI工作台生成
                    </button>
                    <button
                      className="secondary"
                      onClick={handleBuildKnowledge}
                      disabled={actionLoading === "knowledge"}
                    >
                      {actionLoading === "knowledge" ? "构建中..." : "📚 一键构建知识"}
                    </button>
                    <button
                      className="secondary"
                      onClick={() => navigate(`/mvp-workbench?source_type=material&source_id=${detail.id}&enable_rewrite=true`)}
                    >
                      🔥 爆款仿写
                    </button>
                    <button
                      className="ghost"
                      onClick={handleToggleHot}
                      disabled={actionLoading === "hot"}
                    >
                      {actionLoading === "hot" ? "处理中..." : detail.is_hot ? "🏷️ 取消爆款" : "🏷️ 标记为爆款"}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
