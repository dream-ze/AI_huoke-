import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { clearToken, isLoggedIn } from "./lib/auth";
import { AppLayout } from "./components/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ContentPage } from "./pages/ContentPage";
import { AIPage } from "./pages/AIPage";
import { CompliancePage } from "./pages/CompliancePage";
import { CustomersPage } from "./pages/CustomersPage";
import { PublishPage } from "./pages/PublishPage";
import { SetupPage } from "./pages/SetupPage";
import { InsightPage } from "./pages/InsightPage";

// 是否运行在 Electron 中
const isElectron = typeof window !== "undefined" && !!(window as any).desktop?.isElectron;

type AppState = "loading" | "setup" | "ready";

function Protected({ children }: { children: JSX.Element }) {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
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

  // 开发模式或非 Electron：直接跳入主 app
  if (appState === "loading") {
    return <LoadingScreen message="正在启动后端服务，请稍候..." />;
  }

  if (appState === "setup") {
    return (
      <SetupPage
        initialConfig={initConfig}
        onSaved={() => setAppState("ready")}
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
                clearToken();
                navigate("/login");
              }}
            >
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/content" element={<ContentPage />} />
                <Route path="/insight" element={<InsightPage />} />
                <Route path="/ai" element={<AIPage />} />
                <Route path="/compliance" element={<CompliancePage />} />
                <Route path="/customers" element={<CustomersPage />} />
                <Route path="/publish" element={<PublishPage />} />
              </Routes>
            </AppLayout>
          </Protected>
        }
      />
    </Routes>
  );
}

