import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { assignLeadOwner, convertLeadToCustomer, getLeadAttribution, listLeads, updateLeadStatus } from "../../lib/api";
import { leadApi } from "../../api/leadApi";
import { LeadAttribution, LeadItem, LeadAttributionChainResponse, BatchImportLeadItem, BatchImportLeadsResponse } from "../../types";

const statusOptions = ["new", "contacted", "qualified", "converted", "lost"];
const gradeOptions = ["A", "B", "C", "D"];

const platformLabels: Record<string, string> = {
  xiaohongshu: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
  xianyu: "闲鱼",
  wechat: "微信",
  other: "其他",
};

const platformIcons: Record<string, string> = {
  xiaohongshu: "📕",
  douyin: "🎵",
  zhihu: "📘",
  xianyu: "🐟",
  wechat: "💬",
  other: "📄",
};

// ABCD 分级配置
const gradeConfig: Record<string, { label: string; color: string; bgColor: string; description: string }> = {
  A: { label: "A-高意向", color: "#059669", bgColor: "#d1fae5", description: "高意向客户，优先跟进" },
  B: { label: "B-有需求", color: "#2563eb", bgColor: "#dbeafe", description: "有明确需求，需要培育" },
  C: { label: "C-待培育", color: "#ca8a04", bgColor: "#fef9c3", description: "有潜在需求，持续跟进" },
  D: { label: "D-高风险", color: "#dc2626", bgColor: "#fee2e2", description: "风险较高，谨慎处理" },
};

