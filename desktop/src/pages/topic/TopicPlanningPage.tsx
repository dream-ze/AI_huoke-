import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { topicApi, TopicPlan, TopicIdea, HotTopic, TopicRecommendation, CalendarItem } from "../../api/topicApi";
import { getErrorMessage } from "../../utils/errorHandler";

type TabKey = "plans" | "hot" | "ideas" | "calendar";

const PLATFORMS = [
  { value: "xiaohongshu", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
];

const PLAN_STATUSES = [
  { value: "draft", label: "草稿" },
  { value: "scheduled", label: "已排期" },
  { value: "published", label: "已发布" },
  { value: "archived", label: "已归档" },
];

const IDEA_STATUSES = [
  { value: "pending", label: "待审核" },
  { value: "accepted", label: "已采纳" },
  { value: "rejected", label: "已拒绝" },
  { value: "used", label: "已使用" },
];

const TREND_ICONS: Record<string, string> = {
  up: "↑",
  down: "↓",
  stable: "→",
};

function getPlatformLabel(platform: string): string {
  return PLATFORMS.find(p => p.value === platform)?.label || platform;
}

function getPlanStatusLabel(status: string): string {
  return PLAN_STATUSES.find(s => s.value === status)?.label || status;
}

function getIdeaStatusLabel(status: string): string {
  return IDEA_STATUSES.find(s => s.value === status)?.label || status;
}

function getTrendIcon(direction: string): string {
  return TREND_ICONS[direction] || "→";
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("zh-CN");
}

function getCurrentMonthRange(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return {
    start: start.toISOString().split("T")[0],
    end: end.toISOString().split("T")[0],
  };
}

export function TopicPlanningPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabKey>("plans");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // 选题计划状态
  const [plans, setPlans] = useState<TopicPlan[]>([]);
  const [planPlatformFilter, setPlanPlatformFilter] = useState("all");
  const [planStatusFilter, setPlanStatusFilter] = useState("all");
  const [showPlanForm, setShowPlanForm] = useState(false);
  const [editingPlan, setEditingPlan] = useState<TopicPlan | null>(null);
  const [planForm, setPlanForm] = useState({
    title: "",
    platform: "xiaohongshu",
    target_audience: "",
    content_type: "",
    scheduled_date: "",
    description: "",
  });

  // 热门话题状态
  const [hotTopics, setHotTopics] = useState<HotTopic[]>([]);
  const [hotPlatformFilter, setHotPlatformFilter] = useState("all");
  const [discovering, setDiscovering] = useState(false);

  // 选题创意状态
  const [ideas, setIdeas] = useState<TopicIdea[]>([]);
  const [ideaStatusFilter, setIdeaStatusFilter] = useState("all");
  const [ideaPlatformFilter, setIdeaPlatformFilter] = useState("all");
  const [showIdeaForm, setShowIdeaForm] = useState(false);
  const [ideaForm, setIdeaForm] = useState({
    title: "",
    description: "",
    keywords: "",
    platform: "xiaohongshu",
  });
  const [showRecommendPanel, setShowRecommendPanel] = useState(false);
  const [recommendForm, setRecommendForm] = useState({
    platform: "xiaohongshu",
    audience: "",
    count: 5,
  });
  const [recommending, setRecommending] = useState(false);
  const [recommendations, setRecommendations] = useState<TopicRecommendation[]>([]);

  // 排期日历状态
  const [calendarItems, setCalendarItems] = useState<CalendarItem[]>([]);
  const [calendarRange, setCalendarRange] = useState(getCurrentMonthRange);

  // 加载数据
  useEffect(() => {
    loadTabData();
  }, [activeTab]);

  async function loadTabData() {
    setLoading(true);
    setError("");
    try {
      switch (activeTab) {
        case "plans":
          await loadPlans();
          break;
        case "hot":
          await loadHotTopics();
          break;
        case "ideas":
          await loadIdeas();
          break;
        case "calendar":
          await loadCalendar();
          break;
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadPlans() {
    const result = await topicApi.listPlans({
      platform: planPlatformFilter === "all" ? undefined : planPlatformFilter,
      status: planStatusFilter === "all" ? undefined : planStatusFilter,
      page_size: 50,
    });
    setPlans(result.items || []);
  }

  async function loadHotTopics() {
    const result = await topicApi.listHotTopics({
      platform: hotPlatformFilter === "all" ? undefined : hotPlatformFilter,
      limit: 50,
    });
    setHotTopics(result.items || []);
  }

  async function loadIdeas() {
    const result = await topicApi.listIdeas({
      platform: ideaPlatformFilter === "all" ? undefined : ideaPlatformFilter,
      status: ideaStatusFilter === "all" ? undefined : ideaStatusFilter,
      page_size: 50,
    });
    setIdeas(result.items || []);
  }

  async function loadCalendar() {
    const result = await topicApi.getCalendar(calendarRange.start, calendarRange.end);
    setCalendarItems(result.items || []);
  }

  // 刷新筛选数据
  useEffect(() => {
    if (activeTab === "plans") loadPlans();
  }, [planPlatformFilter, planStatusFilter]);

  useEffect(() => {
    if (activeTab === "hot") loadHotTopics();
  }, [hotPlatformFilter]);

  useEffect(() => {
    if (activeTab === "ideas") loadIdeas();
  }, [ideaPlatformFilter, ideaStatusFilter]);

  useEffect(() => {
    if (activeTab === "calendar") loadCalendar();
  }, [calendarRange]);

  // === 选题计划操作 ===

  function openCreatePlanForm() {
    setEditingPlan(null);
    setPlanForm({
      title: "",
      platform: "xiaohongshu",
      target_audience: "",
      content_type: "",
      scheduled_date: "",
      description: "",
    });
    setShowPlanForm(true);
  }

  function openEditPlanForm(plan: TopicPlan) {
    setEditingPlan(plan);
    setPlanForm({
      title: plan.title,
      platform: plan.platform,
      target_audience: plan.target_audience || "",
      content_type: plan.content_type || "",
      scheduled_date: plan.scheduled_date || "",
      description: plan.description || "",
    });
    setShowPlanForm(true);
  }

  async function handleSavePlan(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    setError("");
    try {
      if (editingPlan) {
        await topicApi.updatePlan(editingPlan.id, planForm);
        setMessage("选题计划已更新");
      } else {
        await topicApi.createPlan(planForm);
        setMessage("选题计划已创建");
      }
      setShowPlanForm(false);
      await loadPlans();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleDeletePlan(id: number) {
    if (!window.confirm("确定要删除该选题计划吗？")) return;
    setMessage("");
    setError("");
    try {
      await topicApi.deletePlan(id);
      setMessage("选题计划已删除");
      await loadPlans();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // === 热门话题操作 ===

  async function handleDiscoverHotTopics() {
    if (hotPlatformFilter === "all") {
      setError("请先选择平台");
      return;
    }
    setDiscovering(true);
    setMessage("");
    setError("");
    try {
      const result = await topicApi.discoverHotTopics(hotPlatformFilter);
      setMessage(`发现 ${result.count} 个热门话题`);
      await loadHotTopics();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDiscovering(false);
    }
  }

  async function handleConvertHotToIdea(topic: HotTopic) {
    setMessage("");
    setError("");
    try {
      await topicApi.createIdea({
        title: topic.topic_name,
        description: topic.description,
        keywords: topic.tags,
        platform: topic.platform,
        source_type: "hot_topic",
        source_hot_topic_id: topic.id,
      });
      setMessage("已将热题转为选题创意");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // === 选题创意操作 ===

  async function handleCreateIdea(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    setError("");
    try {
      await topicApi.createIdea({
        ...ideaForm,
        keywords: ideaForm.keywords.split(/[,，]/).map(k => k.trim()).filter(Boolean),
      });
      setMessage("选题创意已创建");
      setShowIdeaForm(false);
      setIdeaForm({
        title: "",
        description: "",
        keywords: "",
        platform: "xiaohongshu",
      });
      await loadIdeas();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleUpdateIdeaStatus(id: number, status: "pending" | "accepted" | "rejected" | "used") {
    setMessage("");
    setError("");
    try {
      await topicApi.updateIdeaStatus(id, status);
      setMessage("创意状态已更新");
      await loadIdeas();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // === AI 推荐操作 ===

  async function handleRecommend(e: FormEvent) {
    e.preventDefault();
    setRecommending(true);
    setMessage("");
    setError("");
    try {
      const result = await topicApi.recommendTopics(recommendForm);
      setRecommendations(result.recommendations || []);
      setMessage(`获得 ${result.count} 条选题推荐`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setRecommending(false);
    }
  }

  async function handleAdoptRecommendation(rec: TopicRecommendation) {
    setMessage("");
    setError("");
    try {
      await topicApi.createIdea({
        title: rec.title,
        description: rec.description,
        keywords: rec.keywords,
        platform: recommendForm.platform,
        source_type: "ai_recommend",
      });
      setMessage("已将推荐转为选题创意");
      await loadIdeas();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  // === 跳转到 AI 工作台 ===

  function goToWorkbench(plan: TopicPlan) {
    navigate(`/mvp-workbench?topic=${encodeURIComponent(plan.title)}&platform=${plan.platform}`);
  }

  // === 渲染 ===

  return (
    <div className="page grid">
      <h2>选题规划</h2>

      {/* Tab 切换 */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {[
          { key: "plans", label: "选题计划", icon: "📋" },
          { key: "hot", label: "热题推荐", icon: "🔥" },
          { key: "ideas", label: "选题创意", icon: "💡" },
          { key: "calendar", label: "排期日历", icon: "📅" },
        ].map(tab => (
          <button
            key={tab.key}
            className={activeTab === tab.key ? "primary" : "ghost"}
            onClick={() => setActiveTab(tab.key as TabKey)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* 消息提示 */}
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="muted">加载中...</div>
      ) : (
        <>
          {/* Tab 1: 选题计划 */}
          {activeTab === "plans" && (
            <section className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h3>选题计划列表</h3>
                <button className="primary" onClick={openCreatePlanForm}>
                  + 新建选题计划
                </button>
              </div>

              <div className="form-row" style={{ marginBottom: 16 }}>
                <div>
                  <label>平台筛选</label>
                  <select value={planPlatformFilter} onChange={e => setPlanPlatformFilter(e.target.value)}>
                    <option value="all">全部平台</option>
                    {PLATFORMS.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label>状态筛选</label>
                  <select value={planStatusFilter} onChange={e => setPlanStatusFilter(e.target.value)}>
                    <option value="all">全部状态</option>
                    {PLAN_STATUSES.map(s => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {plans.length === 0 ? (
                <div className="muted">暂无选题计划</div>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>标题</th>
                      <th>平台</th>
                      <th>目标人群</th>
                      <th>计划日期</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plans.map(plan => (
                      <tr key={plan.id}>
                        <td>{plan.id}</td>
                        <td>{plan.title}</td>
                        <td>{getPlatformLabel(plan.platform)}</td>
                        <td>{plan.target_audience || "-"}</td>
                        <td>{formatDate(plan.scheduled_date)}</td>
                        <td>
                          <span className={`status-dot ${plan.status === "published" ? "ok" : plan.status === "scheduled" ? "warn" : "muted"}`} />
                          {getPlanStatusLabel(plan.status)}
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <button className="ghost" onClick={() => openEditPlanForm(plan)}>编辑</button>
                            <button className="secondary" onClick={() => goToWorkbench(plan)}>生成内容</button>
                            <button className="ghost" onClick={() => handleDeletePlan(plan.id)}>删除</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          )}

          {/* Tab 2: 热题推荐 */}
          {activeTab === "hot" && (
            <section className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h3>热门话题</h3>
                <div style={{ display: "flex", gap: 8 }}>
                  <select value={hotPlatformFilter} onChange={e => setHotPlatformFilter(e.target.value)}>
                    <option value="all">全部平台</option>
                    {PLATFORMS.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                  <button
                    className="primary"
                    onClick={handleDiscoverHotTopics}
                    disabled={discovering || hotPlatformFilter === "all"}
                  >
                    {discovering ? "发现中..." : "发现热题"}
                  </button>
                </div>
              </div>

              {hotTopics.length === 0 ? (
                <div className="muted">暂无热门话题，点击"发现热题"获取最新热题</div>
              ) : (
                <div className="grid cards" style={{ gap: 12 }}>
                  {hotTopics.map(topic => (
                    <div key={topic.id} className="card" style={{ position: "relative" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                        <span style={{ fontWeight: 600 }}>{topic.topic_name}</span>
                        <span style={{
                          fontSize: 12,
                          padding: "2px 8px",
                          borderRadius: 4,
                          background: topic.trend_direction === "up" ? "#dcfce7" : topic.trend_direction === "down" ? "#fee2e2" : "#f3f4f6",
                          color: topic.trend_direction === "up" ? "#166534" : topic.trend_direction === "down" ? "#991b1b" : "#374151",
                        }}>
                          {getTrendIcon(topic.trend_direction)} {topic.heat_score.toFixed(0)}
                        </span>
                      </div>
                      <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
                        {getPlatformLabel(topic.platform)} · {topic.category || "未分类"}
                      </div>
                      {topic.description && (
                        <div style={{ fontSize: 13, marginBottom: 8 }}>{topic.description}</div>
                      )}
                      {topic.tags && topic.tags.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 12 }}>
                          {topic.tags.slice(0, 5).map((tag, i) => (
                            <span key={i} style={{
                              fontSize: 11,
                              padding: "2px 6px",
                              background: "rgba(15, 109, 122, 0.1)",
                              borderRadius: 4,
                              color: "var(--brand-2)",
                            }}>{tag}</span>
                          ))}
                        </div>
                      )}
                      <button
                        className="ghost"
                        style={{ width: "100%" }}
                        onClick={() => handleConvertHotToIdea(topic)}
                      >
                        转为选题创意
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Tab 3: 选题创意 */}
          {activeTab === "ideas" && (
            <section className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h3>选题创意</h3>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="ghost" onClick={() => setShowRecommendPanel(true)}>
                    AI 推荐
                  </button>
                  <button className="primary" onClick={() => setShowIdeaForm(true)}>
                    + 添加创意
                  </button>
                </div>
              </div>

              <div className="form-row" style={{ marginBottom: 16 }}>
                <div>
                  <label>平台筛选</label>
                  <select value={ideaPlatformFilter} onChange={e => setIdeaPlatformFilter(e.target.value)}>
                    <option value="all">全部平台</option>
                    {PLATFORMS.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label>状态筛选</label>
                  <select value={ideaStatusFilter} onChange={e => setIdeaStatusFilter(e.target.value)}>
                    <option value="all">全部状态</option>
                    {IDEA_STATUSES.map(s => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {ideas.length === 0 ? (
                <div className="muted">暂无选题创意</div>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>标题</th>
                      <th>平台</th>
                      <th>来源</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ideas.map(idea => (
                      <tr key={idea.id}>
                        <td>{idea.id}</td>
                        <td>{idea.title}</td>
                        <td>{getPlatformLabel(idea.platform)}</td>
                        <td>{idea.source_type === "hot_topic" ? "热题" : idea.source_type === "ai_recommend" ? "AI推荐" : "手动"}</td>
                        <td>
                          <span className={`status-dot ${idea.status === "accepted" || idea.status === "used" ? "ok" : idea.status === "rejected" ? "danger" : "warn"}`} />
                          {getIdeaStatusLabel(idea.status)}
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            {idea.status === "pending" && (
                              <>
                                <button className="secondary" onClick={() => handleUpdateIdeaStatus(idea.id, "accepted")}>采纳</button>
                                <button className="ghost" onClick={() => handleUpdateIdeaStatus(idea.id, "rejected")}>拒绝</button>
                              </>
                            )}
                            {idea.status === "accepted" && (
                              <button className="ghost" onClick={() => handleUpdateIdeaStatus(idea.id, "used")}>标记已使用</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          )}

          {/* Tab 4: 排期日历 */}
          {activeTab === "calendar" && (
            <section className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h3>排期日历</h3>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    type="date"
                    value={calendarRange.start}
                    onChange={e => setCalendarRange(r => ({ ...r, start: e.target.value }))}
                  />
                  <span style={{ lineHeight: "40px" }}>至</span>
                  <input
                    type="date"
                    value={calendarRange.end}
                    onChange={e => setCalendarRange(r => ({ ...r, end: e.target.value }))}
                  />
                </div>
              </div>

              {calendarItems.length === 0 ? (
                <div className="muted">该时间段内暂无选题排期</div>
              ) : (
                <div className="grid" style={{ gap: 12 }}>
                  {calendarItems.map(item => (
                    <div key={item.date} className="card" style={{ padding: 12 }}>
                      <div style={{ fontWeight: 600, marginBottom: 8 }}>{item.date} ({item.count} 条)</div>
                      {item.plans.length > 0 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {item.plans.map(plan => (
                            <div
                              key={plan.id}
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                padding: "6px 10px",
                                background: "#fafafa",
                                borderRadius: 6,
                              }}
                            >
                              <span>{plan.title}</span>
                              <span style={{ fontSize: 12, color: "var(--muted)" }}>{getPlatformLabel(plan.platform)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}

      {/* 选题计划表单弹窗 */}
      {showPlanForm && (
        <section className="card">
          <h3>{editingPlan ? "编辑选题计划" : "新建选题计划"}</h3>
          <form onSubmit={handleSavePlan} className="grid">
            <div className="form-row">
              <div>
                <label>标题 *</label>
                <input
                  value={planForm.title}
                  onChange={e => setPlanForm(f => ({ ...f, title: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label>平台 *</label>
                <select
                  value={planForm.platform}
                  onChange={e => setPlanForm(f => ({ ...f, platform: e.target.value }))}
                  required
                >
                  {PLATFORMS.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div>
                <label>目标人群</label>
                <input
                  value={planForm.target_audience}
                  onChange={e => setPlanForm(f => ({ ...f, target_audience: e.target.value }))}
                />
              </div>
              <div>
                <label>内容类型</label>
                <input
                  value={planForm.content_type}
                  onChange={e => setPlanForm(f => ({ ...f, content_type: e.target.value }))}
                  placeholder="如: 图文、视频"
                />
              </div>
            </div>
            <div>
              <label>计划发布日期</label>
              <input
                type="date"
                value={planForm.scheduled_date}
                onChange={e => setPlanForm(f => ({ ...f, scheduled_date: e.target.value }))}
              />
            </div>
            <div>
              <label>描述说明</label>
              <textarea
                value={planForm.description}
                onChange={e => setPlanForm(f => ({ ...f, description: e.target.value }))}
                style={{ minHeight: 80 }}
              />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="primary" type="submit">{editingPlan ? "保存修改" : "创建计划"}</button>
              <button className="ghost" type="button" onClick={() => setShowPlanForm(false)}>取消</button>
            </div>
          </form>
        </section>
      )}

      {/* 添加创意表单弹窗 */}
      {showIdeaForm && (
        <section className="card">
          <h3>添加选题创意</h3>
          <form onSubmit={handleCreateIdea} className="grid">
            <div>
              <label>标题 *</label>
              <input
                value={ideaForm.title}
                onChange={e => setIdeaForm(f => ({ ...f, title: e.target.value }))}
                required
              />
            </div>
            <div className="form-row">
              <div>
                <label>平台 *</label>
                <select
                  value={ideaForm.platform}
                  onChange={e => setIdeaForm(f => ({ ...f, platform: e.target.value }))}
                  required
                >
                  {PLATFORMS.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>关键词（逗号分隔）</label>
                <input
                  value={ideaForm.keywords}
                  onChange={e => setIdeaForm(f => ({ ...f, keywords: e.target.value }))}
                  placeholder="如: 负债优化, 征信修复"
                />
              </div>
            </div>
            <div>
              <label>描述说明</label>
              <textarea
                value={ideaForm.description}
                onChange={e => setIdeaForm(f => ({ ...f, description: e.target.value }))}
                style={{ minHeight: 80 }}
              />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="primary" type="submit">添加创意</button>
              <button className="ghost" type="button" onClick={() => setShowIdeaForm(false)}>取消</button>
            </div>
          </form>
        </section>
      )}

      {/* AI 推荐面板 */}
      {showRecommendPanel && (
        <section className="card">
          <h3>AI 选题推荐</h3>
          <form onSubmit={handleRecommend} className="grid">
            <div className="form-row">
              <div>
                <label>平台 *</label>
                <select
                  value={recommendForm.platform}
                  onChange={e => setRecommendForm(f => ({ ...f, platform: e.target.value }))}
                  required
                >
                  {PLATFORMS.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>目标人群</label>
                <input
                  value={recommendForm.audience}
                  onChange={e => setRecommendForm(f => ({ ...f, audience: e.target.value }))}
                  placeholder="如: 有负债困扰的年轻人"
                />
              </div>
              <div>
                <label>推荐数量</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={recommendForm.count}
                  onChange={e => setRecommendForm(f => ({ ...f, count: Number(e.target.value) }))}
                />
              </div>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="primary" type="submit" disabled={recommending}>
                {recommending ? "推荐中..." : "获取推荐"}
              </button>
              <button className="ghost" type="button" onClick={() => { setShowRecommendPanel(false); setRecommendations([]); }}>
                关闭
              </button>
            </div>
          </form>

          {recommendations.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ marginBottom: 12 }}>推荐结果</h4>
              <div className="grid" style={{ gap: 12 }}>
                {recommendations.map((rec, i) => (
                  <div key={i} className="card" style={{ padding: 12, background: "#fafafa" }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>{rec.title}</div>
                    <div style={{ fontSize: 13, marginBottom: 8 }}>{rec.description}</div>
                    <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>
                      关键词: {rec.keywords.join(", ")}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--brand-2)", marginBottom: 12 }}>
                      推荐理由: {rec.reason}
                    </div>
                    <button
                      className="ghost"
                      style={{ width: "100%" }}
                      onClick={() => handleAdoptRecommendation(rec)}
                    >
                      采纳此创意
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default TopicPlanningPage;
