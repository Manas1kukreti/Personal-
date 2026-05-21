import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import AppShell from "./shell/AppShell.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import UploadCenter from "./pages/UploadCenter.jsx";
import SubmissionsPage from "./pages/SubmissionsPage.jsx";
import ManagerDashboard from "./pages/ManagerDashboard.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import "./styles.css";

function HomeRedirect() {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const from = location.state?.from?.pathname;
  if (from && from !== "/") return <Navigate to={from} replace />;
  const home =
    user?.role === "admin" ? "/admin" :
    user?.role === "manager" ? "/manager" :
    "/dashboard";

  return <Navigate to={home} replace />;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/login" element={<AuthPage />} />
          <Route element={<ProtectedRoute roles={["employee", "manager", "admin"]} />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/uploads" element={<UploadCenter />} />
              <Route path="/submissions" element={<SubmissionsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route element={<ProtectedRoute roles={["manager"]} />}>
            <Route element={<AppShell />}>
              <Route path="/manager" element={<ManagerDashboard />} />
            </Route>
          </Route>
          <Route element={<ProtectedRoute roles={["admin"]} />}>
            <Route element={<AppShell />}>
              <Route path="/admin" element={<AdminDashboard />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
