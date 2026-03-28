import { FormEvent, useState } from "react";

import { createKeywordCollectTask, submitEmployeeLink } from "../../lib/api";

const PLATFORMS: [string, string][] = [
  ["xiaohongshu", "小红书"],
  ["douyin", "抖音"],
  ["zhihu", "知乎"],
  ["bilibili", "B站"],
  ["weibo", "微博"],
  ["kuaishou", "快手"],
];

type Tab = "link" | "keyword";

export function CollectCenterPage() {
  const [tab, setTab] = useState<Tab>("link");

  // 贴链接提交
  const [lUrl, setLUrl] = useState("");
  const [lNote, setLNote] = useState("");
  const [lLoading, setLLoading] = useState(false);
  const [lResult, setLResult] = useState<{ submission_id: number; status: string } | null>(null);
  const [lError, setLError] = useState("");

  // 关键词批量采集
  const [kPlatform, setKPlatform] = useState("xiaohongshu");
  const [kKeyword, setKKeyword] = useState("");
  const [kMaxItems, setKMaxItems] = useState(20);
  const [kLoading, setKLoading] = useState(false);
  const [kResult, setKResult] = useState<{
    task_id: number;
    status: string;
    result_count: number;
    inserted: number;
    review: number;
    discard: number;
    duplicate: number;
    failed: number;
  } | null>(null);
  const [kError, setKError] = useState("");

  async function onLinkSubmit(e: FormEvent) {
    e.preventDefault();
    if (!lUrl.trim()) return;
    setLLoading(true);
    setLError("");
    setLResult(null);
    try {
      const result = await submitEmployeeLink({ url: lUrl.trim(), note: lNote.trim() || undefined });
      setLResult(result);
      setLUrl("");
      setLNote("");
    } catch (err: any) {
      setLError(err?.response?.data?.detail || "提交失败，请稍后重试");
    } finally {
      setLLoading(false);
    }
  }

  async function onKeywordSubmit(e: FormEvent) {
    e.preventDefault();
    if (!kKeyword.trim()) return;
    setKLoading(true);
    setKError("");
    setKResult(null);
    try {
      const result = await createKeywordCollectTask({
        platform: kPlatform,
        keyword: kKeyword.trim(),
        max_items: kMaxItems,
      });
      setKResult(result);
    } catch (err: any) {
      setKError(err?.response?.data?.detail || "采集失败，请稍后重试");
    } finally {
      setKLoading(false);
    }
  }

  return (
    <div className="page grid">
      <h2>采集中心</h2>
      <p className="muted" style={{ marginTop: 0, marginBottom: 16, fontSize: 13 }}>
        采集结果统一进入收件箱，在<a href="/inbox" style={{ color: "var(--brand)" }}>收件箱</a>中审核后方可入素材库。当前默认会执行详情补采（need_detail=true）。
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button
          className={tab === "link" ? "secondary" : "ghost"}
          type="button"
          onClick={() => setTab("link")}
        >
          贴链接提交
        </button>
        <button
          className={tab === "keyword" ? "secondary" : "ghost"}
          type="button"
          onClick={() => setTab("keyword")}
        >
          关键词批量采集
        </button>
      </div>

      {tab === "link" && (
        <section className="card">
          <h3 style={{ marginBottom: 12 }}>贴链接提交</h3>
          <p className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
            粘贴小红书/抖音/知乎等平台内容链接，采集服务将自动解析内容并放入收件箱。
          </p>
          <form onSubmit={onLinkSubmit} className="grid">
            <div>
              <label>内容链接 *</label>
              <input
                type="url"
                placeholder="https://www.xiaohongshu.com/..."
                value={lUrl}
                onChange={(e) => setLUrl(e.target.value)}
                required
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label>备注（可选）</label>
              <textarea
                rows={2}
                placeholder="说明来源或用途"
                value={lNote}
                onChange={(e) => setLNote(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <button className="secondary" type="submit" disabled={lLoading || !lUrl.trim()}>
                {lLoading ? "采集中…" : "提交采集"}
              </button>
            </div>
          </form>
          {lError && (
            <div style={{ color: "var(--danger)", marginTop: 12, fontSize: 13 }}>{lError}</div>
          )}
          {lResult && (
            <div style={{ marginTop: 12, padding: 12, background: "var(--bg-2)", borderRadius: 8, fontSize: 13 }}>
              <div style={{ color: "var(--ok)", fontWeight: 600, marginBottom: 4 }}>✓ 提交成功</div>
              <div className="muted">提交 ID：{lResult.submission_id}，状态：{lResult.status}</div>
              <div className="muted">
                → 前往 <a href="/inbox" style={{ color: "var(--brand)" }}>收件箱</a> 审核
              </div>
            </div>
          )}
        </section>
      )}

      {tab === "keyword" && (
        <section className="card">
          <h3 style={{ marginBottom: 12 }}>关键词批量采集</h3>
          <p className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
            按关键词批量抓取平台内容，采集结果自动进入收件箱待审核。默认补采详情页后再入库，耗时 30~120 秒，请耐心等待。
          </p>
          <form onSubmit={onKeywordSubmit} className="grid">
            <div className="form-row">
              <div>
                <label>平台</label>
                <select value={kPlatform} onChange={(e) => setKPlatform(e.target.value)}>
                  {PLATFORMS.map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label>关键词 *</label>
                <input
                  type="text"
                  placeholder="例：信用卡逾期 贷款攻略"
                  value={kKeyword}
                  onChange={(e) => setKKeyword(e.target.value)}
                  required
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <label>数量上限</label>
                <select value={kMaxItems} onChange={(e) => setKMaxItems(Number(e.target.value))}>
                  {[10, 20, 30, 50].map((n) => (
                    <option key={n} value={n}>{n} 条</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <button className="secondary" type="submit" disabled={kLoading || !kKeyword.trim()}>
                {kLoading ? "采集中，请耐心等待…" : "开始采集"}
              </button>
            </div>
          </form>
          {kError && (
            <div style={{ color: "var(--danger)", marginTop: 12, fontSize: 13 }}>{kError}</div>
          )}
          {kResult && (
            <div style={{ marginTop: 12, padding: 12, background: "var(--bg-2)", borderRadius: 8, fontSize: 13 }}>
              <div style={{ color: "var(--ok)", fontWeight: 600, marginBottom: 4 }}>✓ 采集完成</div>
              <div className="muted" style={{ marginBottom: 8 }}>
                任务 ID：{kResult.task_id}，采集状态：{kResult.status}，抓取总量：{kResult.result_count}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8 }}>
                <div style={{ padding: "8px 10px", borderRadius: 8, background: "#e8f5e9" }}>
                  <div style={{ fontSize: 12, color: "#2e7d32" }}>pending</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#1b5e20" }}>{kResult.inserted}</div>
                </div>
                <div style={{ padding: "8px 10px", borderRadius: 8, background: "#fff8e1" }}>
                  <div style={{ fontSize: 12, color: "#f57f17" }}>review</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#e65100" }}>{kResult.review}</div>
                </div>
                <div style={{ padding: "8px 10px", borderRadius: 8, background: "#f5f5f5" }}>
                  <div style={{ fontSize: 12, color: "#616161" }}>discard</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#424242" }}>{kResult.discard}</div>
                </div>
                <div style={{ padding: "8px 10px", borderRadius: 8, background: "#ffebee" }}>
                  <div style={{ fontSize: 12, color: "#c62828" }}>duplicate</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#b71c1c" }}>{kResult.duplicate}</div>
                </div>
                <div style={{ padding: "8px 10px", borderRadius: 8, background: "#ede7f6" }}>
                  <div style={{ fontSize: 12, color: "#5e35b1" }}>failed</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#4527a0" }}>{kResult.failed}</div>
                </div>
              </div>
              <div className="muted">
                → 前往 <a href="/inbox" style={{ color: "var(--brand)" }}>收件箱</a> 审核
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
