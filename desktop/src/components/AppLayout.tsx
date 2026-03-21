import { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/dashboard", label: "数据看板" },
  { to: "/content", label: "内容采集" },
  { to: "/ai", label: "AI改写" },
  { to: "/compliance", label: "合规审核" },
  { to: "/customers", label: "客户管理" },
  { to: "/publish", label: "发布记录" }
];

export function AppLayout({
  children,
  onLogout
}: PropsWithChildren<{ onLogout: () => void }>) {
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
          <button className="ghost" onClick={onLogout}>
            退出登录
          </button>
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
