import { FormEvent, useEffect, useState } from "react";
import { createPublishRecord, listPublishRecords } from "../lib/api";

type PublishRecord = {
  id: number;
  platform: string;
  account_name: string;
  publish_time: string;
  views: number;
  wechat_adds: number;
  leads: number;
  valid_leads: number;
  conversions: number;
};

export function PublishPage() {
  const [list, setList] = useState<PublishRecord[]>([]);
  const [rewrittenContentId, setRewrittenContentId] = useState("1");
  const [platform, setPlatform] = useState("xiaohongshu");
  const [accountName, setAccountName] = useState("主账号");
  const [message, setMessage] = useState("");

  async function fetchData() {
    const data = await listPublishRecords();
    setList(data || []);
  }

  useEffect(() => {
    fetchData();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("");
    try {
      await createPublishRecord({
        rewritten_content_id: Number(rewrittenContentId),
        platform,
        account_name: accountName
      });
      setMessage("发布记录已创建");
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "创建失败（请确认改写内容ID存在）");
    }
  }

  return (
    <div className="page grid">
      <h2>发布记录</h2>

      <section className="card">
        <h3>新增发布记录</h3>
        <form onSubmit={onSubmit} className="grid">
          <div className="form-row">
            <div>
              <label>改写内容ID</label>
              <input
                type="number"
                value={rewrittenContentId}
                onChange={(e) => setRewrittenContentId(e.target.value)}
                min={1}
                required
              />
            </div>
            <div>
              <label>平台</label>
              <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
                <option value="xiaohongshu">小红书</option>
                <option value="douyin">抖音</option>
                <option value="zhihu">知乎</option>
              </select>
            </div>
          </div>

          <div>
            <label>账号名称</label>
            <input value={accountName} onChange={(e) => setAccountName(e.target.value)} required />
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button className="primary" type="submit">
              创建记录
            </button>
            {message && <span className="muted">{message}</span>}
          </div>
        </form>
      </section>

      <section className="card">
        <h3>记录列表</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>账号</th>
              <th>发布时间</th>
              <th>浏览</th>
              <th>加微</th>
              <th>线索</th>
              <th>有效线索</th>
              <th>转化</th>
            </tr>
          </thead>
          <tbody>
            {list.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.platform}</td>
                <td>{item.account_name}</td>
                <td>{new Date(item.publish_time).toLocaleString()}</td>
                <td>{item.views}</td>
                <td>{item.wechat_adds}</td>
                <td>{item.leads}</td>
                <td>{item.valid_leads}</td>
                <td>{item.conversions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
