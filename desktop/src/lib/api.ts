import axios from "axios";
import { clearToken, getToken } from "./auth";

// When served by the backend on the same origin, baseURL can be empty.
// During local dev (Vite on 5173), set VITE_API_BASE_URL=http://localhost:8000
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 20000
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearToken();
    }
    return Promise.reject(error);
  }
);

export async function login(username: string, password: string) {
  const { data } = await api.post("/api/auth/login", { username, password });
  return data;
}

export async function getDashboardSummary() {
  const { data } = await api.get("/api/dashboard/summary");
  return data;
}

export async function getTrend(days = 7) {
  const { data } = await api.get(`/api/dashboard/trend?days=${days}`);
  return data;
}

export async function getAICallStats(days = 7, scope: "me" | "all" = "me") {
  const { data } = await api.get(`/api/dashboard/ai-call-stats?days=${days}&scope=${scope}`);
  return data;
}

export async function listContent() {
  const { data } = await api.get("/api/content/list");
  return data;
}

export async function createContent(payload: {
  platform: string;
  content_type: string;
  title: string;
  content: string;
  tags: string[];
}) {
  const { data } = await api.post("/api/content/create", payload);
  return data;
}

export async function rewriteContent(payload: {
  content_id: number;
  target_platform: "xiaohongshu" | "douyin" | "zhihu";
}) {
  const endpointMap = {
    xiaohongshu: "/api/ai/rewrite/xiaohongshu",
    douyin: "/api/ai/rewrite/douyin",
    zhihu: "/api/ai/rewrite/zhihu"
  };
  const { data } = await api.post(endpointMap[payload.target_platform], {
    content_id: payload.content_id,
    target_platform: payload.target_platform,
    content_type: "post"
  });
  return data;
}

export async function analyzeArkVision(payload: {
  image_url: string;
  text: string;
  model?: string;
}) {
  const { data } = await api.post("/api/ai/ark/vision", payload);
  return data;
}

export async function checkCompliance(content: string) {
  const { data } = await api.post("/api/compliance/check", { content, content_type: "post" });
  return data;
}

export async function listCustomers() {
  const { data } = await api.get("/api/customer/list");
  return data;
}

export async function createCustomer(payload: {
  nickname: string;
  wechat_id?: string;
  source_platform: string;
  tags: string[];
  intention_level: string;
  inquiry_content?: string;
}) {
  const { data } = await api.post("/api/customer/create", payload);
  return data;
}

export async function listPublishRecords() {
  const { data } = await api.get("/api/publish/list");
  return data;
}

export async function createPublishRecord(payload: {
  rewritten_content_id: number;
  platform: string;
  account_name: string;
}) {
  const { data } = await api.post("/api/publish/create", payload);
  return data;
}
