import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const AUTH_STORAGE_KEY = "ledgerflow_auth";

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  withCredentials: true,
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

let isRefreshing = false;
let waitQueue = [];

const processQueue = (error, newToken = null) => {
  waitQueue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(newToken)
  );
  waitQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const requestUrl = original?.url || "";
    const isLoginAttempt = requestUrl.includes("/auth/login") || requestUrl.includes("/auth/register");
    const isRefreshAttempt = requestUrl.includes("/auth/refresh");

    if (error.response?.status !== 401) {
      return Promise.reject(error);
    }

    if (isLoginAttempt) {
      return Promise.reject(error);
    }

    if (isRefreshAttempt || original._retry) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        waitQueue.push({ resolve, reject });
      }).then((newToken) => {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      });
    }

    original._retry = true;
    isRefreshing = true;

    try {
      const { data } = await api.post("/auth/refresh");
      const newToken = data.access_token;

      const rawSession = localStorage.getItem(AUTH_STORAGE_KEY);
      if (rawSession) {
        const session = JSON.parse(rawSession);
        session.access_token = newToken;
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
      }

      processQueue(null, newToken);
      original.headers.Authorization = `Bearer ${newToken}`;
      return api(original);
    } catch (refreshError) {
      processQueue(refreshError, null);
      localStorage.removeItem(AUTH_STORAGE_KEY);
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export function websocketUrl(channel) {
  const url = new URL(API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/${channel}`;
  return url.toString();
}