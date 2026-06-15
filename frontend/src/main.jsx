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
import AuditPage from "./pages/AuditPage.jsx";
import AlertsPage from "./pages/AlertsPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import "./styles.css";
import LandingPage from "./pages/LandingPage.jsx";
// Auto-scaling script to set viewport scale ratio based on 1536px target width
const handleResize = () => {
  const width = window.innerWidth;
  if (width > 1024) {
    const scale = width / 1536; // Target base width of 1536px
    const cappedScale = Math.min(1.3, Math.max(0.7, scale));
    document.documentElement.style.setProperty("--app-scale", cappedScale);
  } else {
    document.documentElement.style.setProperty("--app-scale", 1);
  }
};
window.addEventListener("resize", handleResize);
handleResize();

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<AuthPage />} />
          <Route element={<ProtectedRoute roles={["employee", "manager", "admin"]} />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/uploads" element={<UploadCenter />} />
              <Route path="/submissions" element={<SubmissionsPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
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
              <Route path="/audit" element={<AuditPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
