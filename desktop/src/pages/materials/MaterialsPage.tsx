import { FormEvent, useEffect, useState } from "react";
import { analyzeCollect, getCollectDetail, listCollect, rewriteCollect, submitManualToInbox } from "../../lib/api";
import { CollectDetail, CollectItem } from "../../types";

const DRAFT_KEY = "zhk_material_editor_draft";
const CONTENT_LIMITS: Record<string, number> = {
  xiaohongshu: 1000,
  douyin: 800,
  zhihu: 5000,
  xianyu: 2000,
};

export function MaterialsPage() {
  const [items, setItems] = useState<CollectItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState<CollectDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"blocks" | "comments" | "snapshot" | "insight" | "raw">("blocks");
  const [actionMessage, setActionMessage] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [rewritePlatform, setRewritePlatform] = useState<"xiaohongshu" | "douyin" | "zhihu">("xiaohongshu");
  const [rewrittenText, setRewrittenText] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [platform, setPlatform] = useState("xiaohongshu");
  const [tags, setTags] = useState("内容,获客");
  const [message, setMessage] = useState("");
  const currentLimit = CONTENT_LIMITS[platform] || 2000;
  const titleLength = title.trim().length;
  const contentLength = content.trim().length;

  useEffect(() => {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return;
    try {
      const draft = JSON.parse(raw) as {
        platform?: string;
        title?: string;
        content?: string;
        tags?: string;
      };
      if (draft.platform) setPlatform(draft.platform);
      if (draft.title) setTitle(draft.title);
      if (draft.content) setContent(draft.content);
      if (draft.tags) setTags(draft.tags);
      setMessage("已恢复上次编辑草稿");
    } catch {
      localStorage.removeItem(DRAFT_KEY);
    }
  }, []);

  useEffect(() => {
    const hasDraft = title.trim() || content.trim();
    if (!hasDraft) {
      localStorage.removeItem(DRAFT_KEY);
      return;
    }
    const timer = window.setTimeout(() => {
      localStorage.setItem(
        DRAFT_KEY,
        JSON.stringify({
          platform,
          title,
          content,
          tags,
        }),
      );
    }, 300);
    return () => window.clearTimeout(timer);
  }, [platform, title, content, tags]);

  async function fetchData() {
    setListLoading(true);
    setListError("");
    try {
      const data = await listCollect();
      setItems(data || []);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setListError(typeof detail === "string" ? detail : "素材列表加载失败，请检查登录状态或刷新重试");
      setItems([]);
    } finally {
      setListLoading(false);
    }
  }

  async function openDetail(id: number) {
    setDetailLoading(true);
    setActionMessage("");
    setRewrittenText("");
    try {
      const data = await getCollectDetail(id);
      setDetail(data);
      setActiveTab("blocks");
    } catch (err: any) {
      setActionMessage(err?.response?.data?.detail || "加载素材详情失败");
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleAnalyze() {
    if (!detail) return;
    setAnalyzing(true);
    setActionMessage("");
    try {
      await analyzeCollect(detail.id);
      const fresh = await getCollectDetail(detail.id);
      setDetail(fresh);
      setActionMessage("分析完成，洞察结果已回写");
      setActiveTab("insight");
      await fetchData();
    } catch (err: any) {
      setActionMessage(err?.response?.data?.detail || "分析失败");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleRewrite() {
    if (!detail) return;
    setRewriting(true);
    setActionMessage("");
    try {
      const data = await rewriteCollect(detail.id, rewritePlatform);
      setRewrittenText(data?.rewritten || "");
      setActionMessage("改写完成");
    } catch (err: any) {
      setActionMessage(err?.response?.data?.detail || "改写失败");
    } finally {
      setRewriting(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (titleLength < 4) {
      setMessage("标题至少 4 个字符");
      return;
    }
    if (contentLength < 20) {
      setMessage("正文至少 20 个字符");
      return;
    }
    if (contentLength > currentLimit) {
      setMessage(`当前平台正文长度上限 ${currentLimit}，请精简后再提交`);
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      await submitManualToInbox({
        platform,
        title,
        content,
        tags: tags
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setMessage("已提交到收件箱，等待审核后入库");
      setTitle("");
      setContent("");
      localStorage.removeItem(DRAFT_KEY);
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "保存失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page grid">
      <h2>素材中心</h2>

      <section className="card">
        <h3>手动录入素材</h3>
        <form onSubmit={onSubmit} className="grid">
          <div className="form-row">
            <div>
              <label>平台</label>
              <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
                <option value="xiaohongshu">小红书</option>
                <option value="douyin">抖音</option>
                <option value="zhihu">知乎</option>
                <option value="xianyu">咸鱼</option>
              </select>
            </div>
            <div>
              <label>标签（逗号分隔）</label>
              <input value={tags} onChange={(e) => setTags(e.target.value)} />
            </div>
          </div>

          <div>
            <label>标题</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
            <div className="muted" style={{ marginTop: 6 }}>当前字数：{titleLength}</div>
          </div>

          <div>
            <label>正文</label>
            <textarea value={content} onChange={(e) => setContent(e.target.value)} required />
            <div className="muted" style={{ marginTop: 6 }}>
              当前字数：{contentLength} / {currentLimit}
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button className="primary" type="submit" disabled={loading || contentLength > currentLimit}>
              {loading ? "保存中..." : "保存素材"}
            </button>
            {message && <span className="muted">{message}</span>}
          </div>
        </form>
      </section>

      <section className="card">
        <h3>素材列表</h3>
        <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
          <button className="ghost" type="button" onClick={fetchData} disabled={listLoading}>
            {listLoading ? "刷新中..." : "刷新列表"}
          </button>
          {listError && <span className="muted" style={{ color: "#c0392b" }}>{listError}</span>}
          {!listError && !listLoading && <span className="muted">共 {items.length} 条素材</span>}
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>标题</th>
              <th>标签</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.platform}</td>
                <td>{item.title}</td>
                <td>{item.tags?.join(", ")}</td>
                <td>{item.created_at ? new Date(item.created_at).toLocaleString() : "-"}</td>
                <td>
                  <button className="ghost" type="button" onClick={() => openDetail(item.id)}>
                    查看详情
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h3>素材详情</h3>
        {detailLoading ? (
          <div className="muted">详情加载中...</div>
        ) : !detail ? (
          <div className="muted">请在上方列表点击“查看详情”</div>
        ) : (
          <div className="grid" style={{ gap: 12 }}>
            <div className="muted">
              标题：{detail.title} | 平台：{detail.platform} | 作者：{detail.author_name || "-"}
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className="secondary" type="button" onClick={handleAnalyze} disabled={analyzing}>
                {analyzing ? "分析中..." : "生成洞察"}
              </button>
              <select
                value={rewritePlatform}
                onChange={(e) => setRewritePlatform(e.target.value as "xiaohongshu" | "douyin" | "zhihu")}
                style={{ width: 140 }}
              >
                <option value="xiaohongshu">改写-小红书</option>
                <option value="douyin">改写-抖音</option>
                <option value="zhihu">改写-知乎</option>
              </select>
              <button className="secondary" type="button" onClick={handleRewrite} disabled={rewriting}>
                {rewriting ? "改写中..." : "执行改写"}
              </button>
            </div>
            {actionMessage && <div className="muted">{actionMessage}</div>}

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className={activeTab === "blocks" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("blocks")}>正文块</button>
              <button className={activeTab === "comments" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("comments")}>评论</button>
              <button className={activeTab === "snapshot" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("snapshot")}>快照</button>
              <button className={activeTab === "insight" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("insight")}>洞察</button>
              <button className={activeTab === "raw" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("raw")}>原始字段</button>
            </div>

            {activeTab === "blocks" && (
              <div className="grid" style={{ gap: 8 }}>
                {(detail.blocks || []).length ? detail.blocks.map((block, index) => (
                  <div key={`${block.block_type}-${block.block_order}-${index}`} className="card" style={{ padding: 10 }}>
                    <div className="muted">{block.block_type} #{block.block_order}</div>
                    <div>{block.block_text}</div>
                  </div>
                )) : <div className="muted">暂无结构化正文块</div>}
              </div>
            )}

            {activeTab === "comments" && (
              <div className="grid" style={{ gap: 8 }}>
                {(detail.comments || []).length ? detail.comments.map((comment, index) => (
                  <div key={`${comment.commenter_name || "u"}-${index}`} className="card" style={{ padding: 10 }}>
                    <div className="muted">{comment.commenter_name || "匿名"} · 赞 {comment.like_count || 0}</div>
                    <div>{comment.comment_text}</div>
                  </div>
                )) : <div className="muted">暂无评论</div>}
              </div>
            )}

            {activeTab === "snapshot" && (
              <div className="grid" style={{ gap: 8 }}>
                <div className="muted">截图地址：{detail.snapshot?.screenshot_url || "-"}</div>
                <textarea readOnly value={detail.snapshot?.raw_html || ""} placeholder="无页面 HTML 快照" />
              </div>
            )}

            {activeTab === "insight" && (
              <div className="grid" style={{ gap: 8 }}>
                <div className="muted">标题模式：{detail.insight?.title_pattern || "-"}</div>
                <div>高频问题：{(detail.insight?.high_freq_questions_json || []).join(" / ") || "-"}</div>
                <div>关键句：{(detail.insight?.key_sentences_json || []).join(" / ") || "-"}</div>
                <div>建议选题：{(detail.insight?.suggested_topics_json || []).join(" / ") || "-"}</div>
              </div>
            )}

            {activeTab === "raw" && (
              <div className="grid" style={{ gap: 8 }}>
                <div className="muted">用于回放 Spider_XHS 原始字段（如 note_id、note_type、image_list、video_addr 等）。</div>
                <textarea
                  readOnly
                  value={JSON.stringify(detail.snapshot?.raw_payload || detail.snapshot?.page_meta_json || {}, null, 2)}
                  placeholder="无原始字段"
                />
              </div>
            )}

            {rewrittenText && (
              <div className="grid" style={{ gap: 8 }}>
                <h4 style={{ margin: 0 }}>改写结果</h4>
                <textarea readOnly value={rewrittenText} />
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