export function LeadsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<LeadItem[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [gradeFilter, setGradeFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [attribution, setAttribution] = useState<LeadAttribution | null>(null);
  const [attributionDays, setAttributionDays] = useState(30);
  const focusLeadId = Number(searchParams.get("focusLeadId") || 0);
  const focusCustomerId = Number(searchParams.get("customerId") || 0);
  const sourceTaskId = Number(searchParams.get("taskId") || 0);

  // 归因链详情弹窗状态
  const [showAttributionModal, setShowAttributionModal] = useState(false);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [attributionChain, setAttributionChain] = useState<LeadAttributionChainResponse | null>(null);
  const [loadingChain, setLoadingChain] = useState(false);

  // 批量导入弹窗状态
  const [showImportModal, setShowImportModal] = useState(false);
  const [importItems, setImportItems] = useState<BatchImportLeadItem[]>([
    { platform: "xiaohongshu", title: "", note: "" }
  ]);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<BatchImportLeadsResponse | null>(null);

  async function refreshData() {
    let data: LeadItem[] = [];
    if (gradeFilter && gradeFilter !== "all") {
      // 按分级查询
      data = await leadApi.getLeadsByGrade(gradeFilter as 'A' | 'B' | 'C' | 'D', 0, 100);
    } else {
      data = await listLeads({ status: statusFilter === "all" ? undefined : statusFilter, limit: 100 });
    }
    setItems(data || []);
  }

  async function refreshAttribution() {
    try {
      const data = await getLeadAttribution(attributionDays);
      setAttribution(data);
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    async function run() {
      try {
        await Promise.all([refreshData(), refreshAttribution()]);
      } finally {
        setLoading(false);
      }
    }
    run();
  }, [statusFilter, attributionDays, gradeFilter]);

  async function handleStatus(leadId: number, status: string) {
    setBusyId(leadId);
    setMessage("");
    try {
      await updateLeadStatus(leadId, status);
      setMessage(`线索 #${leadId} 已更新为 ${status}`);
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "状态更新失败");
    } finally {
      setBusyId(null);
    }
  }

  async function handleAssignToMe(leadId: number) {
    setBusyId(leadId);
    setMessage("");
    try {
      await assignLeadOwner(leadId);
      setMessage(`线索 #${leadId} 已归属到我`);
      await refreshData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "归属更新失败");
    } finally {
      setBusyId(null);
    }
  }

  async function handleConvertToCustomer(leadId: number) {
    const nickname = window.prompt("可选：输入客户昵称（留空使用默认）", "");
    setBusyId(leadId);
    setMessage("");
    try {
      const customer = await convertLeadToCustomer(leadId, {
        nickname: nickname?.trim() || undefined,
      });
      setMessage(`线索 #${leadId} 已转客户 #${customer.id}`);
      await refreshData();
      navigate(`/customers?focusCustomerId=${customer.id}&fromLeadId=${leadId}`);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "转客户失败");
    } finally {
      setBusyId(null);
    }
  }

  // 查看归因链
  async function handleViewAttributionChain(leadId: number) {
    setSelectedLeadId(leadId);
    setShowAttributionModal(true);
    setLoadingChain(true);
    setAttributionChain(null);
    try {
      const data = await leadApi.getLeadAttribution(leadId);
      setAttributionChain(data);
    } catch (err: any) {
      console.error("获取归因链失败:", err);
      setMessage(err?.response?.data?.detail || "获取归因链失败");
    } finally {
      setLoadingChain(false);
    }
  }

  // 批量导入相关
  function addImportRow() {
    setImportItems([...importItems, { platform: "xiaohongshu", title: "", note: "" }]);
  }

  function removeImportRow(index: number) {
    setImportItems(importItems.filter((_, i) => i !== index));
  }

  function updateImportItem(index: number, field: keyof BatchImportLeadItem, value: string | number) {
    const updated = [...importItems];
    (updated[index] as any)[field] = value;
    setImportItems(updated);
  }

  async function handleBatchImport() {
    // 过滤掉空行
    const validItems = importItems.filter(item => item.title.trim() && item.platform);
    if (validItems.length === 0) {
      setMessage("请填写至少一条有效的线索数据");
      return;
    }

    setImporting(true);
    setImportResult(null);
    try {
      const result = await leadApi.batchImportLeads(validItems);
      setImportResult(result);
      if (result.success > 0) {
        await refreshData();
      }
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "批量导入失败");
    } finally {
      setImporting(false);
    }
  }

  function closeImportModal() {
    setShowImportModal(false);
    setImportItems([{ platform: "xiaohongshu", title: "", note: "" }]);
    setImportResult(null);
  }

  // 渲染分级标签
  function renderGradeTag(grade?: string) {
    if (!grade) return <span style={{ color: "#999" }}>-</span>;
    const config = gradeConfig[grade];
    if (!config) return <span>{grade}</span>;
    return (
      <span
        style={{
          display: "inline-block",
          padding: "2px 8px",
          borderRadius: 4,
          fontSize: 12,
          fontWeight: 500,
          color: config.color,
          backgroundColor: config.bgColor,
        }}
        title={config.description}
      >
        {config.label}
      </span>
    );
  }

  // 渲染归因来源
  function renderAttributionSource(item: LeadItem) {
    const chain = item.attribution_chain;
    if (!chain) {
      return <span style={{ color: "#999" }}>-</span>;
    }

    const platformLabel = platformLabels[chain.platform || item.platform] || item.platform;
    const platformIcon = platformIcons[chain.platform || item.platform] || "📄";

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span>{platformIcon}</span>
          <span style={{ fontSize: 12 }}>{platformLabel}</span>
        </div>
        {chain.channel && (
          <span style={{ fontSize: 11, color: "#666" }}>渠道: {chain.channel}</span>
        )}
        {chain.audience_tags && chain.audience_tags.length > 0 && (
          <span style={{ fontSize: 11, color: "#888" }}>
            标签: {chain.audience_tags.slice(0, 2).join(", ")}{chain.audience_tags.length > 2 ? "..." : ""}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="page grid">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>线索池</h2>
        <button
          type="button"
          onClick={() => setShowImportModal(true)}
          style={{
            padding: "8px 16px",
            background: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          📥 批量导入
        </button>
      </div>

      {/* 归因分析区域 */}
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>线索来源归因分析</h3>
          <select
            value={attributionDays}
            onChange={(e) => setAttributionDays(Number(e.target.value))}
            style={{ padding: "4px 8px" }}
          >
            <option value={7}>近7天</option>
            <option value={30}>近30天</option>
            <option value={90}>近90天</option>
          </select>
        </div>

        {attribution && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* 平台来源分布 */}
            <div>
              <h4 style={{ margin: "0 0 8px 0", color: "#666" }}>平台来源分布</h4>
              <table className="table" style={{ fontSize: 13 }}>
                <thead>
                  <tr>
                    <th>平台</th>
                    <th>线索数</th>
                    <th>有效线索</th>
                    <th>转化数</th>
                    <th>转化率</th>
                  </tr>
                </thead>
                <tbody>
                  {attribution.by_platform.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: "center", color: "#999" }}>暂无数据</td>
                    </tr>
                  ) : (
                    attribution.by_platform.map((item) => (
                      <tr key={item.platform}>
                        <td>
                          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            {platformIcons[item.platform] || "📄"}
                            {platformLabels[item.platform] || item.platform}
                          </span>
                        </td>
                        <td>{item.lead_count}</td>
                        <td>{item.valid_count}</td>
                        <td>{item.conversion_count}</td>
                        <td>{(item.conversion_rate * 100).toFixed(1)}%</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* 最佳引流内容 */}
            <div>
              <h4 style={{ margin: "0 0 8px 0", color: "#666" }}>最佳引流内容 TOP 10</h4>
              <table className="table" style={{ fontSize: 13 }}>
                <thead>
                  <tr>
                    <th>标题</th>
                    <th>平台</th>
                    <th>带来线索</th>
                  </tr>
                </thead>
                <tbody>
                  {attribution.top_content.length === 0 ? (
                    <tr>
                      <td colSpan={3} style={{ textAlign: "center", color: "#999" }}>暂无数据</td>
                    </tr>
                  ) : (
                    attribution.top_content.map((item, idx) => (
                      <tr key={idx}>
                        <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={item.title}>
                          {item.title}
                        </td>
                        <td>{platformLabels[item.platform] || item.platform}</td>
                        <td>{item.lead_count}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <section className="card">
        {focusLeadId > 0 && (
          <div className="muted" style={{ marginBottom: 10, display: "flex", gap: 10, alignItems: "center" }}>
            <span>
              已从任务 #{sourceTaskId || "-"} 跳转定位线索 #{focusLeadId}
              {focusCustomerId > 0 ? `，关联客户 #${focusCustomerId}` : ""}
            </span>
            {focusCustomerId > 0 && (
              <button
                className="ghost"
                type="button"
                onClick={() => navigate(`/customers?focusCustomerId=${focusCustomerId}&fromLeadId=${focusLeadId}`)}
              >
                打开客户
              </button>
            )}
          </div>
        )}
        <div className="form-row" style={{ alignItems: "end", gap: 16 }}>
          <div>
            <label>状态筛选</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">全部</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>分级筛选</label>
            <select value={gradeFilter} onChange={(e) => setGradeFilter(e.target.value)}>
              <option value="all">全部分级</option>
              {gradeOptions.map((grade) => (
                <option key={grade} value={grade}>
                  {gradeConfig[grade]?.label || grade}
                </option>
              ))}
            </select>
          </div>
        </div>
        {message && <div className="muted" style={{ marginTop: 10 }}>{message}</div>}
      </section>

      <section className="card">
        <h3>线索列表</h3>
        <div style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>分级</th>
                <th>归因来源</th>
                <th>来源任务</th>
                <th>标题</th>
                <th>归属人</th>
                <th>关联客户</th>
                <th>加微</th>
                <th>线索</th>
                <th>有效</th>
                <th>转化</th>
                <th>状态流转</th>
                <th>归属操作</th>
                <th>客户流转</th>
                <th>归因链</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={15}>加载中...</td>
                </tr>
              ) : (
                items.map((item) => {
                  const busy = busyId === item.id;
                  return (
                    <tr key={item.id} style={item.id === focusLeadId ? { background: "#fff8e8" } : undefined}>
                      <td>{item.id}</td>
                      <td>{renderGradeTag(item.grade)}</td>
                      <td>{renderAttributionSource(item)}</td>
                      <td>{item.publish_task_id || "-"}</td>
                      <td style={{ maxWidth: 150, overflow: "hidden", textOverflow: "ellipsis" }} title={item.title || ""}>
                        {item.title || "-"}
                      </td>
                      <td>{item.owner_id}</td>
                      <td>{item.customer_id ? `#${item.customer_id}` : "-"}</td>
                      <td>{item.wechat_adds}</td>
                      <td>{item.leads}</td>
                      <td>{item.valid_leads}</td>
                      <td>{item.conversions}</td>
                      <td>
                        <select
                          value={item.status}
                          disabled={busy}
                          onChange={(e) => handleStatus(item.id, e.target.value)}
                        >
                          {statusOptions.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <button className="ghost" type="button" disabled={busy} onClick={() => handleAssignToMe(item.id)}>
                          归我
                        </button>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <button
                            className="secondary"
                            type="button"
                            disabled={busy || Boolean(item.customer_id)}
                            onClick={() => handleConvertToCustomer(item.id)}
                          >
                            {item.customer_id ? "已转客户" : "转客户"}
                          </button>
                          {item.customer_id && (
                            <button
                              className="ghost"
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                navigate(`/customers?focusCustomerId=${item.customer_id}&fromLeadId=${item.id}`)
                              }
                            >
                              查看客户
                            </button>
                          )}
                        </div>
                      </td>
                      <td>
                        <button
                          className="ghost"
                          type="button"
                          disabled={busy}
                          onClick={() => handleViewAttributionChain(item.id)}
                          title="查看归因链"
                        >
                          🔗 链路
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* 归因链详情弹窗 */}
      {showAttributionModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowAttributionModal(false)}
        >
          <div
            style={{
              background: "white",
              borderRadius: 8,
              padding: 24,
              maxWidth: 600,
              width: "90%",
              maxHeight: "80vh",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>线索 #{selectedLeadId} 归因链</h3>
              <button
                type="button"
                onClick={() => setShowAttributionModal(false)}
                style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer" }}
              >
                ×
              </button>
            </div>

            {loadingChain ? (
              <div style={{ textAlign: "center", padding: 20 }}>加载中...</div>
            ) : attributionChain ? (
              <div>
                {/* 归因链步骤条 */}
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {/* 平台 */}
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: "#dbeafe",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 16,
                      }}
                    >
                      {platformIcons[attributionChain.platform || ""] || "📄"}
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "#666" }}>平台</div>
                      <div style={{ fontWeight: 500 }}>
                        {platformLabels[attributionChain.platform || ""] || attributionChain.platform || "-"}
                      </div>
                    </div>
                  </div>

                  <div style={{ width: 2, height: 16, background: "#e5e7eb", marginLeft: 15 }} />

                  {/* 账号 */}
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: "#fef3c7",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 16,
                      }}
                    >
                      👤
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "#666" }}>发布账号</div>
                      <div style={{ fontWeight: 500 }}>{attributionChain.account_name || "-"}</div>
                    </div>
                  </div>

                  <div style={{ width: 2, height: 16, background: "#e5e7eb", marginLeft: 15 }} />

                  {/* 内容 */}
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: "#d1fae5",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 16,
                      }}
                    >
                      📝
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "#666" }}>关联内容</div>
                      <div style={{ fontWeight: 500, maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis" }}>
                        {attributionChain.content_title || "-"}
                      </div>
                    </div>
                  </div>

                  <div style={{ width: 2, height: 16, background: "#e5e7eb", marginLeft: 15 }} />

                  {/* 活动 */}
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: "#fce7f3",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 16,
                      }}
                    >
                      📢
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "#666" }}>活动</div>
                      <div style={{ fontWeight: 500 }}>{attributionChain.campaign_name || "-"}</div>
                    </div>
                  </div>

                  <div style={{ width: 2, height: 16, background: "#e5e7eb", marginLeft: 15 }} />

                  {/* 人群标签 */}
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: "#e0e7ff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 16,
                      }}
                    >
                      🏷️
                    </div>
                    <div>
                      <div style={{ fontSize: 12, color: "#666" }}>人群标签</div>
                      <div style={{ fontWeight: 500 }}>
                        {attributionChain.audience_tags.length > 0
                          ? attributionChain.audience_tags.join(", ")
                          : "-"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* 其他信息 */}
                <div style={{ marginTop: 20, padding: 12, background: "#f9fafb", borderRadius: 6 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
                    <div>
                      <span style={{ color: "#666" }}>渠道：</span>
                      <span>{attributionChain.channel || "-"}</span>
                    </div>
                    <div>
                      <span style={{ color: "#666" }}>当前阶段：</span>
                      <span>{attributionChain.current_stage}</span>
                    </div>
                    <div>
                      <span style={{ color: "#666" }}>首次接触：</span>
                      <span>{attributionChain.first_contact_time || "-"}</span>
                    </div>
                    <div>
                      <span style={{ color: "#666" }}>转化结果：</span>
                      <span>{attributionChain.conversion_result || "-"}</span>
                    </div>
                  </div>
                  {attributionChain.touchpoint_url && (
                    <div style={{ marginTop: 8, fontSize: 13 }}>
                      <span style={{ color: "#666" }}>触点链接：</span>
                      <a
                        href={attributionChain.touchpoint_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "#3b82f6" }}
                      >
                        {attributionChain.touchpoint_url}
                      </a>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: 20, color: "#999" }}>
                暂无归因链数据
              </div>
            )}
          </div>
        </div>
      )}

      {/* 批量导入弹窗 */}
      {showImportModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={closeImportModal}
        >
          <div
            style={{
              background: "white",
              borderRadius: 8,
              padding: 24,
              maxWidth: 800,
              width: "90%",
              maxHeight: "80vh",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>📥 批量导入线索</h3>
              <button
                type="button"
                onClick={closeImportModal}
                style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer" }}
              >
                ×
              </button>
            </div>

            <div style={{ marginBottom: 12, color: "#666", fontSize: 13 }}>
              填写线索信息，每行一条。标题为必填项。
            </div>

            {/* 导入结果 */}
            {importResult && (
              <div
                style={{
                  marginBottom: 16,
                  padding: 12,
                  background: importResult.success > 0 ? "#d1fae5" : "#fee2e2",
                  borderRadius: 6,
                }}
              >
                <div style={{ fontWeight: 500, marginBottom: 8 }}>
                  导入完成：成功 {importResult.success} 条，失败 {importResult.failed} 条，重复 {importResult.duplicates} 条
                </div>
                {importResult.failed_details.length > 0 && (
                  <div style={{ fontSize: 12, color: "#666" }}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>失败详情：</div>
                    {importResult.failed_details.map((detail, idx) => (
                      <div key={idx}>
                        第 {detail.index + 1} 行: {detail.error}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 输入表格 */}
            <div style={{ maxHeight: 300, overflow: "auto" }}>
              <table className="table" style={{ fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ width: 40 }}>#</th>
                    <th style={{ width: 120 }}>平台 *</th>
                    <th>标题 *</th>
                    <th style={{ width: 100 }}>来源</th>
                    <th style={{ width: 200 }}>备注</th>
                    <th style={{ width: 40 }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {importItems.map((item, index) => (
                    <tr key={index}>
                      <td>{index + 1}</td>
                      <td>
                        <select
                          value={item.platform}
                          onChange={(e) => updateImportItem(index, "platform", e.target.value)}
                          style={{ width: "100%", padding: "4px" }}
                        >
                          {Object.entries(platformLabels).map(([key, label]) => (
                            <option key={key} value={key}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          type="text"
                          value={item.title}
                          onChange={(e) => updateImportItem(index, "title", e.target.value)}
                          placeholder="线索标题"
                          style={{ width: "100%", padding: "4px" }}
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          value={item.source || ""}
                          onChange={(e) => updateImportItem(index, "source", e.target.value)}
                          placeholder="来源"
                          style={{ width: "100%", padding: "4px" }}
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          value={item.note || ""}
                          onChange={(e) => updateImportItem(index, "note", e.target.value)}
                          placeholder="备注"
                          style={{ width: "100%", padding: "4px" }}
                        />
                      </td>
                      <td>
                        {importItems.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeImportRow(index)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "#ef4444",
                              cursor: "pointer",
                            }}
                          >
                            ✕
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button
                type="button"
                onClick={addImportRow}
                style={{
                  padding: "6px 12px",
                  background: "#f3f4f6",
                  border: "1px solid #d1d5db",
                  borderRadius: 4,
                  cursor: "pointer",
                }}
              >
                + 添加行
              </button>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 20 }}>
              <button
                type="button"
                onClick={closeImportModal}
                style={{
                  padding: "8px 16px",
                  background: "#f3f4f6",
                  border: "1px solid #d1d5db",
                  borderRadius: 6,
                  cursor: "pointer",
                }}
              >
                取消
              </button>
              <button
                type="button"
                onClick={handleBatchImport}
                disabled={importing}
                style={{
                  padding: "8px 16px",
                  background: "#3b82f6",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  opacity: importing ? 0.6 : 1,
                }}
              >
                {importing ? "导入中..." : "开始导入"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
