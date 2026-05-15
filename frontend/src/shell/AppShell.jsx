import React from "react";
import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { FiActivity, FiBarChart2, FiBell, FiCheckSquare, FiChevronRight, FiDatabase, FiLogOut, FiUploadCloud, FiUserCheck, FiUsers } from "react-icons/fi";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: FiBarChart2 },
  { to: "/uploads", label: "Uploads", icon: FiUploadCloud },
  { to: "/manager", label: "Approvals", icon: FiCheckSquare, roles: ["manager"] },
  { to: "/admin", label: "Admin", icon: FiUserCheck, roles: ["admin"] }
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const [pendingActions, setPendingActions] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const navigate = useNavigate();
  const visibleNavItems = navItems.filter((item) => !item.roles || item.roles.includes(user?.role));

  const loadPendingActions = useCallback(async () => {
    if (!user) {
      setPendingActions(0);
      setNotifications([]);
      return;
    }

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
    if (user?.role === "manager") {
      navigate(`/manager?submission_id=${upload.id}`);
      return;
    }
    if (user?.role === "admin") {
      navigate("/admin");
      return;
    }
    navigate("/uploads");
  }

  return (
    <div className="min-h-screen bg-mist text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-line bg-white lg:flex lg:flex-col">
        <div className="border-b border-line px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center bg-brand text-white" style={{ borderRadius: 8 }}>
              <FiDatabase />
            </div>
            <div>
              <div className="text-sm font-bold text-ink">LedgerFlow</div>
              <div className="text-xs text-muted">Analytics Platform</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          <div className="px-3 pb-2 text-[11px] font-bold uppercase tracking-widest text-slate-400">Navigation</div>
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 border-l-2 px-3 py-2.5 text-sm font-semibold transition ${
                    isActive
                      ? "border-brand bg-teal-50 text-brand"
                      : "border-transparent text-muted hover:bg-slate-50 hover:text-ink"
                  }`
                }
                style={{ borderRadius: 8 }}
              >
                <Icon />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="border-t border-line p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-muted">
              <FiUsers />
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-bold text-ink">{user?.name || "LedgerFlow User"}</div>
              <div className="text-xs capitalize text-muted">{user?.role || "user"}</div>
            </div>
          </div>
        </div>
      </aside>
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 border-b border-line bg-white/95 px-5 py-3 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2 text-sm text-muted">
              <FiActivity className="shrink-0" />
              <span>LedgerFlow</span>
              <span className="text-slate-300">/</span>
              <span className="truncate font-semibold text-ink">Enterprise data approval workspace</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="chip hidden sm:inline-flex">
                <span className="status-dot pulse-soft bg-success" />
                WS Live
              </div>
              <div className="relative">
                <button
                  className="icon-button relative"
                  title="Notifications"
                  onClick={async () => {
                    await loadPendingActions();
                    setShowNotifications((value) => !value);
                  }}
                >
                  <FiBell />
                  {pendingActions > 0 && (
                    <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">
                      {pendingActions}
                    </span>
                  )}
                </button>
                {showNotifications && (
                  <div className="absolute right-0 top-12 z-30 w-80 overflow-hidden border border-line bg-white shadow-panel" style={{ borderRadius: 8 }}>
                    <div className="flex items-center justify-between border-b border-line px-4 py-3">
                      <div>
                        <div className="text-sm font-bold text-ink">Notifications</div>
                        <div className="text-xs text-muted">
                          {user?.role === "employee" ? "Recent upload status" : "Pending actions"}
                        </div>
                      </div>
                      {pendingActions > 0 && <span className="status-badge status-pending">{pendingActions}</span>}
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                      {notifications.map((upload) => (
                        <button
                          key={upload.id}
                          className="flex w-full items-center justify-between gap-3 border-b border-line px-4 py-3 text-left transition hover:bg-slate-50"
                          onClick={() => openNotification(upload)}
                        >
                          <div className="min-w-0">
                            <div className="mono truncate text-xs font-bold text-accent">{upload.filename}</div>
                            <div className="mt-1 flex items-center gap-2 text-xs text-muted">
                              <span className={`status-badge status-${upload.status}`}>{upload.status}</span>
                              <span>{upload.total_rows} rows</span>
                            </div>
                          </div>
                          <FiChevronRight className="shrink-0 text-slate-300" />
                        </button>
                      ))}
                      {!notifications.length && (
                        <div className="px-4 py-8 text-center text-sm text-muted">
                          No notifications right now
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
              {visibleNavItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink key={item.to} to={item.to} className="icon-button lg:hidden" title={item.label}>
                    <Icon />
                  </NavLink>
                );
              })}
              <button className="icon-button" onClick={logout} title="Sign out">
                <FiLogOut />
              </button>
            </div>
          </div>
        </header>
        <main className="p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
