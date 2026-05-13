import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { FiActivity, FiBarChart2, FiBell, FiCheckSquare, FiDatabase, FiLogOut, FiUploadCloud, FiUsers } from "react-icons/fi";
import { useAuth } from "../auth/AuthContext.jsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: FiBarChart2 },
  { to: "/uploads", label: "Uploads", icon: FiUploadCloud },
  { to: "/manager", label: "Approvals", icon: FiCheckSquare, roles: ["manager", "admin"] }
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const visibleNavItems = navItems.filter((item) => !item.roles || item.roles.includes(user?.role));

  return (
    <div className="min-h-screen bg-mist text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-line bg-white lg:flex lg:flex-col">
        <div className="border-b border-line px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center bg-brand text-white" style={{ borderRadius: 8 }}>
              <FiDatabase />
            </div>
            <div>
              <div className="text-sm font-bold text-ink">ExcelFlow</div>
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
              <div className="truncate text-sm font-bold text-ink">{user?.name || "ExcelFlow User"}</div>
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
              <span>ExcelFlow</span>
              <span className="text-slate-300">/</span>
              <span className="truncate font-semibold text-ink">Enterprise data approval workspace</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="chip hidden sm:inline-flex">
                <span className="status-dot pulse-soft bg-success" />
                WS Live
              </div>
              <button className="icon-button" title="Notifications">
                <FiBell />
              </button>
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
