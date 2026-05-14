import React from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { AUTH_STORAGE_KEY, api } from "../api/client.js";

const AuthContext = createContext(null);

function readStoredSession() {
  const rawSession = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!rawSession) return null;
  try {
    return JSON.parse(rawSession);
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readStoredSession);
  const [isCheckingSession, setIsCheckingSession] = useState(Boolean(session?.access_token));

  function saveSession(nextSession) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
  }

  async function login(payload) {
    const response = await api.post("/auth/login", payload);
    saveSession(response.data);
    return response.data;
  }

  async function register(payload) {
    const response = await api.post("/auth/register", payload);
    saveSession(response.data);
    return response.data;
  }

  function logout() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setSession(null);
  }

  useEffect(() => {
    let isMounted = true;

    async function validateStoredSession() {
      if (!session?.access_token) {
        setIsCheckingSession(false);
        return;
      }

      setIsCheckingSession(true);
      try {
        const response = await api.get("/auth/me");
        if (isMounted) {
          setSession((currentSession) => ({
            ...currentSession,
            user: response.data
          }));
        }
      } catch {
        localStorage.removeItem(AUTH_STORAGE_KEY);
        if (isMounted) setSession(null);
      } finally {
        if (isMounted) setIsCheckingSession(false);
      }
    }

    validateStoredSession();

    return () => {
      isMounted = false;
    };
  }, [session?.access_token]);

  const value = useMemo(
    () => ({
      accessToken: session?.access_token || "",
      user: session?.user || null,
      isAuthenticated: Boolean(session?.access_token && session?.user),
      isCheckingSession,
      login,
      register,
      logout
    }),
    [isCheckingSession, session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
