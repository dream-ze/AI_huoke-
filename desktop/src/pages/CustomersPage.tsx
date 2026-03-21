import { FormEvent, useEffect, useState } from "react";
import { createCustomer, listCustomers } from "../lib/api";
import { Customer } from "../types";

export function CustomersPage() {
  const [items, setItems] = useState<Customer[]>([]);
  const [nickname, setNickname] = useState("");
  const [wechatId, setWechatId] = useState("");
  const [sourcePlatform, setSourcePlatform] = useState("xiaohongshu");
  const [tags, setTags] = useState("新线索");
  const [intention, setIntention] = useState("medium");
  const [message, setMessage] = useState("");

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
        source_platform: sourcePlatform,
        intention_level: intention,
        tags: tags
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      });
      setNickname("");
      setWechatId("");
      setMessage("客户已录入");
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "录入失败");
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
              <label>客户昵称</label>
              <input value={nickname} onChange={(e) => setNickname(e.target.value)} required />
            </div>
            <div>
              <label>微信号</label>
              <input value={wechatId} onChange={(e) => setWechatId(e.target.value)} />
            </div>
          </div>

          <div className="form-row">
            <div>
              <label>来源平台</label>
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

          <div>
            <label>标签（逗号分隔）</label>
            <input value={tags} onChange={(e) => setTags(e.target.value)} />
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
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>昵称</th>
              <th>微信号</th>
              <th>来源</th>
              <th>标签</th>
              <th>意向</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.nickname}</td>
                <td>{item.wechat_id || "-"}</td>
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
