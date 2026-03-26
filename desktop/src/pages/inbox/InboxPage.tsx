import { useEffect, useState } from "react";

import {
  approveInboxItem,
  discardInboxItem,
  listInsightTopics,
  listMaterialInbox,
  toNegativeCaseInboxItem,
  toTopicInboxItem,
} from "../../lib/api";

type InboxRow = {
  id: number;
  source_channel: string;
  source_task_id?: number | null;
  source_submission_id?: number | null;
  platform: string;
  title?: string | null;
  author?: string | null;
  content?: string | null;
  url?: string | null;
  like_count: number;
  comment_count: number;
  collect_count: number;
  share_count: number;
  status: string;
  submitted_by_employee_id?: number | null;
  remark?: string | null;
  created_at?: string | null;
};

type Topic = { id: number; name: string };

const SOURCE_CHANNEL_LABELS: Record<string, string> = {
  collect_task: "关键词采集",
  employee_submission: "员工提交",
  wechat_robot: "微信机器人",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "待处理",
  approved: "已入素材库",
  topic: "已转选题池",
  negative_case: "已转反例库",
  discarded: "已丢弃",
};

const PLATFORM_LABELS: Record<string, string> = {
  xiaohongshu: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
  gongzhonghao: "公众号",
  weibo: "微博",
  bilibili: "B站",
  kuaishou: "快手",
  xianyu: "咸鱼",
  other: "其他",
};

const STATUS_OPTIONS = ["pending", "approved", "topic", "negative_case", "discarded"];
const PLATFORM_OPTIONS = ["xiaohongshu", "douyin", "zhihu", "gongzhonghao", "weibo", "bilibili", "kuaishou", "other"];
const SOURCE_OPTIONS = ["collect_task", "employee_submission", "wechat_robot"];

// 转选题池时用的内联弹层状态
type TopicDialog = { inboxId: number } | null;

