import { FormEvent, useEffect, useState } from "react";

import {
  createInboxItem,
  getInboxStats,
  listInboxItems,
  parseLink,
} from "../../lib/api";
import { InboxItem, InboxStats, ParsedLinkMeta } from "../../types";

const emptyStats: InboxStats = {
  total: 0,
  pending: 0,
  analyzed: 0,
  imported: 0,
  discarded: 0,
  by_platform: {},
};

export function CollectCenterPage() {
  const [stats, setStats] = useState<InboxStats>(emptyStats);
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [message, setMessage] = useState("");
  const [parseMessage, setParseMessage] = useState("");
  const [url, setUrl] = useState("");
  const [parsed, setParsed] = useState<ParsedLinkMeta | null>(null);
  const [form, setForm] = useState({
    platform: "xiaohongshu",
    source_url: "",
    title: "",
    content: "",
    author: "",
    category: "",
    manual_note: "",
    source_type: "paste",
  });

  async function refreshData() {
    const [statsData, listData] = await Promise.all([
      getInboxStats().catch(() => emptyStats),
      listInboxItems({ limit: 20 }).catch(() => []),
    ]);
    setStats(statsData || emptyStats);
    setItems(listData || []);
  }

  useEffect(() => {
    async function run() {
      try {
        await refreshData();
      } finally {
        setLoading(false);
      }
    }

    run();
  }, []);

  async function onParse(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setParsing(true);
    setParseMessage("");
    try {
      const data = await parseLink(url.trim());
      setParsed(data);
      setForm((current) => ({
        ...current,
        platform: data.platform || current.platform,
        source_url: data.source_url || current.source_url,
        title: data.detected_title || current.title,
        content: data.detected_content || current.content,
        author: data.detected_author || current.author,
        source_type: "link",
      }));
      setParseMessage(data.message || "解析完成");
    } catch (err: any) {
      setParseMessage(err?.response?.data?.detail || "链接解析失败");
    } finally {
      setParsing(false);
    }
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      await createInboxItem({
        ...form,
        source_url: form.source_url || undefined,
        author: form.author || undefined,
        category: form.category || undefined,
        manual_note: form.manual_note || undefined,
        tags: [],
      });
      setMessage("采集内容已送入收件箱，等待分拣入库");
      setUrl("");
      setParsed(null);
      setForm({
        platform: "xiaohongshu",
        source_url: "",
        title: "",
        content: "",
        author: "",
        category: "",
        manual_note: "",
        source_type: "paste",
      });
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "保存失败");
    } finally {
      setSaving(false);
    }
  }

  const topPlatforms = Object.entries(stats.by_platform || {}).slice(0, 4);

  return (
    <div className="page grid">
      <h2>采集中心</h2>

      {loading ? (
        <div className="card">加载中...</div>
      ) : (
        <>
          <section className="grid cards">
            <div className="card">
              <h3>收件箱总量</h3>
              <div className="big-number">{stats.total}</div>
            </div>
            <div className="card">
              <h3>待分拣</h3>
              <div className="big-number">{stats.pending}</div>
            </div>
            <div className="card">
              <h3>平台分布</h3>
              <div className="muted">
                {topPlatforms.length
                  ? topPlatforms.map(([name, count]) => `${name} ${count}`).join(" / ")
                  : "暂无数据"}
              </div>
            </div>
          </section>

          <section className="card">
            <h3>链接解析</h3>
            <form onSubmit={onParse} className="grid">
              <div>
                <label>素材链接</label>
                <input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="粘贴小红书 / 抖音 / 知乎等链接"
                />
              </div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <button className="secondary" type="submit" disabled={parsing || !url.trim()}>
                  {parsing ? "解析中..." : "识别链接"}
                </button>
                {parseMessage && <span className="muted">{parseMessage}</span>}
              </div>
            </form>
            {parsed && (
              <div className="muted" style={{ marginTop: 12 }}>
                已识别平台：{parsed.platform_label}；请核对内容后再保存。
              </div>
            )}
          </section>

          <section className="card">
            <h3>采集入箱</h3>
            <form onSubmit={onSave} className="grid">
              <div className="form-row">
                <div>
                  <label>平台</label>
                  <select
                    value={form.platform}
                    onChange={(e) => setForm((current) => ({ ...current, platform: e.target.value }))}
                  >
                    <option value="xiaohongshu">小红书</option>
                    <option value="douyin">抖音</option>
                    <option value="zhihu">知乎</option>
                    <option value="xianyu">咸鱼</option>
                    <option value="other">其他</option>
                  </select>
                </div>
                <div>
                  <label>采集方式</label>
                  <select
                    value={form.source_type}
                    onChange={(e) => setForm((current) => ({ ...current, source_type: e.target.value }))}
                  >
                    <option value="link">链接解析</option>
                    <option value="paste">手动粘贴</option>
                    <option value="import">批量导入</option>
                    <option value="plugin">插件采集</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div>
                  <label>来源链接</label>
                  <input
                    value={form.source_url}
                    onChange={(e) => setForm((current) => ({ ...current, source_url: e.target.value }))}
                  />
                </div>
                <div>
                  <label>作者</label>
                  <input
                    value={form.author}
                    onChange={(e) => setForm((current) => ({ ...current, author: e.target.value }))}
                  />
                </div>
              </div>

              <div className="form-row">
                <div>
                  <label>标题</label>
                  <input
                    value={form.title}
                    onChange={(e) => setForm((current) => ({ ...current, title: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <label>分类</label>
                  <input
                    value={form.category}
                    onChange={(e) => setForm((current) => ({ ...current, category: e.target.value }))}
                    placeholder="可留空，由系统自动判定"
                  />
                </div>
              </div>

              <div>
                <label>正文</label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm((current) => ({ ...current, content: e.target.value }))}
                  required
                />
              </div>

              <div>
                <label>备注</label>
                <input
                  value={form.manual_note}
                  onChange={(e) => setForm((current) => ({ ...current, manual_note: e.target.value }))}
                />
              </div>

              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <button className="primary" type="submit" disabled={saving}>
                  {saving ? "提交中..." : "送入收件箱"}
                </button>
                {message && <span className="muted">{message}</span>}
              </div>
            </form>
          </section>

          <section className="card">
            <h3>最近入箱</h3>
            <div className="muted" style={{ marginBottom: 12 }}>
              当前状态：待分拣 {stats.pending} / 已分析 {stats.analyzed} / 已入库 {stats.imported}
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>平台</th>
                  <th>标题</th>
                  <th>分类</th>
                  <th>采集方式</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td>{item.platform}</td>
                    <td>{item.title}</td>
                    <td>{item.category || "-"}</td>
                    <td>{item.source_type || "paste"}</td>
                    <td>{item.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  );
}