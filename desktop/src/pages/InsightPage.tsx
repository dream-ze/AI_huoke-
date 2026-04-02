import { useEffect, useRef, useState } from "react";
import {
  createInsightTopic,
  deleteInsightItem,
  getInsightStats,
  importInsightItem,
  listInsightItems,
  listInsightTopics,
  analyzeInsightItem,
  retrieveInsightContext,
} from "../lib/api";
import type { InsightTopic, InsightContentItem, InsightStats } from "../api/insightApi";

// ─── 类型 ────────────────────────────────────────────────
// 扩展 API 类型，添加页面渲染所需的计算字段
type InsightItem = InsightContentItem & {
  engagement_score?: number;
  emotion_level?: number;
  info_density?: number;
  pain_points?: string[];
  highlights?: string[];
  risk_level?: string;
  risk_flags?: string[];
  structure_type?: string;
  hook_type?: string;
  tone_style?: string;
  cta_type?: string;
  content_summary?: string;
  title_formula?: string;
};

// 扩展 InsightTopic 类型，添加页面渲染所需的字段
type ExtendedInsightTopic = InsightTopic & {
  content_count?: number;
  common_titles?: string[];
  common_pain_points?: string[];
  common_structures?: string[];
  common_ctas?: string[];
};

// ─── 常量 ────────────────────────────────────────────────
const PLATFORMS = [
  { value: "xiaohongshu", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "bilibili", label: "B站" },
  { value: "zhihu", label: "知乎" },
  { value: "weibo", label: "微博" },
  { value: "kuaishou", label: "快手" },
  { value: "other", label: "其他" },
];

const HEAT_TIER_LABEL: Record<string, string> = {
  viral: "🔥 病毒级",
  hot: "⬆️ 高热",
  warm: "📈 上升",
  normal: "📄 普通",
};

const HEAT_TIER_COLOR: Record<string, string> = {
  viral: "#a11d2f",
  hot: "#b63d1f",
  warm: "#b05a05",
  normal: "#6d5d4f",
};

const RISK_COLOR: Record<string, string> = {
  low: "var(--ok)",
  medium: "var(--warn)",
  high: "var(--danger)",
};

// ─── 公共小组件 ─────────────────────────────────────────
function Tag({ text, color }: { text: string; color?: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        background: color ? `${color}22` : "var(--bg-2)",
        color: color || "var(--muted)",
        border: `1px solid ${color ? `${color}44` : "var(--line)"}`,
        borderRadius: 6,
        padding: "2px 8px",
        fontSize: 12,
        marginRight: 4,
        marginBottom: 2,
      }}
    >
      {text}
    </span>
  );
}

function MetricBadge({ label, value }: { label: string; value: number }) {
  return (
    <span style={{ fontSize: 12, color: "var(--muted)", marginRight: 10 }}>
      {label} <strong style={{ color: "var(--text)" }}>{value.toLocaleString()}</strong>
    </span>
  );
}

