import React, { Suspense, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "./store";
import { saveRedirectPath } from "./lib/auth";
import { AppLayout } from "./components/AppLayout";

// 懒加载页面组件
const LoginPage = React.lazy(() => import("./pages/LoginPage").then(m => ({ default: m.LoginPage })));
const DashboardPage = React.lazy(() => import("./pages/dashboard/DashboardPage").then(m => ({ default: m.DashboardPage })));
const CollectCenterPage = React.lazy(() => import("./pages/collect-center/CollectCenterPage").then(m => ({ default: m.CollectCenterPage })));
const AIHubPage = React.lazy(() => import("./pages/ai-hub/AIHubPage").then(m => ({ default: m.AIHubPage })));
const KnowledgePage = React.lazy(() => import("./pages/knowledge/KnowledgePage"));
const CustomersPage = React.lazy(() => import("./pages/CustomersPage").then(m => ({ default: m.CustomersPage })));
const LeadsPage = React.lazy(() => import("./pages/leads/LeadsPage").then(m => ({ default: m.LeadsPage })));
const ConversationsPage = React.lazy(() => import("./pages/conversations/ConversationsPage"));
const SocialAccountsPage = React.lazy(() => import("./pages/social-accounts/SocialAccountsPage").then(m => ({ default: m.SocialAccountsPage })));
const SetupPage = React.lazy(() => import("./pages/SetupPage").then(m => ({ default: m.SetupPage })));

// MVP 页面（核心）
const MvpInboxPage = React.lazy(() => import("./pages/inbox/MvpInboxPage"));
const MvpMaterialsPage = React.lazy(() => import("./pages/materials/MvpMaterialsPage"));
const MvpWorkbenchPage = React.lazy(() => import("./pages/ai-workbench/MvpWorkbenchPage"));
const ComplianceRulesPage = React.lazy(() => import("./pages/compliance/ComplianceRulesPage"));
const RemindersPage = React.lazy(() => import("./pages/reminders/RemindersPage"));
const TrafficStrategyPage = React.lazy(() => import("./pages/traffic/TrafficStrategyPage").then(m => ({ default: m.TrafficStrategyPage })));
const TopicPlanningPage = React.lazy(() => import("./pages/topic/TopicPlanningPage"));

// 旧版页面（暂时保留import，路由已注释）
// const InboxPage = React.lazy(() => import("./pages/inbox/InboxPage").then(m => ({ default: m.InboxPage })));
// const MaterialsPage = React.lazy(() => import("./pages/materials/MaterialsPage").then(m => ({ default: m.MaterialsPage })));
// const AIWorkbenchPage = React.lazy(() => import("./pages/ai-workbench/AIWorkbenchPage").then(m => ({ default: m.AIWorkbenchPage })));
// const PublishPage = React.lazy(() => import("./pages/PublishPage").then(m => ({ default: m.PublishPage })));
// const InsightPage = React.lazy(() => import("./pages/InsightPage").then(m => ({ default: m.InsightPage })));
// const OpsPage = React.lazy(() => import("./pages/OpsPage").then(m => ({ default: m.OpsPage })));
// const WorkflowPage = React.lazy(() => import("./pages/WorkflowPage").then(m => ({ default: m.WorkflowPage })));
// const MvpKnowledgePage = React.lazy(() => import("./pages/knowledge/MvpKnowledgePage"));

// 是否运行在 Electron 中
const isElectron = typeof window !== "undefined" && !!(window as any).desktop?.isElectron;

type AppState = "loading" | "setup" | "ready";

function applyRuntimeApiBaseUrl(port?: string) {
  if (typeof window === "undefined") return;
  const validPort = Number(port || "8000");
  const targetPort = Number.isFinite(validPort) && validPort > 0 ? validPort : 8000;
  localStorage.setItem("zhk_api_base_url", `http://127.0.0.1:${targetPort}`);
}

function Protected({ children }: { children: JSX.Element }) {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  if (!isAuthenticated) {
    const redirect = `${location.pathname}${location.search}${location.hash}`;
    saveRedirectPath(redirect);
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return children;
}

// 启动加载屏
function LoadingScreen({ message }: { message: string }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        color: "#fff",
        gap: 20,
      }}
    >
      <div style={{ fontSize: 48, animation: "spin 1.5s linear infinite" }}>⚙️</div>
      <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>智获客</h2>
      <p style={{ margin: 0, color: "#888", fontSize: 14 }}>{message}</p>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default function App() {
  const navigate = useNavigate();
  const [appState, setAppState] = useState<AppState>(isElectron ? "loading" : "ready");
  const [initConfig, setInitConfig] = useState<any>(null);

  useEffect(() => {
    if (!isElectron) return;

    async function initApp() {
      const desktop = (window as any).desktop;
      // 读取已保存的配置
      const cfg = await desktop.getDbConfig().catch(() => null);
      setInitConfig(cfg);
      applyRuntimeApiBaseUrl(cfg?.BACKEND_PORT);

      // 检查后端是否已就绪
      const { running } = await desktop.checkBackend().catch(() => ({ running: false }));
      if (running) {
        setAppState("ready");
      } else {
        // 后端未就绪 → 进入配置页
        setAppState("setup");
      }
    }

    initApp();
  }, []);

  useEffect(() => {
    const onLogout = () => {
      navigate("/login", { replace: true });
    };

    window.addEventListener("zhk-auth-logout", onLogout as EventListener);
    return () => window.removeEventListener("zhk-auth-logout", onLogout as EventListener);
  }, [navigate]);

  // 开发模式或非 Electron：直接跳入主 app
  if (appState === "loading") {
    return <LoadingScreen message="正在启动后端服务，请稍候..." />;
  }

  if (appState === "setup") {
    return (
      <SetupPage
        initialConfig={initConfig}
        onSaved={(cfg) => {
          applyRuntimeApiBaseUrl(cfg?.BACKEND_PORT);
          setAppState("ready");
        }}
      />
    );
  }

  return (
    <Suspense fallback={
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#8B7355' }}>
        加载中...
      </div>
    }>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <Protected>
              <AppLayout
                onLogout={() => {
                  useAuthStore.getState().logout();
                  navigate("/login");
                }}
              >
                <Routes>
                  {/* 默认重定向到 AI中枢 */}
                  <Route path="/" element={<Navigate to="/ai-hub" replace />} />
                  
                  {/* === 内容生产 === */}
                  <Route path="/ai-hub" element={<AIHubPage />} />
                  <Route path="/collect-center" element={<CollectCenterPage />} />
                  <Route path="/mvp-workbench" element={<MvpWorkbenchPage />} />
                  <Route path="/knowledge" element={<KnowledgePage />} />
                  
                  {/* === 选题规划 === */}
                  <Route path="/topic" element={<TopicPlanningPage />} />
                  
                  {/* === 内容管理 === */}
                  <Route path="/mvp-inbox" element={<MvpInboxPage />} />
                  <Route path="/mvp-materials" element={<MvpMaterialsPage />} />
                  
                  {/* === 合规管理 === */}
                  <Route path="/compliance-rules" element={<ComplianceRulesPage />} />
                  
                  {/* === 业务管理 === */}
                  <Route path="/leads" element={<LeadsPage />} />
                  <Route path="/conversations" element={<ConversationsPage />} />
                  <Route path="/customers" element={<CustomersPage />} />
                  <Route path="/social-accounts" element={<SocialAccountsPage />} />
                  <Route path="/reminders" element={<RemindersPage />} />
                  <Route path="/traffic-strategies" element={<TrafficStrategyPage />} />
                  
                  {/* === 管理层 === */}
                  <Route path="/dashboard" element={<DashboardPage />} />
                  
                  {/* === 旧版路由（已注释） === */}
                  {/* <Route path="/inbox" element={<InboxPage />} /> */}
                  {/* <Route path="/materials" element={<MaterialsPage />} /> */}
                  {/* <Route path="/ai-workbench" element={<AIWorkbenchPage />} /> */}
                  {/* <Route path="/mvp-knowledge" element={<MvpKnowledgePage />} /> */}
                  {/* <Route path="/publish" element={<PublishPage />} /> */}
                  {/* <Route path="/insight" element={<InsightPage />} /> */}
                  {/* <Route path="/workflow" element={<WorkflowPage />} /> */}
                  {/* <Route path="/ops" element={<OpsPage />} /> */}
                </Routes>
              </AppLayout>
            </Protected>
          }
        />
      </Routes>
    </Suspense>
  );
}

