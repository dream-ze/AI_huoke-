import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { createCustomer, exportCustomersCsv, listCustomers } from "../lib/api";
import { Customer } from "../types";

export function CustomersPage() {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<Customer[]>([]);
  const [nickname, setNickname] = useState("");
  const [wechatId, setWechatId] = useState("");
  const [phone, setPhone] = useState("");
  const [sourcePlatform, setSourcePlatform] = useState("xiaohongshu");
  const [tags, setTags] = useState("新线索");
  const [intention, setIntention] = useState("medium");
  // 扩展字段
  const [company, setCompany] = useState("");
  const [position, setPosition] = useState("");
  const [industry, setIndustry] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const focusCustomerId = Number(searchParams.get("focusCustomerId") || 0);
  const fromLeadId = Number(searchParams.get("fromLeadId") || 0);

  async function fetchData() {
    const data = await listCustomers();
    setItems(data || []);
  }

  useEffect(() => {
    fetchData();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    try {
      await createCustomer({
        nickname,
        wechat_id: wechatId || undefined,
        phone: phone || undefined,
        source_platform: sourcePlatform,
        intention_level: intention,
        tags: tags
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        // 扩展字段
        company: company || undefined,
        position: position || undefined,
        industry: industry || undefined,
        email: email || undefined,
      });
      setNickname("");
      setWechatId("");
      setPhone("");
      setCompany("");
      setPosition("");
      setIndustry("");
      setEmail("");
      setMessage("客户已录入");
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "录入失败");
    }
  }

  async function handleExportCustomers() {
    try {
      const { blob } = await exportCustomersCsv();
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

  return (
    <div className="page grid">
      <h2>客户管理</h2>

      <section className="card">
        <h3>新增客户</h3>
        <form onSubmit={onSubmit} className="grid">
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
                <option value="xianyu">咸鱼</option>
              </select>
            </div>
            <div>
              <label>意向等级</label>
              <select value={intention} onChange={(e) => setIntention(e.target.value)}>
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
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
            <button className="primary" type="submit">
              保存客户
            </button>
            {message && <span className="muted">{message}</span>}
          </div>
        </form>
      </section>

      <section className="card">
        <h3>客户列表</h3>
        <div style={{ marginBottom: 10 }}>
          <button className="ghost" type="button" onClick={handleExportCustomers}>导出客户CSV</button>
        </div>
        {focusCustomerId > 0 && (
          <div className="muted" style={{ marginBottom: 10 }}>
            已从线索 #{fromLeadId || "-"} 跳转，定位客户 #{focusCustomerId}
          </div>
        )}
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>昵称</th>
              <th>微信号</th>
              <th>手机号</th>
              <th>公司</th>
              <th>行业</th>
              <th>来源</th>
              <th>标签</th>
              <th>意向</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} style={item.id === focusCustomerId ? { background: "#fff8e8" } : undefined}>
                <td>{item.id}</td>
                <td>{item.nickname}</td>
                <td>{item.wechat_id || "-"}</td>
                <td>{item.phone || "-"}</td>
                <td>{item.company || "-"}</td>
                <td>{item.industry || "-"}</td>
                <td>{item.source_platform}</td>
                <td>{item.tags?.join(", ") || "-"}</td>
                <td>{item.intention_level}</td>
                <td>{item.customer_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
