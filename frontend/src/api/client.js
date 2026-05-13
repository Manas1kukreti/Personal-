import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const AUTH_STORAGE_KEY = "excelflow_auth";

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api`
});

api.interceptors.request.use((config) => {
  const rawSession = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!rawSession) return config;

  try {
    const session = JSON.parse(rawSession);
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  return config;
});

export function websocketUrl(channel) {
  const url = new URL(API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/${channel}`;
  return url.toString();
}
