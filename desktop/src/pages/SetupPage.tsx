import { useState } from "react";

interface DbConfig {
  DATABASE_HOST: string;
  DATABASE_PORT: string;
  DATABASE_USER: string;
  DATABASE_PASSWORD: string;
  DATABASE_NAME: string;
  SECRET_KEY: string;
  BACKEND_PORT: string;
}

interface Props {
  initialConfig?: Partial<DbConfig>;
  onSaved: () => void;
}

export function SetupPage({ initialConfig, onSaved }: Props) {
  const [cfg, setCfg] = useState<DbConfig>({
    DATABASE_HOST: "localhost",
    DATABASE_PORT: "5432",
    DATABASE_USER: "postgres",
    DATABASE_PASSWORD: "password",
    DATABASE_NAME: "zhihuokeke",
    SECRET_KEY: "zhihuokeke-secret-key-change-me",
    BACKEND_PORT: "8000",
    ...initialConfig,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const field = (
    label: string,
    key: keyof DbConfig,
    type = "text",
    placeholder = ""
  ) => (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "block", marginBottom: 4, color: "#ccc", fontSize: 13 }}>
        {label}
      </label>
      <input
        type={type}
        value={cfg[key]}
        placeholder={placeholder}
        onChange={(e) => setCfg((c) => ({ ...c, [key]: e.target.value }))}
        style={{
          width: "100%",
          padding: "8px 10px",
          background: "#2a2a3a",
          border: "1px solid #444",
          borderRadius: 6,
          color: "#fff",
          fontSize: 14,
          boxSizing: "border-box",
        }}
      />
    </div>
  );

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const result = await (window as any).desktop.saveDbConfig(cfg);
      if (result.ok) {
        onSaved();
      } else {
        setError(`连接失败: ${result.error || "请检查数据库配置"}`);
      }
    } catch (e: any) {
      setError(e.message || "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      <div
        style={{
          width: 460,
          background: "#1e1e2e",
          borderRadius: 16,
          padding: "36px 40px",
          boxShadow: "0 8px 48px rgba(0,0,0,0.5)",
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>🎯</div>
          <h1 style={{ color: "#fff", fontSize: 22, fontWeight: 700, margin: 0 }}>
            智获客
          </h1>
          <p style={{ color: "#888", fontSize: 13, marginTop: 8, margin: "8px 0 0" }}>
            首次启动，请配置 PostgreSQL 数据库连接
          </p>
        </div>

        {/* 字段 */}
        {field("数据库主机", "DATABASE_HOST", "text", "localhost")}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={{ display: "block", marginBottom: 4, color: "#ccc", fontSize: 13 }}>
              端口
            </label>
            <input
              type="text"
              value={cfg.DATABASE_PORT}
              onChange={(e) => setCfg((c) => ({ ...c, DATABASE_PORT: e.target.value }))}
              style={{
                width: "100%",
                padding: "8px 10px",
                background: "#2a2a3a",
                border: "1px solid #444",
                borderRadius: 6,
                color: "#fff",
                fontSize: 14,
                boxSizing: "border-box",
              }}
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, color: "#ccc", fontSize: 13 }}>
              后端服务端口
            </label>
            <input
              type="text"
              value={cfg.BACKEND_PORT}
              onChange={(e) => setCfg((c) => ({ ...c, BACKEND_PORT: e.target.value }))}
              style={{
                width: "100%",
                padding: "8px 10px",
                background: "#2a2a3a",
                border: "1px solid #444",
                borderRadius: 6,
                color: "#fff",
                fontSize: 14,
                boxSizing: "border-box",
              }}
            />
          </div>
        </div>
        <div style={{ marginBottom: 14 }} />
        {field("数据库名", "DATABASE_NAME", "text", "zhihuokeke")}
        {field("用户名", "DATABASE_USER", "text", "postgres")}
        {field("密码", "DATABASE_PASSWORD", "password")}
        {field("JWT 密钥 (随机字符串)", "SECRET_KEY", "text", "请填写随机密钥")}

        {/* 错误提示 */}
        {error && (
          <div
            style={{
              background: "#3a1a1a",
              border: "1px solid #a33",
              borderRadius: 6,
              padding: "10px 14px",
              color: "#f88",
              fontSize: 13,
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            width: "100%",
            padding: "12px",
            background: saving ? "#444" : "linear-gradient(90deg, #6c6cff, #a060ff)",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            fontSize: 15,
            fontWeight: 600,
            cursor: saving ? "not-allowed" : "pointer",
            marginTop: 4,
          }}
        >
          {saving ? "正在连接后端..." : "保存并启动"}
        </button>
      </div>
    </div>
  );
}
