import { PropsWithChildren, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { getSystemVersion } from "../lib/api";

const navItems = [
  { to: "/dashboard", label: "数据看板" },
  { to: "/collect-center", label: "采集中心" },
  { to: "/inbox", label: "收件箱" },
  { to: "/materials", label: "素材中心" },
  { to: "/insight", label: "爆款洞察" },
  { to: "/ai-workbench", label: "AI工作台" },
  { to: "/compliance", label: "合规审核" },
  { to: "/leads", label: "线索池" },
  { to: "/customers", label: "客户管理" },
  { to: "/publish", label: "发布任务" }
];

export function AppLayout({
  children,
  onLogout
}: PropsWithChildren<{ onLogout: () => void }>) {
  const [versionText, setVersionText] = useState("版本检测中...");

  useEffect(() => {
    async function loadVersion() {
      try {
        const data = await getSystemVersion();
        setVersionText(`API v${data.api_version} | Desktop latest ${data.latest_desktop_version}`);
      } catch {
        setVersionText("版本检查不可用");
      }
    }
    loadVersion();
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">智获客</div>
        <div className="brand-sub">AI 内容获客运营系统</div>

        <nav>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div style={{ marginTop: 20 }}>
          <div className="muted" style={{ marginBottom: 8 }}>{versionText}</div>
          <button className="ghost" onClick={onLogout}>
            退出登录
          </button>
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
