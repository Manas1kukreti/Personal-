import React from "react";
import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { FiActivity, FiArchive, FiBell, FiCheckSquare, FiChevronLeft, FiChevronRight, FiDatabase, FiLogOut, FiSettings, FiTrendingUp, FiUploadCloud, FiUserCheck, FiUsers } from "react-icons/fi";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const navItems = [
  { to: "/dashboard", label: "Analytics", icon: FiTrendingUp },
  { to: "/uploads", label: "Upload Center", icon: FiUploadCloud },
  { to: "/submissions", label: "Submissions", icon: FiArchive },
  { to: "/manager", label: "Approvals", icon: FiCheckSquare, roles: ["manager"] },
  { to: "/admin", label: "Admin", icon: FiUserCheck, roles: ["admin"] },
  { to: "/settings", label: "Settings", icon: FiSettings }
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [pendingActions, setPendingActions] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const visibleNavItems = navItems.filter((item) => !item.roles || item.roles.includes(user?.role));
  const currentNav = visibleNavItems.find((item) => location.pathname === item.to) || visibleNavItems.find((item) => location.pathname.startsWith(item.to));
  const initials = (user?.name || "LF").split(" ").map((word) => word[0]).join("").toUpperCase().slice(0, 2);
  const sidebarWidth = collapsed ? 64 : 240;

  const loadPendingActions = useCallback(async () => {
    if (!user) { setPendingActions(0); setNotifications([]); return; }
    const endpoint = ["manager", "admin"].includes(user.role) ? "/uploads?status=pending" : "/uploads";
    const response = await api.get(endpoint);
    const items = response.data.slice(0, 5);
    setNotifications(items);
    setPendingActions(user.role === "employee" ? items.filter((item) => item.status === "pending").length : response.data.length);
  }, [user]);

  useEffect(() => {
    loadPendingActions().catch(() => setPendingActions(0));
  }, [loadPendingActions]);

  function openNotification(upload) {
    setShowNotifications(false);
    if (user?.role === "manager") { navigate(`/manager?submission_id=${upload.id}`); return; }
    if (user?.role === "admin") { navigate("/admin"); return; }
    navigate("/uploads");
  }

  return (
    <div className="min-h-screen bg-mist text-ink" style={{ display: "flex" }}>

      {/* SIDEBAR */}
      <aside style={{
        width: sidebarWidth,
        minWidth: sidebarWidth,
        transition: "width 0.22s ease, min-width 0.22s ease",
        position: "fixed",
        top: 0,
        left: 0,
        bottom: 0,
        zIndex: 30,
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid var(--color-line, #e5e9e6)",
        background: "rgba(255,255,255,0.95)",
        backdropFilter: "blur(16px)",
        overflow: "hidden"
      }}>

        {/* Logo */}
        <div style={{
          borderBottom: "1px solid var(--color-line, #e5e9e6)",
          padding: collapsed ? "18px 0" : "18px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "flex-start",
          gap: 12,
          transition: "padding 0.22s ease"
        }}>
          <div style={{
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 36,
            height: 36,
            borderRadius: 10,
            background: "#0d6e56",
            color: "#fff"
          }}>
            <FiDatabase size={18} />
          </div>
          {!collapsed && (
            <div style={{ overflow: "hidden" }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#0a3d2e", whiteSpace: "nowrap" }}>LedgerFlow</div>
              <div style={{ fontSize: 11, color: "#6b9080", whiteSpace: "nowrap" }}>Analytics Platform</div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: collapsed ? "16px 8px" : "16px 12px", display: "flex", flexDirection: "column", gap: 2, overflowY: "auto", transition: "padding 0.22s ease" }}>
          {!collapsed && (
            <div style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: "#8ab8aa", padding: "0 8px", marginBottom: 6 }}>
              Workspace
            </div>
          )}
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.to || location.pathname.startsWith(item.to + "/");
            return (
              <div
                key={item.to}
                className={collapsed ? "sidebar-tooltip-item" : ""}
                data-tooltip={item.label}
                style={{ position: "relative" }}
              >
                <NavLink
                  to={item.to}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: collapsed ? 0 : 10,
                    justifyContent: collapsed ? "center" : "flex-start",
                    padding: collapsed ? "10px" : "9px 12px",
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: 600,
                    textDecoration: "none",
                    transition: "all 0.15s ease",
                    borderLeft: collapsed ? "none" : `2px solid ${isActive ? "#0d6e56" : "transparent"}`,
                    background: isActive ? "#e8f5f0" : "transparent",
                    color: isActive ? "#0d6e56" : "#6b9080",
                  }}
                  onMouseEnter={(e) => { if (!isActive) { e.currentTarget.style.background = "#f4f7f6"; e.currentTarget.style.color = "#0a3d2e"; }}}
                  onMouseLeave={(e) => { if (!isActive) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#6b9080"; }}}
                >
                  <Icon size={16} style={{ flexShrink: 0 }} />
                  {!collapsed && <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.label}</span>}
                </NavLink>
              </div>
            );
          })}
        </nav>

        {/* User + collapse toggle */}
        <div style={{ borderTop: "1px solid var(--color-line, #e5e9e6)", padding: collapsed ? "12px 8px" : "12px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
          {!collapsed && (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ flexShrink: 0, width: 32, height: 32, borderRadius: "50%", background: "#e8f5f0", color: "#0d6e56", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700 }}>
                {initials}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#0a3d2e", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{user?.name || "User"}</div>
                <div style={{ fontSize: 11, color: "#6b9080", textTransform: "capitalize" }}>{user?.role}</div>
              </div>
            </div>
          )}

          {/* Collapse toggle button */}
          <button
            onClick={() => setCollapsed((c) => !c)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: collapsed ? "center" : "flex-start",
              gap: 8,
              width: "100%",
              padding: collapsed ? "8px" : "7px 10px",
              borderRadius: 8,
              border: "1px solid #c4ddd6",
              background: "transparent",
              color: "#6b9080",
              fontSize: 12,
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.15s ease"
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "#f4f7f6"; e.currentTarget.style.color = "#0a3d2e"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#6b9080"; }}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <FiChevronRight size={15} /> : <><FiChevronLeft size={15} /><span>Collapse</span></>}
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <div style={{ flex: 1, marginLeft: sidebarWidth, transition: "margin-left 0.22s ease", minWidth: 0 }}>

        {/* TOPBAR */}
        <header style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          borderBottom: "1px solid var(--color-line, #e5e9e6)",
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(16px)",
          padding: "10px 20px"
        }}>
          <div className="app-topbar-inner" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#6b9080", minWidth: 0 }}>
              <FiActivity style={{ flexShrink: 0 }} />
              <span style={{ whiteSpace: "nowrap" }}>LedgerFlow</span>
              <span style={{ color: "#c4ddd6" }}>/</span>
              <span style={{ fontWeight: 600, color: "#0a3d2e", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                Enterprise data approval workspace
              </span>
            </div>
            <div className="app-topbar-actions" style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", borderRadius: 20, border: "1px solid #c4ddd6", fontSize: 12, color: "#6b9080" }}>
                <span>Workspace</span>
                <FiChevronRight size={12} />
                <strong style={{ color: "#0a3d2e" }}>{currentNav?.label || "Dashboard"}</strong>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 20, background: "#e8f5f0", fontSize: 12, color: "#0d6e56", fontWeight: 500 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#0d6e56", display: "inline-block" }} />
                WS Live
              </div>

              {/* Notifications */}
              <div style={{ position: "relative" }}>
                <button
                  style={{ position: "relative", padding: 8, borderRadius: 8, border: "1px solid #c4ddd6", background: "transparent", cursor: "pointer", display: "flex", alignItems: "center", color: "#6b9080" }}
                  onClick={async () => { await loadPendingActions(); setShowNotifications((v) => !v); }}
                >
                  <FiBell size={16} />
                  {pendingActions > 0 && (
                    <span style={{ position: "absolute", top: -4, right: -4, minWidth: 18, height: 18, borderRadius: 9, background: "#a32d2d", color: "#fff", fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", padding: "0 4px" }}>
                      {pendingActions}
                    </span>
                  )}
                </button>
                {showNotifications && (
                  <div style={{ position: "absolute", right: 0, top: 44, zIndex: 30, width: 300, background: "#fff", border: "1px solid #c4ddd6", borderRadius: 10, boxShadow: "0 8px 24px rgba(0,0,0,0.1)", overflow: "hidden" }}>
                    <div style={{ padding: "12px 16px", borderBottom: "1px solid #eef4f2", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "#0a3d2e" }}>Notifications</div>
                        <div style={{ fontSize: 11, color: "#6b9080" }}>{user?.role === "employee" ? "Recent upload status" : "Pending actions"}</div>
                      </div>
                    </div>
                    <div style={{ maxHeight: 320, overflowY: "auto" }}>
                      {notifications.map((upload) => (
                        <button key={upload.id} onClick={() => openNotification(upload)}
                          style={{ width: "100%", textAlign: "left", padding: "10px 16px", borderBottom: "1px solid #eef4f2", background: "transparent", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "#f4f7f6"}
                          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                        >
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: "#1E8278", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{upload.filename}</div>
                            <div style={{ fontSize: 11, color: "#6b9080", marginTop: 2 }}>{upload.total_rows} rows · {upload.status}</div>
                          </div>
                          <FiChevronRight size={14} style={{ flexShrink: 0, color: "#c4ddd6" }} />
                        </button>
                      ))}
                      {!notifications.length && <div style={{ padding: "24px 16px", textAlign: "center", fontSize: 13, color: "#6b9080" }}>No notifications right now</div>}
                    </div>
                  </div>
                )}
              </div>

              {/* User badge */}
              <NavLink to="/settings" style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 12px", borderRadius: 20, border: "1px solid #c4ddd6", textDecoration: "none", background: "transparent" }}>
                <div style={{ width: 26, height: 26, borderRadius: "50%", background: "#e8f5f0", color: "#0d6e56", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, flexShrink: 0 }}>
                  {initials}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#0a3d2e", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 100 }}>{user?.name}</div>
                  <div style={{ fontSize: 10, color: "#6b9080", textTransform: "capitalize" }}>{user?.role}</div>
                </div>
              </NavLink>

              <button onClick={logout} title="Sign out"
                style={{ padding: 8, borderRadius: 8, border: "1px solid #c4ddd6", background: "transparent", cursor: "pointer", display: "flex", alignItems: "center", color: "#6b9080" }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "#fcebeb"; e.currentTarget.style.color = "#a32d2d"; e.currentTarget.style.borderColor = "#a32d2d"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#6b9080"; e.currentTarget.style.borderColor = "#c4ddd6"; }}
              >
                <FiLogOut size={16} />
              </button>
            </div>
          </div>
        </header>

        <main className="app-shell-main" style={{ padding: "24px" }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
