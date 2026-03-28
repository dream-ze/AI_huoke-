import { PropsWithChildren, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { getSystemVersion } from "../lib/api";

type NavGroup = {
  title: string;
  items: { to: string; label: string; icon: string; badge?: string }[];
};

const navGroups: NavGroup[] = [
  {
    title: "工作台",
    items: [
      { to: "/dashboard", label: "首页看板", icon: "📊" },
      { to: "/workflow", label: "业务闭环", icon: "🔄", badge: "新" },
    ],
  },
  {
    title: "内容获取",
    items: [
      { to: "/collect-center", label: "采集中心", icon: "🎯" },
      { to: "/inbox", label: "收件箱", icon: "📥" },
      { to: "/materials", label: "素材库", icon: "📦" },
      { to: "/insight", label: "爆款洞察", icon: "🔥" },
    ],
  },
  {
    title: "AI 能力",
    items: [
      { to: "/ai-hub", label: "AI 中枢", icon: "🤖", badge: "新" },
      { to: "/ai-workbench", label: "改写工作台", icon: "✏️" },
      { to: "/compliance", label: "合规审核", icon: "🛡️" },
    ],
  },
  {
    title: "客户转化",
    items: [
      { to: "/publish", label: "发布任务", icon: "📤" },
      { to: "/leads", label: "线索池", icon: "💎" },
      { to: "/customers", label: "客户管理", icon: "👥" },
    ],
  },
  {
    title: "系统运维",
    items: [
      { to: "/ops", label: "运维看板", icon: "⚙️", badge: "新" },
    ],
  },
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
        <div className="brand-sub">AI 内容获客运营系统 · 能力升级版</div>

        <nav className="nav-grouped">
          {navGroups.map((group) => (
            <div key={group.title} className="nav-group">
              <div className="nav-group-title">{group.title}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `nav-link ${isActive ? "active" : ""}`
                  }
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                  {item.badge && <span className="nav-badge">{item.badge}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="muted" style={{ marginBottom: 8, fontSize: 11 }}>{versionText}</div>
          <button className="ghost" onClick={onLogout}>
            退出登录
          </button>
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
