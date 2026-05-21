import React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

export default function ProtectedRoute({ roles = [] }) {
  const location = useLocation();
  const { isAuthenticated, isCheckingSession, user, logout } = useAuth();

  if (isCheckingSession) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (roles.length && !roles.includes(user?.role)) {
    // If arriving via email token link, log out and preserve destination
    const hasToken = new URLSearchParams(location.search).get("token");
    if (hasToken) {
      logout();
      return <Navigate to="/login" replace state={{ from: location }} />;
    }
    // Otherwise just redirect to their home
    const home =
      user?.role === "admin" ? "/admin" :
      user?.role === "manager" ? "/manager" :
      "/dashboard";
    return <Navigate to={home} replace />;
  }

  return <Outlet />;
}