// ─── 导入表单 ────────────────────────────────────────────
function ImportForm({
  topics,
  onSuccess,
}: {
  topics: InsightTopic[];
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    platform: "xiaohongshu",
    title: "",
    body_text: "",
    source_url: "",
    author_name: "",
    fans_count: "",
    account_positioning: "",
    like_count: "",
    comment_count: "",
    share_count: "",
    collect_count: "",
    view_count: "",
    topic_name: "",
    manual_note: "",
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim() || !form.body_text.trim()) {
      setMsg("标题和正文不能为空");
      return;
    }
    setSaving(true);
    setMsg("");
    try {
      await importInsightItem({
        platform: form.platform,
        title: form.title.trim(),
        body_text: form.body_text.trim(),
        source_url: form.source_url || undefined,
        author_name: form.author_name || undefined,
        fans_count: form.fans_count ? parseInt(form.fans_count) : undefined,
        account_positioning: form.account_positioning || undefined,
        like_count: parseInt(form.like_count) || 0,
        comment_count: parseInt(form.comment_count) || 0,
        share_count: parseInt(form.share_count) || 0,
        collect_count: parseInt(form.collect_count) || 0,
        view_count: parseInt(form.view_count) || 0,
        topic_name: form.topic_name || undefined,
        manual_note: form.manual_note || undefined,
      });
      setMsg("✅ 导入成功");
      setForm({
        platform: "xiaohongshu",
        title: "",
        body_text: "",
        source_url: "",
        author_name: "",
        fans_count: "",
        account_positioning: "",
        like_count: "",
        comment_count: "",
        share_count: "",
        collect_count: "",
        view_count: "",
        topic_name: "",
        manual_note: "",
      });
      onSuccess();
    } catch {
      setMsg("❌ 导入失败，请检查数据");
    } finally {
      setSaving(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "8px 10px",
    borderRadius: 8,
    border: "1px solid var(--line)",
    background: "var(--bg)",
    fontSize: 14,
    color: "var(--text)",
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
        <div>
          <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>平台 *</label>
          <select value={form.platform} onChange={(e) => set("platform", e.target.value)} style={inputStyle}>
            {PLATFORMS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>关联主题</label>
          <select value={form.topic_name} onChange={(e) => set("topic_name", e.target.value)} style={inputStyle}>
            <option value="">-- 不关联 --</option>
            {topics.map((t) => (
              <option key={t.id} value={t.name}>{t.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>账号定位</label>
          <select value={form.account_positioning} onChange={(e) => set("account_positioning", e.target.value)} style={inputStyle}>
            <option value="">-- 不指定 --</option>
            {["流量号", "专业顾问号", "案例号", "清单号", "避坑号"].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>标题 *</label>
        <input value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="内容标题" style={inputStyle} />
      </div>

      <div>
        <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>正文 *</label>
        <textarea
          value={form.body_text}
          onChange={(e) => set("body_text", e.target.value)}
          placeholder="粘贴完整正文内容"
          rows={5}
          style={{ ...inputStyle, resize: "vertical" }}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
        <div>
          <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>内容链接</label>
          <input value={form.source_url} onChange={(e) => set("source_url", e.target.value)} placeholder="https://..." style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>账号名</label>
          <input value={form.author_name} onChange={(e) => set("author_name", e.target.value)} placeholder="@账号名" style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>粉丝数</label>
          <input type="number" value={form.fans_count} onChange={(e) => set("fans_count", e.target.value)} placeholder="0" style={inputStyle} />
        </div>
      </div>

      <div>
        <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 6 }}>互动数据</label>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 8 }}>
          {["like_count", "comment_count", "share_count", "collect_count", "view_count"].map((k) => (
            <div key={k}>
              <input
                type="number"
                value={(form as any)[k]}
                onChange={(e) => set(k, e.target.value)}
                placeholder={{ like_count: "👍点赞", comment_count: "💬评论", share_count: "↗分享", collect_count: "⭐收藏", view_count: "👁浏览" }[k]}
                style={inputStyle}
              />
            </div>
          ))}
        </div>
      </div>

      <div>
        <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 4 }}>备注</label>
        <input value={form.manual_note} onChange={(e) => set("manual_note", e.target.value)} placeholder="运营备注（可选）" style={inputStyle} />
      </div>

      {msg && <div style={{ color: msg.startsWith("✅") ? "var(--ok)" : "var(--danger)", fontSize: 13 }}>{msg}</div>}

      <button type="submit" className="btn" disabled={saving} style={{ alignSelf: "flex-start" }}>
        {saving ? "导入中..." : "保存入库"}
      </button>
    </form>
  );
}

// ─── 内容卡片 ────────────────────────────────────────────
function ItemCard({
  item,
  topics,
  onAnalyze,
  onDelete,
}: {
  item: InsightItem;
  topics: InsightTopic[];
  onAnalyze: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const topic = topics.find((t) => t.id === item.topic_id);

  return (
    <div
      className="card"
      style={{
        borderLeft: `4px solid ${HEAT_TIER_COLOR[item.heat_tier || ''] || "var(--line)"}`,
        padding: "14px 16px",
      }}
    >
      {/* 顶栏 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 6 }}>
            <Tag text={PLATFORMS.find((p) => p.value === item.platform)?.label || item.platform} color="var(--brand-2)" />
            {item.heat_tier && <Tag text={HEAT_TIER_LABEL[item.heat_tier] || item.heat_tier} color={HEAT_TIER_COLOR[item.heat_tier]} />}
            {topic && <Tag text={topic.name} color="var(--brand)" />}
            {item.ai_analyzed && <Tag text="AI已分析" color="var(--ok)" />}
            {item.risk_level && item.risk_level !== "low" && (
              <Tag text={`风险:${item.risk_level}`} color={RISK_COLOR[item.risk_level]} />
            )}
          </div>
          <div style={{ fontWeight: 700, fontSize: 15, lineHeight: 1.4, cursor: "pointer" }} onClick={() => setExpanded(!expanded)}>
            {item.title || '(无标题)'}
          </div>
          {item.author_name && (
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 3 }}>@{item.author_name}</div>
          )}
        </div>
        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
          {!item.ai_analyzed && (
            <button
              className="ghost"
              style={{ fontSize: 12, padding: "4px 10px" }}
              onClick={() => onAnalyze(item.id)}
            >
              AI分析
            </button>
          )}
          <button
            className="ghost"
            style={{ fontSize: 12, padding: "4px 10px", color: "var(--danger)" }}
            onClick={() => onDelete(item.id)}
          >
            删除
          </button>
        </div>
      </div>

      {/* 互动数据 */}
      <div style={{ marginBottom: 8 }}>
        <MetricBadge label="👍" value={item.like_count} />
        <MetricBadge label="💬" value={item.comment_count} />
        <MetricBadge label="⭐" value={item.collect_count} />
        <MetricBadge label="↗" value={item.share_count} />
        <MetricBadge label="👁" value={item.view_count} />
        {item.heat_tier && (
          <span style={{ fontSize: 12, color: HEAT_TIER_COLOR[item.heat_tier], fontWeight: 700 }}>
            互动分 {item.engagement_score?.toFixed(0) ?? '-'}
          </span>
        )}
      </div>

      {/* 展开详情 */}
      {expanded && (
        <div style={{ borderTop: "1px solid var(--line)", paddingTop: 12, marginTop: 4 }}>
          {item.content_summary && (
            <div style={{ background: "var(--bg-2)", borderRadius: 8, padding: "8px 12px", fontSize: 13, marginBottom: 10 }}>
              💡 {item.content_summary}
            </div>
          )}
          {item.ai_analyzed && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 12 }}>
              {item.structure_type && (
                <div style={{ fontSize: 13 }}><span style={{ color: "var(--muted)" }}>结构：</span>{item.structure_type}</div>
              )}
              {item.hook_type && (
                <div style={{ fontSize: 13 }}><span style={{ color: "var(--muted)" }}>钩子：</span>{item.hook_type}</div>
              )}
              {item.tone_style && (
                <div style={{ fontSize: 13 }}><span style={{ color: "var(--muted)" }}>风格：</span>{item.tone_style}</div>
              )}
              {item.cta_type && (
                <div style={{ fontSize: 13 }}><span style={{ color: "var(--muted)" }}>CTA：</span>{item.cta_type}</div>
              )}
              {item.title_formula && (
                <div style={{ fontSize: 13, gridColumn: "span 2" }}>
                  <span style={{ color: "var(--muted)" }}>标题公式：</span>{item.title_formula}
                </div>
              )}
            </div>
          )}
          {(item.pain_points?.length ?? 0) > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>痛点：</div>
              <div>{item.pain_points!.map((p) => <Tag key={p} text={p} color="var(--warn)" />)}</div>
            </div>
          )}
          {(item.highlights?.length ?? 0) > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>爆点：</div>
              <div>{item.highlights!.map((h) => <Tag key={h} text={h} color="var(--ok)" />)}</div>
            </div>
          )}
          {(item.audience_tags?.length ?? 0) > 0 && (
            <div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>人群：</div>
              <div>{item.audience_tags!.map((t) => <Tag key={t} text={t} />)}</div>
            </div>
          )}
          {(item.risk_flags?.length ?? 0) > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 12, color: "var(--danger)", marginBottom: 4 }}>⚠️ 风险标记：</div>
              <div>{item.risk_flags!.map((f) => <Tag key={f} text={f} color="var(--danger)" />)}</div>
            </div>
          )}
          <div style={{ marginTop: 10, fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>
            <div
              style={{ maxHeight: 120, overflow: "hidden", maskImage: "linear-gradient(to bottom, black 60%, transparent)" }}
            >
              {item.body_text}
            </div>
          </div>
        </div>
      )}
      {!expanded && item.body_text && (
        <div
          style={{ fontSize: 13, color: "var(--muted)", cursor: "pointer", marginTop: 4 }}
          onClick={() => setExpanded(true)}
        >
          {item.body_text?.slice(0, 80)}... <span style={{ color: "var(--brand)" }}>展开</span>
        </div>
      )}
    </div>
  );
}

