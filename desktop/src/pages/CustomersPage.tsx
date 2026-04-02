import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { customerApi, Customer, AddFollowRecordRequest } from "../api/customerApi";

// 意向等级配置
const intentionLevelConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  high: { label: "A", color: "#fff", bgColor: "#22c55e" },
  medium: { label: "B", color: "#fff", bgColor: "#3b82f6" },
  low: { label: "C", color: "#fff", bgColor: "#f59e0b" },
};

// 客户状态配置
const customerStatusConfig: Record<string, { label: string; color: string }> = {
  new: { label: "新客户", color: "#3b82f6" },
  following: { label: "跟进中", color: "#f59e0b" },
  negotiating: { label: "洽谈中", color: "#8b5cf6" },
  converted: { label: "已成交", color: "#22c55e" },
  lost: { label: "已流失", color: "#6b7280" },
};

// 来源平台标签
const platformLabels: Record<string, string> = {
  xiaohongshu: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
  xianyu: "闲鱼",
  wechat: "微信",
  other: "其他",
};

export function CustomersPage() {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  
  // 筛选和搜索状态
  const [statusFilter, setStatusFilter] = useState("all");
  const [intentionFilter, setIntentionFilter] = useState("all");
  const [searchText, setSearchText] = useState("");
  
  // 选中的客户（用于展示详情面板）
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [showDetailPanel, setShowDetailPanel] = useState(false);
  
  // 新增跟进记录状态
  const [followContent, setFollowContent] = useState("");
  const [followMethod, setFollowMethod] = useState("phone");
  const [nextFollowDate, setNextFollowDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  
  // 新增客户表单状态
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [nickname, setNickname] = useState("");
  const [wechatId, setWechatId] = useState("");
  const [phone, setPhone] = useState("");
  const [sourcePlatform, setSourcePlatform] = useState("xiaohongshu");
  const [tags, setTags] = useState("");
  const [intention, setIntention] = useState("medium");
  const [company, setCompany] = useState("");
  const [position, setPosition] = useState("");
  const [industry, setIndustry] = useState("");
  const [email, setEmail] = useState("");

  const focusCustomerId = Number(searchParams.get("focusCustomerId") || 0);
  const fromLeadId = Number(searchParams.get("fromLeadId") || 0);

  async function fetchData() {
    setLoading(true);
    try {
      const data = await customerApi.list({
        status: statusFilter !== "all" ? statusFilter : undefined,
        intention_level: intentionFilter !== "all" ? intentionFilter : undefined,
        search: searchText || undefined,
        limit: 200,
      });
      setItems(data || []);
    } catch (err: any) {
      setMessage(err?.message || "获取客户列表失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, [statusFilter, intentionFilter]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchText !== undefined) fetchData();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchText]);

  async function onCreateCustomer(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    try {
      await customerApi.create({
        nickname,
        wechat_id: wechatId || undefined,
        phone: phone || undefined,
        source_platform: sourcePlatform,
        intention_level: intention,
        tags: tags.split(",").map((s) => s.trim()).filter(Boolean),
        company: company || undefined,
        position: position || undefined,
        industry: industry || undefined,
        email: email || undefined,
      });
      // 重置表单
      setNickname("");
      setWechatId("");
      setPhone("");
      setCompany("");
      setPosition("");
      setIndustry("");
      setEmail("");
      setTags("");
      setShowCreateForm(false);
      setMessage("客户已录入");
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "录入失败");
    }
  }

  async function handleExportCustomers() {
    try {
      const blob = await customerApi.exportCsv(statusFilter !== "all" ? statusFilter : undefined);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "customers_export.csv";
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("客户导出已开始");
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "客户导出失败");
    }
  }

  async function handleUpdateIntentionLevel(customerId: number, newLevel: string) {
    try {
      await customerApi.update(customerId, { intention_level: newLevel });
      setMessage("意向等级已更新");
      await fetchData();
      // 更新详情面板中的数据
      if (selectedCustomer?.id === customerId) {
        setSelectedCustomer(await customerApi.getDetail(customerId));
      }
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "更新失败");
    }
  }

  async function handleUpdateStatus(customerId: number, newStatus: string) {
    try {
      await customerApi.update(customerId, { customer_status: newStatus });
      setMessage("客户状态已更新");
      await fetchData();
      if (selectedCustomer?.id === customerId) {
        setSelectedCustomer(await customerApi.getDetail(customerId));
      }
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "更新失败");
    }
  }

  async function handleAddFollowRecord(e: FormEvent) {
    e.preventDefault();
    if (!selectedCustomer || !followContent.trim()) return;
    
    setSubmitting(true);
    try {
      const request: AddFollowRecordRequest = {
        content: followContent,
        follow_method: followMethod,
        next_follow_date: nextFollowDate || undefined,
      };
      const updated = await customerApi.addFollowRecord(selectedCustomer.id, request);
      setSelectedCustomer(updated);
      setFollowContent("");
      setNextFollowDate("");
      setMessage("跟进记录已添加");
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "添加跟进记录失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function openCustomerDetail(customer: Customer) {
    try {
      const detail = await customerApi.getDetail(customer.id);
      setSelectedCustomer(detail);
      setShowDetailPanel(true);
    } catch (err: any) {
      setMessage(err?.message || "获取客户详情失败");
    }
  }

  function closeDetailPanel() {
    setShowDetailPanel(false);
    setSelectedCustomer(null);
  }

  function renderIntentionBadge(level: string) {
    const config = intentionLevelConfig[level] || intentionLevelConfig.medium;
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 24,
          height: 24,
          borderRadius: "50%",
          backgroundColor: config.bgColor,
          color: config.color,
          fontSize: 12,
          fontWeight: "bold",
        }}
        title={`意向等级: ${level}`}
      >
        {config.label}
      </span>
    );
  }

  function renderStatusBadge(status: string) {
    const config = customerStatusConfig[status] || customerStatusConfig.new;
    return (
      <span
        style={{
          display: "inline-block",
          padding: "2px 8px",
          borderRadius: 4,
          backgroundColor: `${config.color}20`,
          color: config.color,
          fontSize: 12,
        }}
      >
        {config.label}
      </span>
    );
  }

  function renderTags(tags: string[]) {
    if (!tags || tags.length === 0) return <span style={{ color: "#999" }}>-</span>;
    return (
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        {tags.slice(0, 3).map((tag, idx) => (
          <span
            key={idx}
            style={{
              display: "inline-block",
              padding: "1px 6px",
              borderRadius: 4,
              backgroundColor: "#f3f4f6",
              color: "#374151",
              fontSize: 11,
            }}
          >
            {tag}
          </span>
        ))}
        {tags.length > 3 && (
          <span style={{ color: "#999", fontSize: 11 }}>+{tags.length - 3}</span>
        )}
      </div>
    );
  }

  function formatDate(dateStr?: string) {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <div className="page grid" style={{ position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>客户管理</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="ghost" type="button" onClick={handleExportCustomers}>
            导出CSV
          </button>
          <button className="primary" type="button" onClick={() => setShowCreateForm(!showCreateForm)}>
            {showCreateForm ? "取消" : "新增客户"}
          </button>
        </div>
      </div>

      {/* 新增客户表单 */}
      {showCreateForm && (
        <section className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>新增客户</h3>
          <form onSubmit={onCreateCustomer} className="grid">
            <div className="form-row">
              <div>
                <label>客户昵称 *</label>
                <input value={nickname} onChange={(e) => setNickname(e.target.value)} required />
              </div>
              <div>
                <label>微信号</label>
                <input value={wechatId} onChange={(e) => setWechatId(e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label>手机号</label>
                <input value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
              <div>
                <label>邮箱</label>
                <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label>来源平台 *</label>
                <select value={sourcePlatform} onChange={(e) => setSourcePlatform(e.target.value)}>
                  <option value="xiaohongshu">小红书</option>
                  <option value="douyin">抖音</option>
                  <option value="zhihu">知乎</option>
                  <option value="xianyu">闲鱼</option>
                </select>
              </div>
              <div>
                <label>意向等级</label>
                <select value={intention} onChange={(e) => setIntention(e.target.value)}>
                  <option value="low">C - 低意向</option>
                  <option value="medium">B - 中意向</option>
                  <option value="high">A - 高意向</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div>
                <label>公司名称</label>
                <input value={company} onChange={(e) => setCompany(e.target.value)} />
              </div>
              <div>
                <label>职位</label>
                <input value={position} onChange={(e) => setPosition(e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label>行业</label>
                <input value={industry} onChange={(e) => setIndustry(e.target.value)} />
              </div>
              <div>
                <label>标签（逗号分隔）</label>
                <input value={tags} onChange={(e) => setTags(e.target.value)} />
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <button className="primary" type="submit">保存客户</button>
              <button className="ghost" type="button" onClick={() => setShowCreateForm(false)}>取消</button>
            </div>
          </form>
        </section>
      )}

      {/* 筛选区域 */}
      <section className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div>
            <label>搜索</label>
            <input
              type="text"
              placeholder="昵称/手机/微信..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ minWidth: 200 }}
            />
          </div>
          <div>
            <label>客户状态</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">全部状态</option>
              {Object.entries(customerStatusConfig).map(([key, val]) => (
                <option key={key} value={key}>{val.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label>意向等级</label>
            <select value={intentionFilter} onChange={(e) => setIntentionFilter(e.target.value)}>
              <option value="all">全部等级</option>
              {Object.entries(intentionLevelConfig).map(([key, val]) => (
                <option key={key} value={key}>{val.label} - {key === "high" ? "高" : key === "medium" ? "中" : "低"}意向</option>
              ))}
            </select>
          </div>
        </div>
        {focusCustomerId > 0 && (
          <div className="muted" style={{ marginTop: 10 }}>
            已从线索 #{fromLeadId || "-"} 跳转，定位客户 #{focusCustomerId}
          </div>
        )}
        {message && <div className="muted" style={{ marginTop: 10 }}>{message}</div>}
      </section>

      {/* 客户列表 */}
      <section className="card">
        <h3 style={{ marginTop: 0 }}>客户列表 ({items.length})</h3>
        <div style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th>意向</th>
                <th>昵称</th>
                <th>微信号</th>
                <th>手机号</th>
                <th>来源</th>
                <th>标签</th>
                <th>状态</th>
                <th>跟进次数</th>
                <th>最后跟进</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: "center" }}>加载中...</td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: "center", color: "#999" }}>暂无客户数据</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr
                    key={item.id}
                    style={{
                      ...(item.id === focusCustomerId ? { background: "#fff8e8" } : {}),
                      cursor: "pointer",
                    }}
                    onClick={() => openCustomerDetail(item)}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <select
                        value={item.intention_level}
                        onChange={(e) => handleUpdateIntentionLevel(item.id, e.target.value)}
                        style={{ padding: "2px 4px", fontSize: 12 }}
                      >
                        {Object.entries(intentionLevelConfig).map(([key, val]) => (
                          <option key={key} value={key}>{val.label}</option>
                        ))}
                      </select>
                    </td>
                    <td style={{ fontWeight: 500 }}>{item.nickname}</td>
                    <td>{item.wechat_id || "-"}</td>
                    <td>{item.phone || "-"}</td>
                    <td>{platformLabels[item.source_platform] || item.source_platform}</td>
                    <td>{renderTags(item.tags || [])}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <select
                        value={item.customer_status}
                        onChange={(e) => handleUpdateStatus(item.id, e.target.value)}
                        style={{ padding: "2px 4px", fontSize: 12 }}
                      >
                        {Object.entries(customerStatusConfig).map(([key, val]) => (
                          <option key={key} value={key}>{val.label}</option>
                        ))}
                      </select>
                    </td>
                    <td>{item.follow_count || 0}</td>
                    <td>{formatDate(item.last_follow_at)}</td>
                    <td>{formatDate(item.created_at)}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <button
                        className="ghost"
                        type="button"
                        onClick={() => openCustomerDetail(item)}
                      >
                        详情
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* 客户详情侧滑面板 */}
      {showDetailPanel && selectedCustomer && (
        <div
          style={{
            position: "fixed",
            top: 0,
            right: 0,
            width: 480,
            height: "100vh",
            backgroundColor: "#fff",
            boxShadow: "-2px 0 8px rgba(0,0,0,0.1)",
            zIndex: 1000,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* 面板头部 */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "16px 20px",
              borderBottom: "1px solid #e5e7eb",
              backgroundColor: "#f9fafb",
            }}
          >
            <h3 style={{ margin: 0 }}>客户详情</h3>
            <button
              type="button"
              onClick={closeDetailPanel}
              style={{
                border: "none",
                background: "none",
                fontSize: 20,
                cursor: "pointer",
                color: "#6b7280",
              }}
            >
              ×
            </button>
          </div>

          {/* 面板内容 */}
          <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
            {/* 基本信息 */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                <h4 style={{ margin: 0, flex: 1 }}>{selectedCustomer.nickname}</h4>
                {renderIntentionBadge(selectedCustomer.intention_level)}
                {renderStatusBadge(selectedCustomer.customer_status)}
              </div>
              
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 14 }}>
                <div>
                  <span style={{ color: "#6b7280" }}>微信号：</span>
                  {selectedCustomer.wechat_id || "-"}
                </div>
                <div>
                  <span style={{ color: "#6b7280" }}>手机号：</span>
                  {selectedCustomer.phone || "-"}
                </div>
                <div>
                  <span style={{ color: "#6b7280" }}>来源平台：</span>
                  {platformLabels[selectedCustomer.source_platform] || selectedCustomer.source_platform}
                </div>
                <div>
                  <span style={{ color: "#6b7280" }}>邮箱：</span>
                  {selectedCustomer.email || "-"}
                </div>
                <div>
                  <span style={{ color: "#6b7280" }}>公司：</span>
                  {selectedCustomer.company || "-"}
                </div>
                <div>
                  <span style={{ color: "#6b7280" }}>职位：</span>
                  {selectedCustomer.position || "-"}
                </div>
                <div>
                  <span style={{ color: "#6b7280" }}>行业：</span>
                  {selectedCustomer.industry || "-"}
                </div>
                <div>
                  <span style={{ color: "#6b7280" }}>创建时间：</span>
                  {formatDate(selectedCustomer.created_at)}
                </div>
              </div>

              {/* 标签 */}
              <div style={{ marginTop: 12 }}>
                <span style={{ color: "#6b7280", fontSize: 14 }}>标签：</span>
                {selectedCustomer.tags && selectedCustomer.tags.length > 0 ? (
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                    {selectedCustomer.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 4,
                          backgroundColor: "#dbeafe",
                          color: "#1d4ed8",
                          fontSize: 12,
                        }}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span style={{ color: "#999" }}>-</span>
                )}
              </div>

              {/* 咨询内容 */}
              {selectedCustomer.inquiry_content && (
                <div style={{ marginTop: 12 }}>
                  <span style={{ color: "#6b7280", fontSize: 14 }}>咨询内容：</span>
                  <p style={{ margin: "4px 0 0", fontSize: 14, color: "#374151" }}>
                    {selectedCustomer.inquiry_content}
                  </p>
                </div>
              )}
            </div>

            {/* 快速操作 */}
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ margin: "0 0 12px 0", fontSize: 14, color: "#6b7280" }}>快速操作</h4>
              <div style={{ display: "flex", gap: 8 }}>
                <select
                  value={selectedCustomer.intention_level}
                  onChange={(e) => handleUpdateIntentionLevel(selectedCustomer.id, e.target.value)}
                  style={{ padding: "4px 8px", fontSize: 13 }}
                >
                  {Object.entries(intentionLevelConfig).map(([key, val]) => (
                    <option key={key} value={key}>意向: {val.label}</option>
                  ))}
                </select>
                <select
                  value={selectedCustomer.customer_status}
                  onChange={(e) => handleUpdateStatus(selectedCustomer.id, e.target.value)}
                  style={{ padding: "4px 8px", fontSize: 13 }}
                >
                  {Object.entries(customerStatusConfig).map(([key, val]) => (
                    <option key={key} value={key}>状态: {val.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* 跟进记录时间线 */}
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ margin: "0 0 12px 0", fontSize: 14, color: "#6b7280" }}>跟进记录</h4>
              
              {/* 新增跟进记录表单 */}
              <form onSubmit={handleAddFollowRecord} style={{ marginBottom: 16, padding: 12, backgroundColor: "#f9fafb", borderRadius: 8 }}>
                <div style={{ marginBottom: 8 }}>
                  <select
                    value={followMethod}
                    onChange={(e) => setFollowMethod(e.target.value)}
                    style={{ marginRight: 8, padding: "4px 8px", fontSize: 13 }}
                  >
                    <option value="phone">电话</option>
                    <option value="wechat">微信</option>
                    <option value="visit">上门</option>
                    <option value="other">其他</option>
                  </select>
                  <input
                    type="date"
                    value={nextFollowDate}
                    onChange={(e) => setNextFollowDate(e.target.value)}
                    style={{ padding: "4px 8px", fontSize: 13 }}
                    placeholder="下次跟进日期"
                  />
                </div>
                <textarea
                  value={followContent}
                  onChange={(e) => setFollowContent(e.target.value)}
                  placeholder="输入跟进内容..."
                  style={{ width: "100%", minHeight: 60, padding: 8, fontSize: 13, borderRadius: 4, border: "1px solid #e5e7eb", resize: "vertical" }}
                  required
                />
                <div style={{ marginTop: 8, textAlign: "right" }}>
                  <button
                    className="primary"
                    type="submit"
                    disabled={submitting || !followContent.trim()}
                    style={{ fontSize: 13, padding: "4px 12px" }}
                  >
                    {submitting ? "保存中..." : "添加跟进"}
                  </button>
                </div>
              </form>

              {/* 时间线 */}
              {selectedCustomer.follow_records && selectedCustomer.follow_records.length > 0 ? (
                <div style={{ position: "relative", paddingLeft: 20 }}>
                  {/* 时间线轴 */}
                  <div
                    style={{
                      position: "absolute",
                      left: 6,
                      top: 0,
                      bottom: 0,
                      width: 2,
                      backgroundColor: "#e5e7eb",
                    }}
                  />
                  
                  {selectedCustomer.follow_records.map((record, idx) => (
                    <div
                      key={record.id || idx}
                      style={{
                        position: "relative",
                        paddingBottom: 16,
                      }}
                    >
                      {/* 时间点 */}
                      <div
                        style={{
                          position: "absolute",
                          left: -17,
                          top: 4,
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          backgroundColor: "#3b82f6",
                          border: "2px solid #fff",
                        }}
                      />
                      
                      <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 2 }}>
                        {formatDate(record.created_at)}
                        {record.follow_method && (
                          <span style={{
                            marginLeft: 8,
                            padding: "1px 6px",
                            backgroundColor: "#f3f4f6",
                            borderRadius: 4,
                            fontSize: 11,
                          }}>
                            {record.follow_method === "phone" ? "电话" :
                             record.follow_method === "wechat" ? "微信" :
                             record.follow_method === "visit" ? "上门" : "其他"}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 14, color: "#374151" }}>{record.content}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: "#999", textAlign: "center", padding: 20, fontSize: 14 }}>
                  暂无跟进记录
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 遮罩层 */}
      {showDetailPanel && (
        <div
          onClick={closeDetailPanel}
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 480,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.3)",
            zIndex: 999,
          }}
        />
      )}
    </div>
  );
}
