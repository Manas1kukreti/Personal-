import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import AppShell from "./shell/AppShell.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import UploadCenter from "./pages/UploadCenter.jsx";
import ManagerDashboard from "./pages/ManagerDashboard.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/uploads" element={<UploadCenter />} />
            </Route>
          </Route>
          <Route element={<ProtectedRoute roles={["manager", "admin"]} />}>
            <Route element={<AppShell />}>
              <Route path="/manager" element={<ManagerDashboard />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