// ─── 主题知识库面板 ──────────────────────────────────────
function TopicPanel({ topic }: { topic: ExtendedInsightTopic }) {
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div>
          <strong style={{ fontSize: 15 }}>{topic.name}</strong>
          <span style={{ marginLeft: 8, fontSize: 12, color: "var(--muted)" }}>{topic.content_count ?? topic.item_count ?? 0} 条内容</span>
        </div>
        <div>{(topic.platform_focus ?? []).map((p) => <Tag key={p} text={p} color="var(--brand-2)" />)}</div>
      </div>
      {topic.description && <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8 }}>{topic.description}</div>}
      {(topic.audience_tags?.length ?? 0) > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: "var(--muted)" }}>目标人群</div>
          {topic.audience_tags!.map((t) => <Tag key={t} text={t} />)}
        </div>
      )}
      {(topic.common_pain_points?.length ?? 0) > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: "var(--muted)" }}>常见痛点</div>
          {topic.common_pain_points!.map((p: string) => <Tag key={p} text={p} color="var(--warn)" />)}
        </div>
      )}
      {(topic.common_structures?.length ?? 0) > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: "var(--muted)" }}>常见结构</div>
          {topic.common_structures!.map((s: string) => <Tag key={s} text={s} color="var(--brand)" />)}
        </div>
      )}
      {(topic.common_titles?.length ?? 0) > 0 && (
        <div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>高互动标题示例</div>
          {topic.common_titles!.slice(0, 3).map((t: string, i: number) => (
            <div key={i} style={{ fontSize: 13, padding: "4px 0", borderBottom: "1px solid var(--line)" }}>{t}</div>
          ))}
        </div>
      )}
      {topic.risk_notes && (
        <div style={{ marginTop: 8, background: "#fdeeee", borderRadius: 6, padding: "6px 10px", fontSize: 12, color: "var(--danger)" }}>
          ⚠️ {topic.risk_notes}
        </div>
      )}
    </div>
  );
}

