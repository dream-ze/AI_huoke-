import { FormEvent, useEffect, useState } from "react";
import { analyzeCollect, getCollectDetail, listCollect, rewriteCollect, submitManualToInbox } from "../../lib/api";
import { CollectDetail, CollectItem } from "../../types";
import { copyToClipboard } from "../../utils/clipboard";

const DRAFT_KEY = "zhk_material_editor_draft";
const CONTENT_LIMITS: Record<string, number> = {
  xiaohongshu: 1000,
  douyin: 800,
  zhihu: 5000,
  xianyu: 2000,
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
    suggestions?: string[];
  };
};

type RewriteResult = {
  rewritten: string;
  llm_output?: string;
  tags?: {
    topic_tag?: string;
    intent_tag?: string;
    crowd_tag?: string;
    risk_tag?: string;
    heat_score?: number;
    reason?: string;
  } | null;
  copies: RewriteCopy[];
  selected_variant?: string | null;
  compliance?: {
    corrected?: boolean;
    is_compliant?: boolean;
    risk_level?: string;
    risk_score?: number;
  } | null;
};

export function MaterialsPage() {
  const [items, setItems] = useState<CollectItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState<CollectDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"content" | "knowledge" | "raw" | "generation">("content");
  const [actionMessage, setActionMessage] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [rewritePlatform, setRewritePlatform] = useState<"xiaohongshu" | "douyin" | "zhihu">("xiaohongshu");
  const [rewrittenText, setRewrittenText] = useState("");
  const [rewriteResult, setRewriteResult] = useState<RewriteResult | null>(null);
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
    setRewriteResult(null);
    try {
      const data = await getCollectDetail(id);
      setDetail(data);
      setActiveTab("content");
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
      setActionMessage("知识文档已重建");
      setActiveTab("knowledge");
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
      setRewriteResult({
        rewritten: data?.rewritten || "",
        llm_output: data?.llm_output || "",
        tags: data?.tags || null,
        copies: data?.copies || [],
        selected_variant: data?.selected_variant || null,
        compliance: data?.compliance || null,
      });
      setActionMessage("改写完成");
      setActiveTab("generation");
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
          setMessage("已进入素材中心，并放入待审核队列");
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
              <th>状态</th>
              <th>热度/线索</th>
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
                <td>{item.status} / {item.risk_status}</td>
                <td>{item.hot_level} / {item.lead_level}</td>
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
              标题：{detail.title} | 平台：{detail.platform} | 作者：{detail.author_name || "-"} | 状态：{detail.status}
            </div>
            <div className="muted">
              质量 {detail.quality_score} / 相关 {detail.relevance_score} / 线索 {detail.lead_score} | 热度 {detail.hot_level} | 线索等级 {detail.lead_level}
            </div>
            <div className="muted">
              来源：{detail.source_channel} | 风险：{detail.risk_status} | 过滤原因：{detail.filter_reason || "-"}
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className="secondary" type="button" onClick={handleAnalyze} disabled={analyzing}>
                {analyzing ? "重建中..." : "重建知识"}
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
              <button className={activeTab === "content" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("content")}>素材正文</button>
              <button className={activeTab === "knowledge" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("knowledge")}>知识文档</button>
              <button className={activeTab === "raw" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("raw")}>原始载荷</button>
              <button className={activeTab === "generation" ? "primary" : "ghost"} type="button" onClick={() => setActiveTab("generation")}>改写记录</button>
            </div>

            {activeTab === "content" && (
              <div className="grid" style={{ gap: 8 }}>
                <div className="muted">链接：{detail.source_url || "-"}</div>
                <div className="muted">关键词：{detail.keyword || "-"}</div>
                <div className="muted">发布时间：{detail.publish_time ? new Date(detail.publish_time).toLocaleString() : "-"}</div>
                <textarea readOnly value={detail.content_text || ""} placeholder="无正文内容" />
                {detail.review_note && <div className="muted">审核备注：{detail.review_note}</div>}
                {detail.remark && <div className="muted">补充备注：{detail.remark}</div>}
              </div>
            )}

            {activeTab === "knowledge" && (
              <div className="grid" style={{ gap: 8 }}>
                {detail.knowledge && (
                  <div className="card" style={{ padding: 10 }}>
                    <div className="muted">主知识文档</div>
                    <div>账号类型：{detail.knowledge.account_type || "-"}</div>
                    <div>目标人群：{detail.knowledge.target_audience || "-"}</div>
                    <div>内容类型：{detail.knowledge.content_type || "-"}</div>
                    <div>主题：{detail.knowledge.topic || "-"}</div>
                    <div>摘要：{detail.knowledge.summary || "-"}</div>
                  </div>
                )}
                {(detail.knowledge_documents || []).length ? detail.knowledge_documents.map((document) => (
                  <div key={document.document_id} className="card" style={{ padding: 10 }}>
                    <div className="muted">文档 #{document.document_id}</div>
                    <div>主题：{document.topic || "-"}</div>
                    <div>账号类型：{document.account_type} | 目标人群：{document.target_audience}</div>
                    <div>摘要：{document.summary || "-"}</div>
                    <textarea readOnly value={(document.chunks || []).join("\n\n") || document.content_text || ""} placeholder="无知识切片" />
                  </div>
                )) : <div className="muted">暂无知识文档，请先执行“重建知识”</div>}
              </div>
            )}

            {activeTab === "raw" && (
              <div className="grid" style={{ gap: 8 }}>
                <div className="muted">source_id：{detail.source_id || "-"}</div>
                <div className="muted">cover_url：{detail.cover_url || "-"}</div>
                <textarea readOnly value={JSON.stringify(detail.raw_data || {}, null, 2)} placeholder="无原始字段" />
              </div>
            )}

            {activeTab === "generation" && (
              <div className="grid" style={{ gap: 8 }}>
                {rewriteResult?.tags && (
                  <div className="card" style={{ padding: 10 }}>
                    <div className="muted" style={{ marginBottom: 6 }}>本次标签识别</div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", fontSize: 13 }}>
                      <span>topic: {rewriteResult.tags.topic_tag || "-"}</span>
                      <span>intent: {rewriteResult.tags.intent_tag || "-"}</span>
                      <span>crowd: {rewriteResult.tags.crowd_tag || "-"}</span>
                      <span>risk: {rewriteResult.tags.risk_tag || "-"}</span>
                      <span>heat: {rewriteResult.tags.heat_score ?? "-"}</span>
                    </div>
                    {rewriteResult.tags.reason && <div className="muted" style={{ marginTop: 6 }}>{rewriteResult.tags.reason}</div>}
                  </div>
                )}

                {(rewriteResult?.copies || []).length > 0 && (
                  <div className="grid" style={{ gap: 10 }}>
                    <h4 style={{ margin: 0 }}>本次三版文案（已做合规复检）</h4>
                    {rewriteResult?.copies.map((copy, index) => {
                      const compliant = copy.compliance?.is_compliant;
                      const riskLevel = copy.compliance?.risk_level || "low";
                      const riskColor =
                        riskLevel === "high" ? "#b00020" : riskLevel === "medium" ? "#b26a00" : "#1b5e20";
                      const riskBg =
                        riskLevel === "high" ? "#ffebee" : riskLevel === "medium" ? "#fff8e1" : "#e8f5e9";
                      return (
                        <div key={`${copy.variant_name}-${index}`} className="card" style={{ padding: 10 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                            <div style={{ fontWeight: 700 }}>{copy.variant_name} · {copy.title}</div>
                            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                              <span style={{ background: riskBg, color: riskColor, borderRadius: 8, padding: "2px 8px", fontSize: 12 }}>
                                {compliant ? "合规" : "需复核"} · {riskLevel}
                              </span>
                              {copy.compliance?.corrected && (
                                <span style={{ background: "#e3f2fd", color: "#1565c0", borderRadius: 8, padding: "2px 8px", fontSize: 12 }}>
                                  已自动降风险
                                </span>
                              )}
                              <button
                                className="ghost"
                                type="button"
                                onClick={() => copyToClipboard(`${copy.title}\n\n${copy.content}`)}
                                style={{ fontSize: 12, padding: "4px 8px" }}
                              >
                                复制
                              </button>
                            </div>
                          </div>
                          {!!copy.hashtags?.length && (
                            <div className="muted" style={{ marginTop: 6 }}>
                              {copy.hashtags.join(" ")}
                            </div>
                          )}
                          <textarea readOnly value={copy.content || ""} style={{ marginTop: 8 }} />
                          {!!copy.compliance?.suggestions?.length && (
                            <div className="muted" style={{ marginTop: 6 }}>
                              合规建议：{copy.compliance?.suggestions?.join("；")}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {rewrittenText && (
                  <div className="grid" style={{ gap: 8 }}>
                    <h4 style={{ margin: 0 }}>推荐发布版</h4>
                    <textarea readOnly value={rewrittenText} />
                  </div>
                )}
                {(detail.generation_tasks || []).length ? detail.generation_tasks.map((task) => (
                  <div key={task.generation_task_id} className="card" style={{ padding: 10 }}>
                    <div className="muted">
                      #{task.generation_task_id} · {task.platform} · {task.account_type} · {task.target_audience} · {task.created_at ? new Date(task.created_at).toLocaleString() : "-"}
                    </div>
                    <textarea readOnly value={task.output_text || ""} />
                  </div>
                )) : <div className="muted">暂无改写记录</div>}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
