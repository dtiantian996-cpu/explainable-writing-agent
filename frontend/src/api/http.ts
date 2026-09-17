import axios from "axios";

function extractResponseMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const candidate = payload as Record<string, unknown>;
  const possibleKeys = ["errorMessage", "detail", "message"];
  for (const key of possibleKeys) {
    const value = candidate[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

export function normalizeHttpError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNABORTED") {
      return "请求超时，请稍后重试。";
    }
    if (error.code === "ERR_NETWORK" || !error.response) {
      if (typeof navigator !== "undefined" && navigator.onLine === false) {
        return "网络连接已断开，请恢复网络后重试。";
      }
      return "网络连接不可用，请稍后重试。";
    }
    if (error.response.status === 401) {
      return extractResponseMessage(error.response.data) ?? "登录状态已失效，请重新登录。";
    }
    const responseMessage = extractResponseMessage(error.response.data);
    if (responseMessage) {
      return responseMessage;
    }
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  timeout: 120000,
  withCredentials: true
});