// ─── 检索召回面板 ────────────────────────────────────────
function RetrievePanel({ topics }: { topics: InsightTopic[] }) {
  const [platform, setPlatform] = useState("xiaohongshu");
  const [topicName, setTopicName] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function handleRetrieve() {
    setLoading(true);
    try {
      const r = await retrieveInsightContext({ platform, topic_name: topicName || undefined, limit: 5 });
      setResult(r);
    } finally {
      setLoading(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    padding: "8px 10px",
    borderRadius: 8,
    border: "1px solid var(--line)",
    background: "var(--bg)",
    fontSize: 14,
    color: "var(--text)",
    width: "100%",
  };

  return (
    <div className="card" style={{ padding: "16px" }}>
      <h3 style={{ marginBottom: 12 }}>检索召回 · 给生成模块提供参考</h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 10, marginBottom: 12 }}>
        <select value={platform} onChange={(e) => setPlatform(e.target.value)} style={inputStyle}>
          {PLATFORMS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
        <select value={topicName} onChange={(e) => setTopicName(e.target.value)} style={inputStyle}>
          <option value="">全部主题</option>
          {topics.map((t) => <option key={t.id} value={t.name}>{t.name}</option>)}
        </select>
        <button className="btn" onClick={handleRetrieve} disabled={loading} style={{ whiteSpace: "nowrap" }}>
          {loading ? "检索中..." : "召回参考"}
        </button>
      </div>

      {result && (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ fontSize: 13, color: "var(--muted)" }}>
            共检索到 <strong>{result.reference_count}</strong> 条相关内容，以下为结构化参考特征：
          </div>

          {result.title_examples?.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>📌 高互动标题参考</div>
              {result.title_examples.map((t: string, i: number) => (
                <div key={i} style={{ fontSize: 13, padding: "4px 8px", borderLeft: "3px solid var(--brand)", marginBottom: 4, background: "var(--bg-2)", borderRadius: "0 6px 6px 0" }}>{t}</div>
              ))}
            </div>
          )}

          {result.structure_examples?.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>🏗️ 常见结构</div>
              <div>{result.structure_examples.map((s: string) => <Tag key={s} text={s} color="var(--brand)" />)}</div>
            </div>
          )}

          {result.hook_examples?.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>🎣 开头钩子类型</div>
              <div>{result.hook_examples.map((h: string) => <Tag key={h} text={h} color="var(--brand-2)" />)}</div>
            </div>
          )}

          {result.pain_point_examples?.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>💢 高频痛点</div>
              <div>{result.pain_point_examples.map((p: string) => <Tag key={p} text={p} color="var(--warn)" />)}</div>
            </div>
          )}

          <div style={{ background: "var(--bg-2)", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}>
            <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 4 }}>📊 风格分布</div>
            {result.style_summary}
          </div>

          <div style={{ background: "#fdeeee", borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "var(--danger)" }}>
            ⚠️ 风险提醒：{result.risk_reminder}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── 新建主题表单 ────────────────────────────────────────
