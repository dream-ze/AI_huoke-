import { FormEvent, useEffect, useState } from "react";
import {
  listSocialAccounts,
  createSocialAccount,
  updateSocialAccount,
  deleteSocialAccount,
  getSocialPlatforms,
} from "../../lib/api";

interface SocialAccount {
  id: number;
  owner_id: number;
  platform: string;
  account_id: string | null;
  account_name: string;
  avatar_url: string | null;
  status: string;
  followers_count: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface Platform {
  value: string;
  label: string;
}

const PLATFORM_LABELS: Record<string, string> = {
  xiaohongshu: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
  weixin: "微信",
  xianyu: "咸鱼",
  other: "其他",
};

const STATUS_LABELS: Record<string, string> = {
  active: "正常",
  inactive: "停用",
  expired: "过期",
};

const STATUS_COLORS: Record<string, string> = {
  active: "#52c41a",
  inactive: "#faad14",
  expired: "#ff4d4f",
};

export function SocialAccountsPage() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [platformFilter, setPlatformFilter] = useState("all");

  // 新增/编辑表单状态
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    platform: "xiaohongshu",
    account_name: "",
    account_id: "",
    avatar_url: "",
    notes: "",
    status: "active",
    followers_count: 0,
  });

  async function fetchData() {
    setLoading(true);
    try {
      const [accountsData, platformsData] = await Promise.all([
        listSocialAccounts(platformFilter === "all" ? undefined : platformFilter),
        getSocialPlatforms().catch(() => []),
      ]);
      setAccounts(accountsData || []);
      setPlatforms(platformsData || []);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "加载数据失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, [platformFilter]);

  function resetForm() {
    setFormData({
      platform: "xiaohongshu",
      account_name: "",
      account_id: "",
      avatar_url: "",
      notes: "",
      status: "active",
      followers_count: 0,
    });
    setEditingId(null);
    setShowForm(false);
  }

  function openEditForm(account: SocialAccount) {
    setFormData({
      platform: account.platform,
      account_name: account.account_name,
      account_id: account.account_id || "",
      avatar_url: account.avatar_url || "",
      notes: account.notes || "",
      status: account.status,
      followers_count: account.followers_count,
    });
    setEditingId(account.id);
    setShowForm(true);
    setMessage("");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("");

    try {
      if (editingId) {
        await updateSocialAccount(editingId, {
          account_name: formData.account_name,
          account_id: formData.account_id || undefined,
          avatar_url: formData.avatar_url || undefined,
          status: formData.status,
          followers_count: formData.followers_count,
          notes: formData.notes || undefined,
        });
        setMessage("账号已更新");
      } else {
        await createSocialAccount({
          platform: formData.platform,
          account_name: formData.account_name,
          account_id: formData.account_id || undefined,
          avatar_url: formData.avatar_url || undefined,
          notes: formData.notes || undefined,
        });
        setMessage("账号已添加");
      }
      resetForm();
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "操作失败");
    }
  }

  async function handleDelete(id: number, accountName: string) {
    if (!window.confirm(`确定要删除账号 "${accountName}" 吗？`)) {
      return;
    }
    setMessage("");
    try {
      await deleteSocialAccount(id);
      setMessage("账号已删除");
      await fetchData();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "删除失败");
    }
  }

  function getPlatformLabel(value: string): string {
    return PLATFORM_LABELS[value] || value;
  }

  return (
    <div className="page grid">
      <h2>社交账号管理</h2>

      {/* 平台筛选 */}
      <section className="card">
        <div className="form-row" style={{ marginBottom: 0 }}>
          <div>
            <label>平台筛选</label>
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
            >
              <option value="all">全部平台</option>
              {Object.entries(PLATFORM_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "flex-end" }}>
            <button
              className="primary"
              onClick={() => {
                resetForm();
                setShowForm(true);
                setMessage("");
              }}
            >
              + 新增账号
            </button>
          </div>
        </div>
      </section>

      {/* 新增/编辑表单 */}
      {showForm && (
        <section className="card">
          <h3>{editingId ? "编辑账号" : "新增账号"}</h3>
          <form onSubmit={onSubmit} className="grid">
            <div className="form-row">
              <div>
                <label>平台 *</label>
                <select
                  value={formData.platform}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, platform: e.target.value }))
                  }
                  disabled={!!editingId}
                  required
                >
                  {Object.entries(PLATFORM_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label>账号名称 *</label>
                <input
                  value={formData.account_name}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, account_name: e.target.value }))
                  }
                  placeholder="显示名称"
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div>
                <label>平台账号ID</label>
                <input
                  value={formData.account_id}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, account_id: e.target.value }))
                  }
                  placeholder="平台内的账号ID（可选）"
                />
              </div>
              <div>
                <label>头像URL</label>
                <input
                  value={formData.avatar_url}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, avatar_url: e.target.value }))
                  }
                  placeholder="头像图片链接（可选）"
                />
              </div>
            </div>

            {editingId && (
              <div className="form-row">
                <div>
                  <label>状态</label>
                  <select
                    value={formData.status}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, status: e.target.value }))
                    }
                  >
                    <option value="active">正常</option>
                    <option value="inactive">停用</option>
                    <option value="expired">过期</option>
                  </select>
                </div>
                <div>
                  <label>粉丝数</label>
                  <input
                    type="number"
                    min={0}
                    value={formData.followers_count}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        followers_count: parseInt(e.target.value) || 0,
                      }))
                    }
                  />
                </div>
              </div>
            )}

            <div>
              <label>备注</label>
              <input
                value={formData.notes}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, notes: e.target.value }))
                }
                placeholder="备注信息（可选）"
              />
            </div>

            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <button className="primary" type="submit">
                {editingId ? "保存修改" : "添加账号"}
              </button>
              <button
                className="ghost"
                type="button"
                onClick={() => {
                  resetForm();
                  setMessage("");
                }}
              >
                取消
              </button>
              {message && <span className="muted">{message}</span>}
            </div>
          </form>
        </section>
      )}

      {/* 账号列表 */}
      <section className="card">
        <h3>账号列表</h3>
        {loading ? (
          <div className="muted">加载中...</div>
        ) : accounts.length === 0 ? (
          <div className="muted">暂无账号，请点击"新增账号"添加</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>平台</th>
                <th>账号名称</th>
                <th>平台ID</th>
                <th>状态</th>
                <th>粉丝数</th>
                <th>备注</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <tr key={account.id}>
                  <td>{account.id}</td>
                  <td>{getPlatformLabel(account.platform)}</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {account.avatar_url && (
                        <img
                          src={account.avatar_url}
                          alt=""
                          style={{
                            width: 24,
                            height: 24,
                            borderRadius: "50%",
                            objectFit: "cover",
                          }}
                        />
                      )}
                      <span>{account.account_name}</span>
                    </div>
                  </td>
                  <td>{account.account_id || "-"}</td>
                  <td>
                    <span
                      style={{
                        color: STATUS_COLORS[account.status] || "#666",
                        fontWeight: 500,
                      }}
                    >
                      {STATUS_LABELS[account.status] || account.status}
                    </span>
                  </td>
                  <td>{account.followers_count.toLocaleString()}</td>
                  <td>{account.notes || "-"}</td>
                  <td>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        className="ghost"
                        type="button"
                        onClick={() => openEditForm(account)}
                      >
                        编辑
                      </button>
                      <button
                        className="ghost"
                        type="button"
                        style={{ color: "#ff4d4f" }}
                        onClick={() => handleDelete(account.id, account.account_name)}
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!showForm && message && (
          <div style={{ marginTop: 10 }} className="muted">
            {message}
          </div>
        )}
      </section>
    </div>
  );
}
