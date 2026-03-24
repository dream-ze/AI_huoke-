import { FormEvent, useEffect, useState } from "react";
import { createContent, listContent } from "../../lib/api";
import { ContentAsset } from "../../types";

const DRAFT_KEY = "zhk_material_editor_draft";
const CONTENT_LIMITS: Record<string, number> = {
  xiaohongshu: 1000,
  douyin: 800,
  zhihu: 5000,
  xianyu: 2000,
};

export function MaterialsPage() {
  const [items, setItems] = useState<ContentAsset[]>([]);
  const [loading, setLoading] = useState(false);
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
    const data = await listContent();
    setItems(data || []);
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
      await createContent({
        platform,
        content_type: "post",
        title,
        content,
        tags: tags
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setMessage("保存成功");
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
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>标题</th>
              <th>标签</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.platform}</td>
                <td>{item.title}</td>
                <td>{item.tags?.join(", ")}</td>
                <td>{new Date(item.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