function NewTopicForm({ onSuccess }: { onSuccess: () => void }) {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [risk, setRisk] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await createInsightTopic({ name: name.trim(), description: desc, risk_notes: risk || undefined });
      setName(""); setDesc(""); setRisk("");
      onSuccess();
    } finally {
      setSaving(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "8px 10px",
    borderRadius: 8,
    border: "1px solid var(--line)",
    background: "var(--bg)",
    fontSize: 14,
    color: "var(--text)",
  };

  return (
    <form onSubmit={submit} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 8, alignItems: "end" }}>
      <div>
        <label style={{ fontSize: 12, color: "var(--muted)", display: "block", marginBottom: 4 }}>主题名 *</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：征信查询多" style={inputStyle} />
      </div>
      <div>
        <label style={{ fontSize: 12, color: "var(--muted)", display: "block", marginBottom: 4 }}>描述</label>
        <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="简短说明" style={inputStyle} />
      </div>
      <div>
        <label style={{ fontSize: 12, color: "var(--muted)", display: "block", marginBottom: 4 }}>风险提醒</label>
        <input value={risk} onChange={(e) => setRisk(e.target.value)} placeholder="如：避免承诺下款率" style={inputStyle} />
      </div>
      <button type="submit" className="btn" disabled={saving}>{saving ? "..." : "新建"}</button>
    </form>
  );
}

// ─── 主页面 ──────────────────────────────────────────────
type Tab = "library" | "topics" | "retrieve" | "import";

