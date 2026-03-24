import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { assignLeadOwner, convertLeadToCustomer, listLeads, updateLeadStatus } from "../../lib/api";
import { LeadItem } from "../../types";

const statusOptions = ["new", "contacted", "qualified", "converted", "lost"];

export function LeadsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<LeadItem[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const focusLeadId = Number(searchParams.get("focusLeadId") || 0);
  const focusCustomerId = Number(searchParams.get("customerId") || 0);
  const sourceTaskId = Number(searchParams.get("taskId") || 0);

  async function refreshData() {
    const data = await listLeads({ status: statusFilter === "all" ? undefined : statusFilter, limit: 100 });
    setItems(data || []);
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
  }, [statusFilter]);

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

  return (
    <div className="page grid">
      <h2>线索池</h2>

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
        <div className="form-row" style={{ alignItems: "end" }}>
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
        </div>
        {message && <div className="muted" style={{ marginTop: 10 }}>{message}</div>}
      </section>

      <section className="card">
        <h3>线索列表</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>来源任务</th>
              <th>平台</th>
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
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={13}>加载中...</td>
              </tr>
            ) : (
              items.map((item) => {
                const busy = busyId === item.id;
                return (
                  <tr key={item.id} style={item.id === focusLeadId ? { background: "#fff8e8" } : undefined}>
                    <td>{item.id}</td>
                    <td>{item.publish_task_id || "-"}</td>
                    <td>{item.platform}</td>
                    <td>{item.title}</td>
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
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