export function InboxPage() {
  const [items, setItems] = useState<InboxRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  // 筛选
  const [filterStatus, setFilterStatus] = useState("");
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterChannel, setFilterChannel] = useState("");

  // 转选题池弹层
  const [topicDialog, setTopicDialog] = useState<TopicDialog>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<number | "">("");
  const [topicsLoading, setTopicsLoading] = useState(false);

  async function loadItems() {
    setLoading(true);
    try {
      const data = await listMaterialInbox({
        status: filterStatus || undefined,
        platform: filterPlatform || undefined,
        source_channel: filterChannel || undefined,
        limit: 100,
      });
      setItems(data || []);
    } catch {
      setMessage("加载收件箱失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadItems();
  }, [filterStatus, filterPlatform, filterChannel]);

  async function handleApprove(id: number) {
    setBusyId(id);
    setMessage("");
    try {
      await approveInboxItem(id);
      setMessage(`#${id} 已通过审核，已入素材库`);
      await loadItems();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || `#${id} 操作失败`);
    } finally {
      setBusyId(null);
    }
  }

  async function handleDiscard(id: number) {
    setBusyId(id);
    setMessage("");
    try {
      await discardInboxItem(id);
      setMessage(`#${id} 已丢弃`);
      await loadItems();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || `#${id} 操作失败`);
    } finally {
      setBusyId(null);
    }
  }

  async function handleNegativeCase(id: number) {
    setBusyId(id);
    setMessage("");
    try {
      await toNegativeCaseInboxItem(id);
      setMessage(`#${id} 已标记为反案例`);
      await loadItems();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || `#${id} 操作失败`);
    } finally {
      setBusyId(null);
    }
  }

  async function openTopicDialog(id: number) {
    setTopicDialog({ inboxId: id });
    setSelectedTopicId("");
    if (topics.length === 0) {
      setTopicsLoading(true);
      try {
        const data = await listInsightTopics();
        setTopics(Array.isArray(data) ? data : []);
      } catch {
        setTopics([]);
      } finally {
        setTopicsLoading(false);
      }
    }
  }

  async function handleToTopic() {
    if (!topicDialog || !selectedTopicId) return;
    const { inboxId } = topicDialog;
    setBusyId(inboxId);
    setMessage("");
    setTopicDialog(null);
    try {
      await toTopicInboxItem(inboxId, Number(selectedTopicId));
      setMessage(`#${inboxId} 已转选题池`);
      await loadItems();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || `#${inboxId} 操作失败`);
    } finally {
      setBusyId(null);
    }
  }

  const pendingCount = items.filter((i) => i.status === "pending").length;

  return (
    <div className="page grid">
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h2 style={{ margin: 0 }}>收件箱</h2>
        {pendingCount > 0 && (
          <span
            style={{
              background: "var(--brand)",
              color: "#fff",
              borderRadius: 12,
              padding: "2px 10px",
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            {pendingCount} 待处理
          </span>
        )}
      </div>

      {/* 筛选栏 */}
      <section className="card">
        <div className="form-row" style={{ alignItems: "end", flexWrap: "wrap", gap: 12 }}>
          <div>
            <label>状态</label>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">全部状态</option>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{STATUS_LABELS[s] ?? s}</option>
              ))}
            </select>
          </div>
          <div>
            <label>平台</label>
            <select value={filterPlatform} onChange={(e) => setFilterPlatform(e.target.value)}>
              <option value="">全部平台</option>
              {PLATFORM_OPTIONS.map((p) => (
                <option key={p} value={p}>{PLATFORM_LABELS[p] ?? p}</option>
              ))}
            </select>
          </div>
          <div>
            <label>来源渠道</label>
            <select value={filterChannel} onChange={(e) => setFilterChannel(e.target.value)}>
              <option value="">全部渠道</option>
              {SOURCE_OPTIONS.map((c) => (
                <option key={c} value={c}>{SOURCE_CHANNEL_LABELS[c] ?? c}</option>
              ))}
            </select>
          </div>
          <div>
            <button className="ghost" type="button" onClick={() => { setFilterStatus(""); setFilterPlatform(""); setFilterChannel(""); }}>
              重置筛选
            </button>
          </div>
        </div>
        {message && (
          <div style={{ marginTop: 10, fontSize: 13, color: message.includes("失败") ? "var(--danger)" : "var(--ok)" }}>
            {message}
          </div>
        )}
      </section>

      {/* 列表 */}
      <section className="card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>标题</th>
              <th>作者</th>
              <th>来源渠道</th>
              <th style={{ textAlign: "center" }}>👍/💬/⭐</th>
              <th>状态</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} style={{ textAlign: "center", padding: 24 }}>加载中…</td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: "center", padding: 24 }} className="muted">
                  暂无数据
                </td>
              </tr>
            ) : (
              items.map((item) => {
                const busy = busyId === item.id;
                const isPending = item.status === "pending";
                return (
                  <tr key={item.id}>
                    <td style={{ fontSize: 12 }} className="muted">{item.id}</td>
                    <td>{PLATFORM_LABELS[item.platform] ?? item.platform}</td>
                    <td style={{ maxWidth: 220 }}>
                      {item.url ? (
                        <a href={item.url} target="_blank" rel="noreferrer noopener" style={{ color: "var(--brand-2)" }}>
                          {item.title || "(无标题)"}
                        </a>
                      ) : (
                        <span>{item.title || "(无标题)"}</span>
                      )}
                    </td>
                    <td className="muted" style={{ fontSize: 13 }}>{item.author || "-"}</td>
                    <td style={{ fontSize: 13 }}>{SOURCE_CHANNEL_LABELS[item.source_channel] ?? item.source_channel}</td>
                    <td style={{ textAlign: "center", fontSize: 12 }} className="muted">
                      {item.like_count} / {item.comment_count} / {item.collect_count}
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: 12,
                          padding: "2px 8px",
                          borderRadius: 6,
                          background: item.status === "pending" ? "#fff3cd" : item.status === "approved" ? "#d4edda" : "#e2e3e5",
                          color: item.status === "pending" ? "#856404" : item.status === "approved" ? "#155724" : "#495057",
                        }}
                      >
                        {STATUS_LABELS[item.status] ?? item.status}
                      </span>
                    </td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {item.created_at ? item.created_at.slice(0, 10) : "-"}
                    </td>
                    <td>
                      {isPending ? (
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          <button
                            className="secondary"
                            type="button"
                            disabled={busy}
                            onClick={() => handleApprove(item.id)}
                            style={{ fontSize: 12, padding: "4px 8px" }}
                          >
                            通过
                          </button>
                          <button
                            className="ghost"
                            type="button"
                            disabled={busy}
                            onClick={() => openTopicDialog(item.id)}
                            style={{ fontSize: 12, padding: "4px 8px" }}
                          >
                            转选题池
                          </button>
                          <button
                            className="ghost"
                            type="button"
                            disabled={busy}
                            onClick={() => handleNegativeCase(item.id)}
                            style={{ fontSize: 12, padding: "4px 8px" }}
                          >
                            反案例
                          </button>
                          <button
                            className="ghost"
                            type="button"
                            disabled={busy}
                            onClick={() => handleDiscard(item.id)}
                            style={{ fontSize: 12, padding: "4px 8px", color: "var(--muted)" }}
                          >
                            丢弃
                          </button>
                        </div>
                      ) : (
                        <span className="muted" style={{ fontSize: 12 }}>已处理</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </section>

      {/* 转选题池弹层 */}
      {topicDialog && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setTopicDialog(null); }}
        >
          <div
            style={{
              background: "var(--panel)",
              borderRadius: "var(--radius)",
              padding: 28,
              minWidth: 340,
              maxWidth: 480,
              boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
            }}
          >
            <h3 style={{ margin: "0 0 16px" }}>转选题池 — 收件箱 #{topicDialog.inboxId}</h3>
            {topicsLoading ? (
              <div className="muted">加载主题列表中…</div>
            ) : topics.length === 0 ? (
              <div className="muted" style={{ fontSize: 13 }}>
                暂无可用主题，请先在「爆款洞察」中创建主题，再回来操作。
              </div>
            ) : (
              <>
                <div style={{ marginBottom: 16 }}>
                  <label>选择主题 *</label>
                  <select
                    value={selectedTopicId}
                    onChange={(e) => setSelectedTopicId(e.target.value === "" ? "" : Number(e.target.value))}
                    style={{ width: "100%" }}
                  >
                    <option value="">— 请选择主题 —</option>
                    {topics.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button className="ghost" type="button" onClick={() => setTopicDialog(null)}>取消</button>
                  <button
                    className="secondary"
                    type="button"
                    disabled={!selectedTopicId}
                    onClick={handleToTopic}
                  >
                    确认转入
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
