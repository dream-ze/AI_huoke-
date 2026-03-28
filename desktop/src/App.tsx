import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import {
  clearToken,
  getLogoutEventName,
  isLoggedIn,
  saveRedirectPath,
} from "./lib/auth";
import { AppLayout } from "./components/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { CollectCenterPage } from "./pages/collect-center/CollectCenterPage";
import { InboxPage } from "./pages/inbox/InboxPage";
import { MaterialsPage } from "./pages/materials/MaterialsPage";
import { AIWorkbenchPage } from "./pages/ai-workbench/AIWorkbenchPage";
import { AIHubPage } from "./pages/ai-hub/AIHubPage";
import { CompliancePage } from "./pages/CompliancePage";
import { CustomersPage } from "./pages/CustomersPage";
import { PublishPage } from "./pages/PublishPage";
import { LeadsPage } from "./pages/leads/LeadsPage";
import { SetupPage } from "./pages/SetupPage";
import { InsightPage } from "./pages/InsightPage";
import { OpsPage } from "./pages/OpsPage";
import { WorkflowPage } from "./pages/WorkflowPage";

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
  if (!isLoggedIn()) {
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
    const eventName = getLogoutEventName();
    const onLogout = () => {
      navigate("/login", { replace: true });
    };

    window.addEventListener(eventName, onLogout as EventListener);
    return () => window.removeEventListener(eventName, onLogout as EventListener);
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
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <Protected>
            <AppLayout
              onLogout={() => {
                clearToken("manual");
                navigate("/login");
              }}
            >
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/workflow" element={<WorkflowPage />} />
                <Route path="/collect-center" element={<CollectCenterPage />} />
                <Route path="/inbox" element={<InboxPage />} />
                <Route path="/materials" element={<MaterialsPage />} />
                <Route path="/insight" element={<InsightPage />} />
                <Route path="/ai-hub" element={<AIHubPage />} />
                <Route path="/ai-workbench" element={<AIWorkbenchPage />} />
                <Route path="/compliance" element={<CompliancePage />} />
                <Route path="/leads" element={<LeadsPage />} />
                <Route path="/customers" element={<CustomersPage />} />
                <Route path="/publish" element={<PublishPage />} />
                <Route path="/ops" element={<OpsPage />} />
              </Routes>
            </AppLayout>
          </Protected>
        }
      />
    </Routes>
  );
}