export function InsightPage() {
  const [tab, setTab] = useState<Tab>("library");
  const [items, setItems] = useState<InsightItem[]>([]);
  const [topics, setTopics] = useState<ExtendedInsightTopic[]>([]);
  const [stats, setStats] = useState<InsightStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzingIds, setAnalyzingIds] = useState<Set<number>>(new Set());

  // 筛选
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterTopic, setFilterTopic] = useState<number | undefined>(undefined);
  const [filterHot, setFilterHot] = useState<boolean | undefined>(undefined);
  const [search, setSearch] = useState("");

  async function loadAll() {
    setLoading(true);
    try {
      const [its, tops, st] = await Promise.all([
        listInsightItems({
          platform: filterPlatform || undefined,
          topic_id: filterTopic,
          is_hot: filterHot,
          search: search || undefined,
        }),
        listInsightTopics(),
        getInsightStats(),
      ]);
      setItems(its);
      setTopics(tops);
      setStats(st);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, [filterPlatform, filterTopic, filterHot, search]);

  async function handleAnalyze(id: number) {
    setAnalyzingIds((s) => new Set(s).add(id));
    try {
      await analyzeInsightItem(id);
      await loadAll();
    } finally {
      setAnalyzingIds((s) => { const n = new Set(s); n.delete(id); return n; });
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("确定删除这条内容？")) return;
    await deleteInsightItem(id);
    await loadAll();
  }

  const selectStyle: React.CSSProperties = {
    padding: "7px 10px",
    borderRadius: 8,
    border: "1px solid var(--line)",
    background: "var(--bg)",
    fontSize: 13,
    color: "var(--text)",
  };

  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "8px 18px",
    borderRadius: 10,
    border: "none",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 14,
    background: tab === t ? "linear-gradient(90deg, #f8d8bf, #c0edf3)" : "transparent",
    color: "var(--text)",
  });

  return (
    <div className="page grid" style={{ gap: 18 }}>
      {/* 标题 + 统计概览 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ margin: 0 }}>爆款内容采集分析中心</h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            采集 → 清洗 → AI分析 → 主题聚类 → 检索召回 · 闭环内容洞察
          </p>
        </div>
        {stats && (
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {[
              { label: "内容总量", value: stats.total_items },
              { label: "爆款内容", value: stats.hot_items },
              { label: "AI已分析", value: stats.analyzed_items },
              { label: "主题数", value: stats.topic_count },
            ].map(({ label, value }) => (
              <div key={label} className="card" style={{ padding: "10px 16px", textAlign: "center", minWidth: 80 }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: "var(--brand)" }}>{value}</div>
                <div style={{ fontSize: 12, color: "var(--muted)" }}>{label}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 选项卡 */}
      <div style={{ display: "flex", gap: 6, borderBottom: "1px solid var(--line)", paddingBottom: 8 }}>
        <button style={tabStyle("library")} onClick={() => setTab("library")}>📚 内容库</button>
        <button style={tabStyle("topics")} onClick={() => setTab("topics")}>🏷️ 主题管理</button>
        <button style={tabStyle("retrieve")} onClick={() => setTab("retrieve")}>🔍 检索召回</button>
        <button style={tabStyle("import")} onClick={() => setTab("import")}>➕ 导入内容</button>
      </div>

      {/* 内容库 */}
      {tab === "library" && (
        <div style={{ display: "grid", gap: 14 }}>
          {/* 筛选栏 */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <select value={filterPlatform} onChange={(e) => setFilterPlatform(e.target.value)} style={selectStyle}>
              <option value="">全部平台</option>
              {PLATFORMS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
            <select
              value={filterTopic ?? ""}
              onChange={(e) => setFilterTopic(e.target.value ? parseInt(e.target.value) : undefined)}
              style={selectStyle}
            >
              <option value="">全部主题</option>
              {topics.map((t) => <option key={t.id} value={t.id}>{t.name}（{t.content_count ?? t.item_count ?? 0}）</option>)}
            </select>
            <select
              value={filterHot === undefined ? "" : String(filterHot)}
              onChange={(e) => setFilterHot(e.target.value === "" ? undefined : e.target.value === "true")}
              style={selectStyle}
            >
              <option value="">全部热度</option>
              <option value="true">仅爆款</option>
              <option value="false">普通内容</option>
            </select>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索标题/正文..."
              style={{ ...selectStyle, minWidth: 200 }}
            />
          </div>

          {loading ? (
            <div className="card" style={{ textAlign: "center", color: "var(--muted)" }}>加载中...</div>
          ) : items.length === 0 ? (
            <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: 30 }}>
              暂无内容，前往「导入内容」添加第一条
            </div>
          ) : (
            <div style={{ display: "grid", gap: 10 }}>
              {items.map((item) => (
                <div key={item.id} style={{ opacity: analyzingIds.has(item.id) ? 0.6 : 1 }}>
                  <ItemCard
                    item={item}
                    topics={topics}
                    onAnalyze={handleAnalyze}
                    onDelete={handleDelete}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 主题管理 */}
      {tab === "topics" && (
        <div style={{ display: "grid", gap: 14 }}>
          <div className="card" style={{ padding: "14px 16px" }}>
            <h3 style={{ marginBottom: 12 }}>新建主题</h3>
            <NewTopicForm onSuccess={loadAll} />
          </div>
          {topics.length === 0 ? (
            <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: 20 }}>
              暂无主题，先新建一个主题再导入内容
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {topics.map((t) => <TopicPanel key={t.id} topic={t} />)}
            </div>
          )}
        </div>
      )}

      {/* 检索召回 */}
      {tab === "retrieve" && <RetrievePanel topics={topics} />}

      {/* 导入内容 */}
      {tab === "import" && (
        <div className="card" style={{ padding: "16px 20px" }}>
          <h3 style={{ marginBottom: 12 }}>手动导入内容</h3>
          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 16 }}>
            将参考内容粘贴入库，系统自动计算互动分、热度分层；保存后可点击「AI分析」进行深度拆解。
          </p>
          <ImportForm topics={topics} onSuccess={loadAll} />
        </div>
      )}
    </div>
  );
}
