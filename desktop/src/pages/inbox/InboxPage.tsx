import { useEffect, useMemo, useState } from "react";

import {
  adoptGenerationVersion,
  getCollectDetail,
  listMaterialInbox,
  rewriteCollect,
  updateMaterialInboxStatus,
} from "../../lib/api";
import { CollectDetail, CollectGenerationTask } from "../../types";
import { copyToClipboard } from "../../utils/clipboard";

type InboxRow = {
  id: number;
  source_channel: string;
  source_task_id?: number | null;
  source_submission_id?: number | null;
  platform: string;
  source_id?: string | null;
  keyword?: string | null;
  title?: string | null;
  author?: string | null;
  content?: string | null;
  url?: string | null;
  cover_url?: string | null;
  like_count: number;
  comment_count: number;
  collect_count: number;
  share_count: number;
  parse_status: string;
  risk_status: string;
  quality_score: number;
  relevance_score: number;
  lead_score: number;
  is_duplicate: boolean;
  filter_reason?: string | null;
  status: string;
  submitted_by_employee_id?: number | null;
  remark?: string | null;
  review_note?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type RewriteCopy = {
  variant_name: string;
  title: string;
  content: string;
  hashtags: string[];
  compliance?: {
    corrected?: boolean;
    is_compliant?: boolean;
    risk_level?: string;
    risk_score?: number;
    publish_blocked?: boolean;
    suggestions?: string[];
  };
};

const SOURCE_CHANNEL_LABELS: Record<string, string> = {
  collect_task: "关键词采集",
  employee_submission: "员工提交",
  wechat_robot: "微信机器人",
  manual_input: "手动录入",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "待处理",
  review: "待审核",
  discard: "已丢弃",
};

const RISK_LABELS: Record<string, string> = {
  safe: "安全",
  review: "待审",
  medium: "中风险",
  blocked: "拦截",
  high: "高风险",
  reject: "拒绝",
};

const FILTER_REASON_LABELS: Record<string, string> = {
  passed: "通过过滤",
  detail_not_complete: "详情不完整",
  risk_need_review: "风险待审",
  quality_need_review: "质量待审",
  lead_need_review: "线索待审",
  low_quality: "质量过低",
  irrelevant: "业务无关",
  duplicate: "重复内容",
  missing_platform: "缺少平台",
  missing_source_id: "缺少来源ID",
  missing_url: "缺少链接",
  missing_title_and_content: "标题和正文都为空",
  manual_input: "手动录入",
  risk_blocked: "风险拦截",
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

const STATUS_OPTIONS = ["pending", "review", "discard"];
const PLATFORM_OPTIONS = ["xiaohongshu", "douyin", "zhihu", "gongzhonghao", "weibo", "bilibili", "kuaishou", "other"];
const SOURCE_OPTIONS = ["collect_task", "employee_submission", "wechat_robot", "manual_input"];
const RISK_OPTIONS = ["safe", "review", "medium", "blocked", "high", "reject"];

function statusColor(status: string) {
  if (status === "pending") {
    return { background: "#d8f3dc", color: "#1b4332" };
  }
  if (status === "review") {
    return { background: "#fff3cd", color: "#856404" };
  }
  return { background: "#f1f3f5", color: "#495057" };
}

export function InboxPage() {
  const [items, setItems] = useState<InboxRow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState<CollectDetail | null>(null);
  const [rewriteLoading, setRewriteLoading] = useState(false);
  const [rewritePlatform, setRewritePlatform] = useState<"xiaohongshu" | "douyin" | "zhihu">("xiaohongshu");
  const [rewriteCopies, setRewriteCopies] = useState<RewriteCopy[]>([]);
  const [compareLeftId, setCompareLeftId] = useState<number | null>(null);
  const [compareRightId, setCompareRightId] = useState<number | null>(null);
  const [adoptLoading, setAdoptLoading] = useState<number | null>(null);

  const [filterStatus, setFilterStatus] = useState("");
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterChannel, setFilterChannel] = useState("");
  const [filterKeyword, setFilterKeyword] = useState("");
  const [filterRiskStatus, setFilterRiskStatus] = useState("");
  const [filterDuplicate, setFilterDuplicate] = useState("");

  async function loadItems() {
    setLoading(true);
    try {
      const data = await listMaterialInbox({
        status: filterStatus || undefined,
        platform: filterPlatform || undefined,
        source_channel: filterChannel || undefined,
        keyword: filterKeyword || undefined,
        risk_status: filterRiskStatus || undefined,
        is_duplicate: filterDuplicate === "" ? undefined : filterDuplicate === "true",
        limit: 100,
      });
      const rows = data || [];
      setItems(rows);
      if (rows.length === 0) {
        setSelectedId(null);
      } else if (!selectedId || !rows.some((row) => row.id === selectedId)) {
        setSelectedId(rows[0].id);
      }
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "加载收件箱失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(id: number) {
    setDetailLoading(true);
    try {
      const payload = await getCollectDetail(id);
      setDetail(payload);
      const generations = payload?.generation_tasks || [];
      if (generations.length >= 2) {
        setCompareLeftId(generations[0].generation_task_id);
        setCompareRightId(generations[1].generation_task_id);
      } else if (generations.length === 1) {
        setCompareLeftId(generations[0].generation_task_id);
        setCompareRightId(null);
      } else {
        setCompareLeftId(null);
        setCompareRightId(null);
      }
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "加载素材详情失败");
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    loadItems();
  }, [filterStatus, filterPlatform, filterChannel, filterRiskStatus, filterDuplicate]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    setRewriteCopies([]);
    loadDetail(selectedId);
  }, [selectedId]);

  async function applyStatus(id: number, status: "pending" | "review" | "discard", reviewNote: string) {
    setBusyId(id);
    setMessage("");
    try {
      await updateMaterialInboxStatus(id, { status, review_note: reviewNote });
      setMessage(`#${id} 已更新为${STATUS_LABELS[status] ?? status}`);
      await loadItems();
      if (selectedId === id) {
        await loadDetail(id);
      }
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || `#${id} 更新失败`);
    } finally {
      setBusyId(null);
    }
  }

  async function onRewrite() {
    if (!selectedId) return;
    setRewriteLoading(true);
    setMessage("");
    try {
      const result = await rewriteCollect(selectedId, rewritePlatform);
      setRewriteCopies(Array.isArray(result?.copies) ? result.copies : []);
      setMessage("改写已完成，结果已进入历史记录");
      await loadDetail(selectedId);
      await loadItems();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "改写失败");
    } finally {
      setRewriteLoading(false);
    }
  }

  async function onAdoptVersion(generationTaskId: number) {
    if (!selectedId) return;
    setAdoptLoading(generationTaskId);
    setMessage("");
    try {
      await adoptGenerationVersion(selectedId, generationTaskId, "收件箱一键回滚/采纳");
      setMessage("已采纳所选版本并更新当前素材正文");
      await loadDetail(selectedId);
      await loadItems();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "采纳失败");
    } finally {
      setAdoptLoading(null);
    }
  }

  const pendingCount = items.filter((item) => item.status === "pending").length;
  const reviewCount = items.filter((item) => item.status === "review").length;
  const selectedItem = items.find((item) => item.id === selectedId) || null;

  const generationTasks = detail?.generation_tasks || [];
  const compareLeft = generationTasks.find((task) => task.generation_task_id === compareLeftId) || null;
  const compareRight = generationTasks.find((task) => task.generation_task_id === compareRightId) || null;
  const adoptedTaskId = generationTasks.find((task) => task.adoption_status === "adopted")?.generation_task_id;

  const variantsFromLatest = useMemo(() => {
    if (generationTasks.length === 0) return [] as RewriteCopy[];
    const latest = generationTasks[0];
    const copies = latest.copies;
    if (!Array.isArray(copies) || copies.length === 0) return [] as RewriteCopy[];
    return copies as RewriteCopy[];
  }, [generationTasks]);

  return (
    <div className="page grid">
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>收件箱</h2>
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
        <span
          style={{
            background: "#f4a261",
            color: "#1f2937",
            borderRadius: 12,
            padding: "2px 10px",
            fontSize: 13,
            fontWeight: 700,
          }}
        >
          {reviewCount} 待审核
        </span>
      </div>

      <section className="card">
        <div className="form-row" style={{ alignItems: "end", flexWrap: "wrap", gap: 12 }}>
          <div>
            <label>状态</label>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">全部状态</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>{STATUS_LABELS[status] ?? status}</option>
              ))}
            </select>
          </div>
          <div>
            <label>平台</label>
            <select value={filterPlatform} onChange={(e) => setFilterPlatform(e.target.value)}>
              <option value="">全部平台</option>
              {PLATFORM_OPTIONS.map((platform) => (
                <option key={platform} value={platform}>{PLATFORM_LABELS[platform] ?? platform}</option>
              ))}
            </select>
          </div>
          <div>
            <label>来源渠道</label>
            <select value={filterChannel} onChange={(e) => setFilterChannel(e.target.value)}>
              <option value="">全部渠道</option>
              {SOURCE_OPTIONS.map((channel) => (
                <option key={channel} value={channel}>{SOURCE_CHANNEL_LABELS[channel] ?? channel}</option>
              ))}
            </select>
          </div>
          <div>
            <label>风险状态</label>
            <select value={filterRiskStatus} onChange={(e) => setFilterRiskStatus(e.target.value)}>
              <option value="">全部风险</option>
              {RISK_OPTIONS.map((risk) => (
                <option key={risk} value={risk}>{RISK_LABELS[risk] ?? risk}</option>
              ))}
            </select>
          </div>
          <div>
            <label>重复</label>
            <select value={filterDuplicate} onChange={(e) => setFilterDuplicate(e.target.value)}>
              <option value="">全部</option>
              <option value="false">非重复</option>
              <option value="true">重复</option>
            </select>
          </div>
          <div style={{ minWidth: 220 }}>
            <label>关键词</label>
            <input
              value={filterKeyword}
              onChange={(e) => setFilterKeyword(e.target.value)}
              placeholder="输入采集关键词"
            />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="secondary" type="button" onClick={() => loadItems()}>
              查询
            </button>
            <button
              className="ghost"
              type="button"
              onClick={() => {
                setFilterStatus("");
                setFilterPlatform("");
                setFilterChannel("");
                setFilterKeyword("");
                setFilterRiskStatus("");
                setFilterDuplicate("");
              }}
            >
              重置
            </button>
          </div>
        </div>
        {message && (
          <div style={{ marginTop: 10, fontSize: 13, color: message.includes("失败") ? "var(--danger)" : "var(--ok)" }}>
            {message}
          </div>
        )}
      </section>

      <section className="card" style={{ padding: 0 }}>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 0 }}>
          <div style={{ overflowX: "auto", borderRight: "1px solid var(--border)" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>标题 / 正文</th>
                  <th>平台 / 作者</th>
                  <th>关键词 / 来源</th>
                  <th>评分</th>
                  <th>技术状态</th>
                  <th>业务状态</th>
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
                    <td colSpan={9} style={{ textAlign: "center", padding: 24 }} className="muted">暂无数据</td>
                  </tr>
                ) : (
                  items.map((item) => {
                    const busy = busyId === item.id;
                    const colors = statusColor(item.status);
                    const isActive = selectedId === item.id;
                    return (
                      <tr
                        key={item.id}
                        onClick={() => setSelectedId(item.id)}
                        style={{ background: isActive ? "#f6fbff" : "transparent", cursor: "pointer" }}
                      >
                        <td className="muted" style={{ fontSize: 12 }}>{item.id}</td>
                        <td style={{ minWidth: 280, maxWidth: 360 }}>
                          <div style={{ fontWeight: 700, marginBottom: 6 }}>
                            {item.url ? (
                              <a href={item.url} target="_blank" rel="noreferrer noopener" style={{ color: "var(--brand-2)" }}>
                                {item.title || "(无标题)"}
                              </a>
                            ) : (
                              item.title || "(无标题)"
                            )}
                          </div>
                          <div className="muted" style={{ fontSize: 12, lineHeight: 1.5 }}>
                            {(item.content || "").slice(0, 120) || "无正文"}
                          </div>
                          <div style={{ marginTop: 8, fontSize: 12, display: "flex", gap: 6, flexWrap: "wrap" }}>
                            <span className="muted">👍 {item.like_count}</span>
                            <span className="muted">💬 {item.comment_count}</span>
                            <span className="muted">⭐ {item.collect_count}</span>
                            {item.is_duplicate && (
                              <span style={{ background: "#fde2e4", color: "#9d0208", borderRadius: 6, padding: "2px 6px" }}>
                                重复
                              </span>
                            )}
                          </div>
                        </td>
                        <td style={{ minWidth: 120 }}>
                          <div>{PLATFORM_LABELS[item.platform] ?? item.platform}</div>
                          <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>{item.author || "-"}</div>
                        </td>
                        <td style={{ minWidth: 160 }}>
                          <div>{item.keyword || "-"}</div>
                          <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                            {SOURCE_CHANNEL_LABELS[item.source_channel] ?? item.source_channel}
                          </div>
                        </td>
                        <td style={{ minWidth: 120, fontSize: 12 }}>
                          <div>质量 {item.quality_score}</div>
                          <div>相关 {item.relevance_score}</div>
                          <div>线索 {item.lead_score}</div>
                        </td>
                        <td style={{ minWidth: 150, fontSize: 12 }}>
                          <div>解析: {item.parse_status}</div>
                          <div style={{ marginTop: 6 }}>风险: {RISK_LABELS[item.risk_status] ?? item.risk_status}</div>
                          <div className="muted" style={{ marginTop: 6 }}>
                            {FILTER_REASON_LABELS[item.filter_reason || ""] ?? item.filter_reason ?? "-"}
                          </div>
                        </td>
                        <td style={{ minWidth: 110 }}>
                          <span
                            style={{
                              fontSize: 12,
                              padding: "2px 8px",
                              borderRadius: 6,
                              background: colors.background,
                              color: colors.color,
                            }}
                          >
                            {STATUS_LABELS[item.status] ?? item.status}
                          </span>
                        </td>
                        <td className="muted" style={{ fontSize: 12 }}>
                          {item.created_at ? item.created_at.slice(0, 10) : "-"}
                        </td>
                        <td style={{ minWidth: 160 }}>
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            {item.status !== "pending" && (
                              <button
                                className="secondary"
                                type="button"
                                disabled={busy}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  applyStatus(item.id, "pending", "转为待处理");
                                }}
                                style={{ fontSize: 12, padding: "4px 8px" }}
                              >
                                设为待处理
                              </button>
                            )}
                            {item.status !== "review" && (
                              <button
                                className="ghost"
                                type="button"
                                disabled={busy}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  applyStatus(item.id, "review", "转为待审核");
                                }}
                                style={{ fontSize: 12, padding: "4px 8px" }}
                              >
                                设为待审核
                              </button>
                            )}
                            {item.status !== "discard" && (
                              <button
                                className="ghost"
                                type="button"
                                disabled={busy}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  applyStatus(item.id, "discard", "标记丢弃");
                                }}
                                style={{ fontSize: 12, padding: "4px 8px", color: "var(--muted)" }}
                              >
                                标记丢弃
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <aside style={{ padding: 16, minHeight: 720, background: "#fafbfd", overflowY: "auto" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16 }}>详情与改写</h3>
            {!selectedItem ? (
              <div className="muted" style={{ fontSize: 13 }}>请选择左侧一条内容查看详情。</div>
            ) : detailLoading ? (
              <div className="muted" style={{ fontSize: 13 }}>详情加载中...</div>
            ) : (
              <div style={{ display: "grid", gap: 12, fontSize: 13 }}>
                <div>
                  <div className="muted" style={{ marginBottom: 4 }}>标题</div>
                  <div style={{ fontWeight: 700 }}>{selectedItem.title || "(无标题)"}</div>
                </div>
                <div>
                  <div className="muted" style={{ marginBottom: 4 }}>正文</div>
                  <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.65, maxHeight: 220, overflowY: "auto", background: "#fff", border: "1px solid var(--border)", borderRadius: 8, padding: 10 }}>
                    {selectedItem.content || "无正文"}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <div><div className="muted">平台</div><div>{PLATFORM_LABELS[selectedItem.platform] ?? selectedItem.platform}</div></div>
                  <div><div className="muted">作者</div><div>{selectedItem.author || "-"}</div></div>
                  <div><div className="muted">关键词</div><div>{selectedItem.keyword || "-"}</div></div>
                  <div><div className="muted">来源ID</div><div>{selectedItem.source_id || "-"}</div></div>
                </div>

                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <select
                    value={rewritePlatform}
                    onChange={(e) => setRewritePlatform(e.target.value as "xiaohongshu" | "douyin" | "zhihu")}
                    style={{ width: 140 }}
                  >
                    <option value="xiaohongshu">改写-小红书</option>
                    <option value="douyin">改写-抖音</option>
                    <option value="zhihu">改写-知乎</option>
                  </select>
                  <button className="secondary" type="button" disabled={rewriteLoading} onClick={onRewrite}>
                    {rewriteLoading ? "改写中..." : "单条一键送改写"}
                  </button>
                  <button className="ghost" type="button" onClick={() => selectedItem.url && window.open(selectedItem.url, "_blank", "noreferrer")}>打开原链接</button>
                </div>

                {(rewriteCopies.length > 0 || variantsFromLatest.length > 0) && (
                  <div className="card" style={{ padding: 10 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>三版文案</div>
                    {(rewriteCopies.length > 0 ? rewriteCopies : variantsFromLatest).map((copy, idx) => (
                      <div key={`${copy.variant_name}-${idx}`} style={{ marginBottom: 10, border: "1px solid var(--border)", borderRadius: 8, padding: 8 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                          <div>{copy.variant_name} · {copy.title}</div>
                          <button
                            className="ghost"
                            type="button"
                            onClick={() => copyToClipboard(`${copy.title}\n\n${copy.content}`)}
                            style={{ fontSize: 12, padding: "4px 8px" }}
                          >
                            复制
                          </button>
                        </div>
                        <div className="muted" style={{ marginTop: 4 }}>
                          风险：{copy.compliance?.risk_level || "low"} / 分数：{copy.compliance?.risk_score ?? "-"}
                          {copy.compliance?.publish_blocked ? " / 已阻断发布" : ""}
                        </div>
                        <textarea readOnly value={copy.content || ""} style={{ marginTop: 6 }} />
                      </div>
                    ))}
                  </div>
                )}

                <div className="card" style={{ padding: 10 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8 }}>历史版本（对比与回滚）</div>
                  {generationTasks.length === 0 ? (
                    <div className="muted">暂无改写记录</div>
                  ) : (
                    <>
                      {!!detail?.generation_variant_stats?.length && (
                        <div style={{ marginBottom: 10, display: "grid", gap: 6 }}>
                          <div className="muted">variant 采纳率</div>
                          {detail.generation_variant_stats.map((row) => (
                            <div key={row.variant_name} style={{ fontSize: 12 }}>
                              {row.variant_name}: {row.adopted}/{row.total} ({row.adoption_rate}%)
                            </div>
                          ))}
                        </div>
                      )}

                      <div style={{ display: "grid", gap: 8 }}>
                        {generationTasks.map((task: CollectGenerationTask) => (
                          <div key={task.generation_task_id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 8 }}>
                            <div className="muted" style={{ marginBottom: 6 }}>
                              #{task.generation_task_id} · {task.platform} · {task.created_at ? new Date(task.created_at).toLocaleString() : "-"} · 采纳状态: {task.adoption_status || "pending"}
                            </div>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <button className="ghost" type="button" onClick={() => setCompareLeftId(task.generation_task_id)}>设为左侧对比</button>
                              <button className="ghost" type="button" onClick={() => setCompareRightId(task.generation_task_id)}>设为右侧对比</button>
                              <button
                                className="secondary"
                                type="button"
                                disabled={adoptLoading === task.generation_task_id || adoptedTaskId === task.generation_task_id}
                                onClick={() => onAdoptVersion(task.generation_task_id)}
                              >
                                {adoptLoading === task.generation_task_id ? "处理中..." : adoptedTaskId === task.generation_task_id ? "当前生效" : "一键回滚到此版本"}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div style={{ marginTop: 10 }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                          <div>
                            <div className="muted" style={{ marginBottom: 4 }}>左侧版本 #{compareLeft?.generation_task_id || "-"}</div>
                            <textarea readOnly value={compareLeft?.output_text || ""} placeholder="选择左侧版本进行对比" />
                          </div>
                          <div>
                            <div className="muted" style={{ marginBottom: 4 }}>右侧版本 #{compareRight?.generation_task_id || "-"}</div>
                            <textarea readOnly value={compareRight?.output_text || ""} placeholder="选择右侧版本进行对比" />
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
          </aside>
        </div>
      </section>
    </div>
  );
}
