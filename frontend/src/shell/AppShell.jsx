import React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  FiActivity,
  FiAlertTriangle,
  FiArchive,
  FiBell,
  FiCheckSquare,
  FiChevronLeft,
  FiChevronRight,
  FiCommand,
  FiLogOut,
  FiSearch,
  FiSettings,
  FiTrendingUp,
  FiUploadCloud,
  FiUserCheck,
  FiX,
} from "react-icons/fi";
import { createPortal } from "react-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";
import logo from "../asset/logo.png";

const navItems = [
  { to: "/dashboard", label: "Analytics", icon: FiTrendingUp, keywords: ["overview", "kpi", "transactions"] },
  { to: "/submissions", label: "Submissions", icon: FiArchive, keywords: ["history", "conversation", "reupload"] },
  { to: "/alerts", label: "Validation Alerts", icon: FiAlertTriangle, keywords: ["dtcd", "failed", "imbalance", "validation"] },
  { to: "/manager", label: "Manager", icon: FiCheckSquare, roles: ["manager"], keywords: ["review", "queue", "approve"] },
  { to: "/admin", label: "Admin", icon: FiUserCheck, roles: ["admin"], keywords: ["assignments", "managers", "employees"] },
  { to: "/settings", label: "Settings", icon: FiSettings, keywords: ["account", "profile", "security"] },
  { to: "/uploads", label: "Upload Center", icon: FiUploadCloud, keywords: ["upload", "files", "preview"] },
  { to: "/audit", label: "Audit Log", icon: FiActivity, roles: ["admin"], keywords: ["audit", "events", "history"] },
];



