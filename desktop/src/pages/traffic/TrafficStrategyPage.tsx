import { FormEvent, useEffect, useState } from "react";
import { trafficApi } from "../../api/trafficApi";
import type { TrafficStrategy, TrafficStrategySummary } from "../../types";

const PLATFORM_OPTIONS = [
  { value: "xiaohongshu", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
];

const STRATEGY_TYPE_OPTIONS = [
  { value: "cta", label: "CTA引导" },
  { value: "comment_guide", label: "评论引导" },
  { value: "profile_link", label: "主页链接" },
  { value: "live_stream", label: "直播引流" },
  { value: "group", label: "社群引流" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "进行中" },
  { value: "paused", label: "已暂停" },
  { value: "archived", label: "已归档" },
];

export function TrafficStrategyPage() {
  // 列表数据
  const [strategies, setStrategies] = useState<TrafficStrategy[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // 筛选条件
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  // 汇总数据
  const [summary, setSummary] = useState<TrafficStrategySummary | null>(null);

  // 表单数据
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Partial<TrafficStrategy>>({
    name: "",
    platform: "xiaohongshu",
    strategy_type: "cta",
    target_audience: "",
    cta_template: "",
    budget: undefined,
    description: "",
    status: "active",
    start_date: "",
    end_date: "",
  });

  // 指标编辑
  const [editingMetricsId, setEditingMetricsId] = useState<number | null>(null);
  const [metricsData, setMetricsData] = useState({
    views: 0,
    clicks: 0,
    leads: 0,
    conversions: 0,
  });

  async function fetchData() {
    setLoading(true);
    try {
      const result = await trafficApi.listStrategies({
        platform: filterPlatform || undefined,
        status: filterStatus || undefined,
        page,
        page_size: pageSize,
      });
      setStrategies(result.items);
      setTotal(result.total);
    } catch (err: any) {
      setMessage(err?.message || "获取数据失败");
    } finally {
      setLoading(false);
    }
  }

  async function fetchSummary() {
    try {
      const result = await trafficApi.getSummary();
      setSummary(result);
    } catch (err: any) {
      console.warn("获取汇总数据失败:", err);
    }
  }

  useEffect(() => {
    fetchData();
    fetchSummary();
  }, [page, filterPlatform, filterStatus]);

  function resetForm() {
    setFormData({
      name: "",
      platform: "xiaohongshu",
      strategy_type: "cta",
      target_audience: "",
      cta_template: "",
      budget: undefined,
      description: "",
      status: "active",
      start_date: "",
      end_date: "",
    });
    setEditingId(null);
  }

  function handleEdit(strategy: TrafficStrategy) {
    setFormData({
      name: strategy.name,
      platform: strategy.platform,
      strategy_type: strategy.strategy_type,
      target_audience: strategy.target_audience || "",
      cta_template: strategy.cta_template || "",
      budget: strategy.budget,
      description: strategy.description || "",
      status: strategy.status,
      start_date: strategy.start_date || "",
      end_date: strategy.end_date || "",
    });
    setEditingId(strategy.id);
    setShowForm(true);
  }

  function handleEditMetrics(strategy: TrafficStrategy) {
    const metrics = strategy.performance_metrics || {};
    setMetricsData({
      views: metrics.views || 0,
      clicks: metrics.clicks || 0,
      leads: metrics.leads || 0,
      conversions: metrics.conversions || 0,
    });
    setEditingMetricsId(strategy.id);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    try {
      const submitData = {
        ...formData,
        budget: formData.budget ? Number(formData.budget) : undefined,
      };

      if (editingId) {
        await trafficApi.updateStrategy(editingId, submitData);
        setMessage("策略已更新");
      } else {
        await trafficApi.createStrategy(submitData);
        setMessage("策略已创建");
      }
      resetForm();
      setShowForm(false);
      await fetchData();
      await fetchSummary();
    } catch (err: any) {
      setMessage(err?.message || "保存失败");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("确定要删除这个策略吗？")) return;
    try {
      await trafficApi.deleteStrategy(id);
      setMessage("策略已删除");
      await fetchData();
      await fetchSummary();
    } catch (err: any) {
      setMessage(err?.message || "删除失败");
    }
  }

  async function handleMetricsSubmit() {
    if (!editingMetricsId) return;
    try {
      await trafficApi.updateMetrics(editingMetricsId, metricsData);
      setMessage("指标已更新");
      setEditingMetricsId(null);
      await fetchData();
      await fetchSummary();
    } catch (err: any) {
      setMessage(err?.message || "更新指标失败");
    }
  }

  function getPlatformLabel(value: string) {
    return PLATFORM_OPTIONS.find((o) => o.value === value)?.label || value;
  }

  function getStrategyTypeLabel(value: string) {
    return STRATEGY_TYPE_OPTIONS.find((o) => o.value === value)?.label || value;
  }

  function getStatusLabel(value: string) {
    return STATUS_OPTIONS.find((o) => o.value === value)?.label || value;
  }

  function getStatusClass(status: string) {
    switch (status) {
      case "active":
        return "status-active";
      case "paused":
        return "status-paused";
      case "archived":
        return "status-archived";
      default:
        return "";
    }
  }

  return (
    <div className="page grid">
      <h2>引流策略管理</h2>

      {/* 汇总统计面板 */}
      {summary && (
        <section className="card">
          <h3>效果汇总</h3>
          <div className="stats-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 16, marginBottom: 16 }}>
            <div className="stat-card">
              <div className="stat-value">{summary.total_strategies}</div>
              <div className="stat-label">策略总数</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">¥{summary.total_budget.toLocaleString()}</div>
              <div className="stat-label">总预算</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.performance.total_views.toLocaleString()}</div>
              <div className="stat-label">总曝光</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.performance.total_clicks.toLocaleString()}</div>
              <div className="stat-label">总点击</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.performance.total_leads.toLocaleString()}</div>
              <div className="stat-label">总线索</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.performance.total_conversions.toLocaleString()}</div>
              <div className="stat-label">总转化</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">¥{summary.performance.cost_per_lead}</div>
              <div className="stat-label">单线索成本</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.performance.conversion_rate}%</div>
              <div className="stat-label">转化率</div>
            </div>
          </div>

          {summary.by_platform.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4>平台分布</h4>
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                {summary.by_platform.map((item) => (
                  <div key={item.platform} className="platform-stat">
                    <span>{getPlatformLabel(item.platform)}:</span>
                    <span>{item.strategy_count}个策略</span>
                    <span>¥{item.total_budget.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* 筛选和新增 */}
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <select value={filterPlatform} onChange={(e) => setFilterPlatform(e.target.value)}>
              <option value="">所有平台</option>
              {PLATFORM_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">所有状态</option>
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <button className="ghost" onClick={() => { setFilterPlatform(""); setFilterStatus(""); }}>
              重置筛选
            </button>
          </div>
          <button
            className="primary"
            onClick={() => {
              resetForm();
              setShowForm(!showForm);
            }}
          >
            {showForm ? "取消" : "+ 新建策略"}
          </button>
        </div>
        {message && <div className="muted" style={{ marginTop: 8 }}>{message}</div>}
      </section>

      {/* 创建/编辑表单 */}
      {showForm && (
        <section className="card">
          <h3>{editingId ? "编辑策略" : "新建策略"}</h3>
          <form onSubmit={handleSubmit} className="grid">
            <div className="form-row">
              <div>
                <label>策略名称 *</label>
                <input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  placeholder="例如：小红书私信引流策略"
                />
              </div>
              <div>
                <label>平台 *</label>
                <select
                  value={formData.platform}
                  onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                  required
                >
                  {PLATFORM_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div>
                <label>策略类型 *</label>
                <select
                  value={formData.strategy_type}
                  onChange={(e) => setFormData({ ...formData, strategy_type: e.target.value })}
                  required
                >
                  {STRATEGY_TYPE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>目标受众</label>
                <input
                  value={formData.target_audience}
                  onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
                  placeholder="例如：25-35岁职场女性"
                />
              </div>
            </div>

            <div className="form-row">
              <div>
                <label>预算（元）</label>
                <input
                  type="number"
                  value={formData.budget || ""}
                  onChange={(e) => setFormData({ ...formData, budget: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="5000"
                  min="0"
                  step="0.01"
                />
              </div>
              <div>
                <label>状态</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div>
                <label>开始日期</label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                />
              </div>
              <div>
                <label>结束日期</label>
                <input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label>CTA话术模板</label>
              <textarea
                value={formData.cta_template}
                onChange={(e) => setFormData({ ...formData, cta_template: e.target.value })}
                placeholder="例如：感兴趣的朋友可以私信我获取详细方案~"
                rows={3}
              />
            </div>

            <div>
              <label>策略描述</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="描述这个策略的目标、执行方式等..."
                rows={3}
              />
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button className="primary" type="submit">
                {editingId ? "保存修改" : "创建策略"}
              </button>
              <button className="ghost" type="button" onClick={() => { resetForm(); setShowForm(false); }}>
                取消
              </button>
            </div>
          </form>
        </section>
      )}

      {/* 策略列表 */}
      <section className="card">
        <h3>策略列表 ({total})</h3>
        {loading ? (
          <div className="muted">加载中...</div>
        ) : strategies.length === 0 ? (
          <div className="muted">暂无策略，点击上方"新建策略"按钮创建</div>
        ) : (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>名称</th>
                  <th>平台</th>
                  <th>类型</th>
                  <th>预算</th>
                  <th>状态</th>
                  <th>线索/转化</th>
                  <th>日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {strategies.map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td>{item.name}</td>
                    <td>{getPlatformLabel(item.platform)}</td>
                    <td>{getStrategyTypeLabel(item.strategy_type)}</td>
                    <td>¥{item.budget?.toLocaleString() || "-"}</td>
                    <td>
                      <span className={`status-badge ${getStatusClass(item.status)}`}>
                        {getStatusLabel(item.status)}
                      </span>
                    </td>
                    <td>
                      {item.performance_metrics?.leads || 0} / {item.performance_metrics?.conversions || 0}
                    </td>
                    <td>
                      {item.start_date ? new Date(item.start_date).toLocaleDateString() : "-"}
                      {item.end_date ? ` ~ ${new Date(item.end_date).toLocaleDateString()}` : ""}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button className="ghost" onClick={() => handleEdit(item)}>编辑</button>
                        <button className="ghost" onClick={() => handleEditMetrics(item)}>指标</button>
                        <button className="ghost danger" onClick={() => handleDelete(item.id)}>删除</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* 分页 */}
            {total > pageSize && (
              <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
                <button
                  className="ghost"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  上一页
                </button>
                <span className="muted">第 {page} 页 / 共 {Math.ceil(total / pageSize)} 页</span>
                <button
                  className="ghost"
                  disabled={page >= Math.ceil(total / pageSize)}
                  onClick={() => setPage(page + 1)}
                >
                  下一页
                </button>
              </div>
            )}
          </>
        )}
      </section>

      {/* 指标编辑弹窗 */}
      {editingMetricsId && (
        <div className="modal-overlay" style={{
          position: "fixed",
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
        }}>
          <div className="card" style={{ minWidth: 400, maxWidth: 500 }}>
            <h3>更新效果指标</h3>
            <div className="grid">
              <div className="form-row">
                <div>
                  <label>曝光量</label>
                  <input
                    type="number"
                    value={metricsData.views}
                    onChange={(e) => setMetricsData({ ...metricsData, views: Number(e.target.value) })}
                    min="0"
                  />
                </div>
                <div>
                  <label>点击量</label>
                  <input
                    type="number"
                    value={metricsData.clicks}
                    onChange={(e) => setMetricsData({ ...metricsData, clicks: Number(e.target.value) })}
                    min="0"
                  />
                </div>
              </div>
              <div className="form-row">
                <div>
                  <label>线索数</label>
                  <input
                    type="number"
                    value={metricsData.leads}
                    onChange={(e) => setMetricsData({ ...metricsData, leads: Number(e.target.value) })}
                    min="0"
                  />
                </div>
                <div>
                  <label>转化数</label>
                  <input
                    type="number"
                    value={metricsData.conversions}
                    onChange={(e) => setMetricsData({ ...metricsData, conversions: Number(e.target.value) })}
                    min="0"
                  />
                </div>
              </div>
              <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
                <button className="primary" onClick={handleMetricsSubmit}>保存</button>
                <button className="ghost" onClick={() => setEditingMetricsId(null)}>取消</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
