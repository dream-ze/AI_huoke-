import { useEffect, useState } from "react";
import { reminderApi } from "../../api/reminderApi";
import type { ReminderConfig, ReminderConfigUpdate, PendingCustomer } from "../../types";

// 提醒原因中文映射
const REMINDER_REASON_LABELS: Record<string, string> = {
  new_customer: "新客户",
  high_intent_overdue: "高意向超时",
  normal_overdue: "常规超时",
  scheduled: "预约跟进",
};

// 意向等级中文映射
const INTENTION_LEVEL_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

export function RemindersPage() {
  const [config, setConfig] = useState<ReminderConfig | null>(null);
  const [pendingCustomers, setPendingCustomers] = useState<PendingCustomer[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  // 表单字段
  const [webhookUrl, setWebhookUrl] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [dailySummaryTime, setDailySummaryTime] = useState("09:00");
  const [newCustomerHours, setNewCustomerHours] = useState(24);
  const [highIntentDays, setHighIntentDays] = useState(3);
  const [normalDays, setNormalDays] = useState(7);

  // 加载数据
  async function loadData() {
    setLoading(true);
    try {
      const [configData, pendingData] = await Promise.all([
        reminderApi.getConfig(),
        reminderApi.getPending(),
      ]);
      
      setConfig(configData);
      setPendingCustomers(pendingData);
      
      // 初始化表单字段
      setWebhookUrl(configData.webhook_url || "");
      setEnabled(configData.enabled);
      setDailySummaryTime(configData.daily_summary_time || "09:00");
      setNewCustomerHours(configData.new_customer_hours);
      setHighIntentDays(configData.high_intent_days);
      setNormalDays(configData.normal_days);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "加载数据失败" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  // 保存配置
  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      const update: ReminderConfigUpdate = {
        webhook_url: webhookUrl || null,
        enabled,
        daily_summary_time: dailySummaryTime,
        new_customer_hours: newCustomerHours,
        high_intent_days: highIntentDays,
        normal_days: normalDays,
      };
      
      const updated = await reminderApi.updateConfig(update);
      setConfig(updated);
      setMessage({ type: "success", text: "配置已保存" });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "保存失败" });
    } finally {
      setSaving(false);
    }
  }

  // 测试 Webhook
  async function handleTestWebhook() {
    setMessage(null);
    try {
      const result = await reminderApi.testWebhook();
      if (result.ok) {
        setMessage({ type: "success", text: "Webhook 测试成功" });
      } else {
        setMessage({ type: "error", text: "Webhook 测试失败，请检查 URL 是否正确" });
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Webhook 测试失败" });
    }
  }

  // 立即发送提醒
  async function handleSendNow() {
    setMessage(null);
    try {
      const result = await reminderApi.sendNow();
      setMessage({ type: "success", text: result.message || "提醒已发送" });
      // 刷新待跟进列表
      const pendingData = await reminderApi.getPending();
      setPendingCustomers(pendingData);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "发送提醒失败" });
    }
  }

  if (loading) {
    return (
      <div className="page grid">
        <p className="muted">加载中...</p>
      </div>
    );
  }

  return (
    <div className="page grid">
      <h2>提醒设置</h2>

      {/* 配置区域 */}
      <section className="card">
        <h3>提醒配置</h3>
        
        <div className="grid" style={{ gap: 16 }}>
          {/* Webhook URL */}
          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 500 }}>
              Webhook URL
            </label>
            <input
              type="url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://your-webhook-url.com/notify"
            />
            <p className="muted" style={{ marginTop: 4, fontSize: 12 }}>
              接收提醒通知的 Webhook 地址（如企业微信机器人）
            </p>
          </div>

          {/* 启用开关 */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <label style={{ fontWeight: 500 }}>启用提醒</label>
            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                style={{ width: "auto" }}
              />
              <span>{enabled ? "已开启" : "已关闭"}</span>
            </label>
          </div>

          {/* 每日汇总时间 */}
          <div className="form-row">
            <div>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 500 }}>
                每日汇总时间
              </label>
              <input
                type="time"
                value={dailySummaryTime}
                onChange={(e) => setDailySummaryTime(e.target.value)}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 500 }}>
                新客户提醒阈值（小时）
              </label>
              <input
                type="number"
                min={1}
                max={168}
                value={newCustomerHours}
                onChange={(e) => setNewCustomerHours(Number(e.target.value))}
              />
            </div>
          </div>

          {/* 跟进天数 */}
          <div className="form-row">
            <div>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 500 }}>
                高意向客户跟进天数
              </label>
              <input
                type="number"
                min={1}
                max={30}
                value={highIntentDays}
                onChange={(e) => setHighIntentDays(Number(e.target.value))}
              />
              <p className="muted" style={{ marginTop: 4, fontSize: 12 }}>
                超过此天数未跟进将触发提醒
              </p>
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 500 }}>
                常规客户跟进天数
              </label>
              <input
                type="number"
                min={1}
                max={60}
                value={normalDays}
                onChange={(e) => setNormalDays(Number(e.target.value))}
              />
              <p className="muted" style={{ marginTop: 4, fontSize: 12 }}>
                超过此天数未跟进将触发提醒
              </p>
            </div>
          </div>

          {/* 消息提示 */}
          {message && (
            <div
              className={message.type === "success" ? "success" : message.type === "error" ? "error" : "muted"}
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                background: message.type === "success" ? "rgba(44, 122, 71, 0.1)" : 
                           message.type === "error" ? "rgba(161, 29, 47, 0.1)" : "transparent",
              }}
            >
              {message.text}
            </div>
          )}

          {/* 操作按钮 */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <button
              className="primary"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "保存中..." : "保存配置"}
            </button>
            <button
              className="secondary"
              onClick={handleTestWebhook}
              disabled={!webhookUrl}
            >
              测试 Webhook
            </button>
            <button
              className="ghost"
              onClick={handleSendNow}
            >
              立即发送提醒
            </button>
          </div>
        </div>
      </section>

      {/* 待跟进客户列表 */}
      <section className="card">
        <h3>待跟进客户 ({pendingCustomers.length})</h3>
        
        {pendingCustomers.length === 0 ? (
          <p className="muted" style={{ padding: "20px 0", textAlign: "center" }}>
            暂无待跟进客户
          </p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>客户ID</th>
                <th>客户昵称</th>
                <th>意向等级</th>
                <th>距今天数</th>
                <th>提醒原因</th>
              </tr>
            </thead>
            <tbody>
              {pendingCustomers.map((customer) => (
                <tr key={customer.customer_id}>
                  <td>{customer.customer_id}</td>
                  <td>{customer.nickname}</td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: 12,
                        fontWeight: 600,
                        background: customer.intention_level === "high" ? "rgba(182, 61, 31, 0.15)" :
                                   customer.intention_level === "medium" ? "rgba(176, 90, 5, 0.15)" :
                                   "rgba(109, 93, 79, 0.15)",
                        color: customer.intention_level === "high" ? "var(--brand)" :
                              customer.intention_level === "medium" ? "var(--warn)" : "var(--muted)",
                      }}
                    >
                      {INTENTION_LEVEL_LABELS[customer.intention_level] || customer.intention_level}
                    </span>
                  </td>
                  <td>{customer.days_since_follow} 天</td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: 12,
                        background: "rgba(15, 109, 122, 0.1)",
                        color: "var(--brand-2)",
                      }}
                    >
                      {REMINDER_REASON_LABELS[customer.reminder_reason] || customer.reminder_reason}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default RemindersPage;