export default function AppShell() {
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [pendingActions, setPendingActions] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  const visibleNavItems = useMemo(
    () => navItems.filter((item) => !item.roles || item.roles.includes(user?.role)),
    [user?.role],
  );

  const initials = (user?.name || "LF")
    .split(" ")
    .map((word) => word[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const commandItems = useMemo(() => {
    const query = commandQuery.trim().toLowerCase();
    if (!query) return visibleNavItems;
    return visibleNavItems.filter((item) =>
      [item.label, ...(item.keywords || [])].join(" ").toLowerCase().includes(query)
    );
  }, [commandQuery, visibleNavItems]);

  const loadPendingActions = useCallback(async () => {
    if (!user) {
      setPendingActions(0);
      setNotifications([]);
      return;
    }
    const endpoint = ["manager", "admin"].includes(user.role) ? "/uploads?status=pending" : "/uploads";
    const [uploadsResponse, alertsResponse] = await Promise.all([
      api.get(endpoint),
      api.get("/alerts"),
    ]);
    const uploadItems = uploadsResponse.data.slice(0, 5).map((upload) => ({ type: "upload", ...upload }));
    const unreadAlerts = alertsResponse.data.filter((alert) => !alert.is_read);
    const alertItems = unreadAlerts.slice(0, 5).map((alert) => ({ type: "dtcd_alert", ...alert }));
    setNotifications([...alertItems, ...uploadItems].slice(0, 8));
    setPendingActions(
      unreadAlerts.length +
        (user.role === "employee"
          ? uploadsResponse.data.filter((item) => item.status === "pending" || item.status === "processing").length
          : uploadsResponse.data.length),
    );
  }, [user]);

  useEffect(() => {
    loadPendingActions().catch(() => {
      setPendingActions(0);
      setNotifications([]);
    });
  }, [loadPendingActions]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
      if (event.key === "Escape") {
        setCommandOpen(false);
        setShowNotifications(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (!commandOpen) setCommandQuery("");
  }, [commandOpen]);

  useWebSocket(
    "notifications",
    useCallback((event) => {
      if (event.event !== "dtcd_alert") return;
      const alert = { type: "dtcd_alert", ...event.payload };
      setNotifications((current) => [alert, ...current.filter((item) => item.id !== alert.id)].slice(0, 8));
      setPendingActions((current) => current + 1);
    }, []),
  );

  async function openNotification(notification) {
    setShowNotifications(false);
    if (notification.type === "dtcd_alert") {
      try {
        await api.patch(`/alerts/${notification.id}/read`);
      } catch {
        // Keep navigation responsive even if the read marker fails.
      }
      setPendingActions((current) => Math.max(0, current - (notification.is_read ? 0 : 1)));
      setNotifications((current) => current.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
      return navigate(`/alerts?entry=${encodeURIComponent(notification.entry_no)}&account=${encodeURIComponent(notification.account_code)}`);
    }
    if (user?.role === "manager") return navigate(`/manager?submission_id=${notification.id}`);
    if (user?.role === "admin") return navigate("/admin");
    navigate("/uploads");
  }

  function goToCommandItem(item) {
    navigate(item.to);
    setCommandOpen(false);
  }

  return (
    <div className="lf-reference-shell" style={{ gridTemplateColumns: collapsed ? "72px minmax(0,1fr)" : "264px minmax(0,1fr)" }}>

      {/* ── Sidebar ── */}
      <aside className={`lf-reference-sidebar lf-sidebar-collapsible${collapsed ? " is-collapsed" : ""}`}>

        {/* Brand / Logo */}
<div className="lf-reference-sidebar__brand lf-sidebar-brand">
  <div className="lf-sidebar-logo-wrap">
    <img src={logo} alt="LedgerFlow" style={{ width: 200, height: 160, objectFit: "contain" }} />
  </div>
</div>

        {/* Nav links */}
        <nav className="lf-reference-sidebar__nav">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.to || location.pathname.startsWith(item.to + "/");
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`lf-reference-sidebar__link lf-sidebar-link${isActive ? " is-active" : ""}`}
                title={collapsed ? item.label : undefined}
              >
                <Icon size={18} style={{ flexShrink: 0 }} />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>


        {/* Collapse toggle button */}
        <button
          className="lf-sidebar-toggle"
          onClick={() => setCollapsed((v) => !v)}
          type="button"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <FiChevronRight size={15} /> : <FiChevronLeft size={15} />}
        </button>
      </aside>

      {/* ── Main ── */}
      <div
        className="lf-reference-main"
        style={{
          background: "linear-gradient(135deg, #b8bde8 0%, #d4d8f5 40%, #eceffe 100%)",
          minHeight: "100vh",
        }}
      >
        <header className="lf-reference-topbar">
          <button className="lf-reference-search" onClick={() => setCommandOpen(true)} type="button">
            <FiSearch size={18} />
            <span>Search or run a command...</span>
            <kbd><FiCommand size={11} /> K</kbd>
          </button>

          <div className="lf-reference-topbar__right">
            <div className="lf-reference-connection">
              <span className="lf-reference-connection__dot" />
              <span>Connected</span>
            </div>

            <div className="lf-reference-notification-wrap">
              <button
                className="lf-reference-icon-button"
                onClick={async () => { await loadPendingActions(); setShowNotifications((v) => !v); }}
                type="button"
              >
                <FiBell size={18} />
                {pendingActions > 0 && (
                  <span className="lf-reference-notification-badge">
                    {pendingActions > 9 ? "9+" : pendingActions}
                  </span>
                )}
              </button>
              {showNotifications && (
                <div className="lf-reference-notification-panel">
                  <div className="lf-reference-notification-panel__head">
                    <strong>Notifications</strong>
                    <button className="lf-reference-icon-button is-small" onClick={() => setShowNotifications(false)} type="button">
                      <FiX size={14} />
                    </button>
                  </div>
                  <div>
                    {notifications.length
                      ? notifications.map((notification) => (
                          <button key={`${notification.type}-${notification.id}`} className="lf-reference-notification-row" onClick={() => openNotification(notification)} type="button">
                            <div>
                              {notification.type === "dtcd_alert" ? (
                                <>
                                  <strong>{notification.entry_no} · {notification.account_code}</strong>
                                  <span>Difference {formatNotificationCurrency(notification.difference)}</span>
                                </>
                              ) : (
                                <>
                                  <strong>{notification.filename}</strong>
                                  <span>{notification.total_rows || notification.rows || 0} rows</span>
                                </>
                              )}
                            </div>
                          </button>
                        ))
                      : <div className="lf-reference-empty">No notifications right now.</div>}
                  </div>
                </div>
              )}
            </div>

            <div className="lf-reference-avatar">{initials}</div>
            <button className="lf-reference-icon-button" onClick={logout} type="button">
              <FiLogOut size={18} />
            </button>
          </div>
        </header>

        <main className="lf-reference-content">
          <Outlet />
        </main>
      </div>

      {/* ── Command palette ── */}
      {commandOpen && createPortal(
        <div className="lf-command-overlay" onClick={() => setCommandOpen(false)} role="presentation">
          <div className="lf-command-dialog" onClick={(event) => event.stopPropagation()}>
            <div className="lf-command-dialog__input">
              <FiSearch size={16} />
              <input
                autoFocus
                value={commandQuery}
                onChange={(event) => setCommandQuery(event.target.value)}
                placeholder="Jump to a page"
              />
            </div>
            <div className="lf-command-dialog__results">
              {commandItems.length
                ? commandItems.map((item) => {
                    const Icon = item.icon;
                    return (
                      <button key={item.to} className="lf-command-result" onClick={() => goToCommandItem(item)} type="button">
                        <span className="lf-command-result__icon"><Icon size={15} /></span>
                        <span className="lf-command-result__copy">
                          <strong>{item.label}</strong>
                          <small>{item.keywords?.join(" · ")}</small>
                        </span>
                      </button>
                    );
                  })
                : <div className="lf-empty-inline">No matching pages.</div>}
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}

function formatNotificationCurrency(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  });
}
