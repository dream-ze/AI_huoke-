import { useEffect, useState } from "react";

import {
  analyzeInboxItem,
  discardInboxItem,
  getInboxStats,
  listInboxItems,
  promoteInboxItem,
} from "../../lib/api";
import { InboxItem, InboxStats } from "../../types";

const emptyStats: InboxStats = {
  total: 0,
  pending: 0,
  analyzed: 0,
  imported: 0,
  discarded: 0,
  by_platform: {},
};

export function InboxPage() {
  const [stats, setStats] = useState<InboxStats>(emptyStats);
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState("");

  async function refreshData() {
    const [statsData, listData] = await Promise.all([
      getInboxStats().catch(() => emptyStats),
      listInboxItems({ limit: 50 }).catch(() => []),
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

  async function handleAnalyze(itemId: number) {
    setBusyId(itemId);
    setMessage("");
    try {
      await analyzeInboxItem(itemId);
      setMessage(`已完成收件箱条目 #${itemId} 的 AI 分析`);
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "AI 分析失败");
    } finally {
      setBusyId(null);
    }
  }

  async function handlePromote(itemId: number) {
    setBusyId(itemId);
    setMessage("");
    try {
      const data = await promoteInboxItem(itemId);
      setMessage(`条目 #${itemId} 已入库为素材 #${data.content_asset_id}`);
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "入库失败");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDiscard(itemId: number) {
    setBusyId(itemId);
    setMessage("");
    try {
      await discardInboxItem(itemId, "人工判定不入库");
      setMessage(`条目 #${itemId} 已丢弃`);
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "丢弃失败");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page grid">
      <h2>素材收件箱</h2>

      {loading ? (
        <div className="card">加载中...</div>
      ) : (
        <>
          <section className="grid cards">
            <div className="card">
              <h3>待分拣</h3>
              <div className="big-number">{stats.pending}</div>
            </div>
            <div className="card">
              <h3>已分析</h3>
              <div className="big-number">{stats.analyzed}</div>
            </div>
            <div className="card">
              <h3>已入库</h3>
              <div className="big-number">{stats.imported}</div>
            </div>
          </section>

          <section className="card">
            <h3>分拣队列</h3>
            {message && <div className="muted" style={{ marginBottom: 12 }}>{message}</div>}
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>平台</th>
                  <th>标题</th>
                  <th>分类</th>
                  <th>热度</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const busy = busyId === item.id;
                  const disabled = busy || item.status === "discarded" || item.status === "imported";
                  return (
                    <tr key={item.id}>
                      <td>{item.id}</td>
                      <td>{item.platform}</td>
                      <td>{item.title}</td>
                      <td>{item.category || "-"}</td>
                      <td>{item.heat_score}</td>
                      <td>{item.status}</td>
                      <td>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <button
                            className="ghost"
                            type="button"
                            disabled={disabled}
                            onClick={() => handleAnalyze(item.id)}
                          >
                            {busy ? "处理中..." : "AI分析"}
                          </button>
                          <button
                            className="secondary"
                            type="button"
                            disabled={disabled}
                            onClick={() => handlePromote(item.id)}
                          >
                            入素材库
                          </button>
                          <button
                            className="ghost"
                            type="button"
                            disabled={disabled}
                            onClick={() => handleDiscard(item.id)}
                          >
                            丢弃
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  );
}