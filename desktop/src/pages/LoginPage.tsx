import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../lib/api";
import { setToken } from "../lib/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("testuser");
  const [password, setPassword] = useState("password123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(username, password);
      setToken(data.access_token);
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "登录失败，请检查账号密码或后端服务状态");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={handleSubmit}>
        <h2 style={{ marginBottom: 6 }}>欢迎进入智获客</h2>
        <p className="muted" style={{ marginTop: 0, marginBottom: 18 }}>
          先登录，再开始采集、改写、审核和客户跟进
        </p>

        <div style={{ marginBottom: 12 }}>
          <label>用户名</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label>密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <div className="error">{error}</div>}

        <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
          <button className="primary" disabled={loading} type="submit">
            {loading ? "登录中..." : "登录"}
          </button>
        </div>
      </form>
    </div>
  );
}
