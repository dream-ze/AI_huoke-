import { FormEvent, useEffect, useState } from "react";
import { listContent, submitManualToInbox } from "../lib/api";
import { ContentAsset } from "../types";

export function ContentPage() {
  const [items, setItems] = useState<ContentAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [platform, setPlatform] = useState("xiaohongshu");
  const [tags, setTags] = useState("内容,获客");
  const [message, setMessage] = useState("");

  async function fetchData() {
    const data = await listContent();
    setItems(data || []);
  }

  useEffect(() => {
    fetchData();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
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
          setMessage("已进入素材中心，并放入待审核队列");
      setTitle("");
      setContent("");
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "保存失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page grid">
      <h2>内容采集中心</h2>

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
          </div>

          <div>
            <label>正文</label>
            <textarea value={content} onChange={(e) => setContent(e.target.value)} required />
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button className="primary" type="submit" disabled={loading}>
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
              <th>状态</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.platform}</td>
                <td>{item.title}</td>
                <td>{(item as any).status || "-"}</td>
                <td>{new Date(item.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
