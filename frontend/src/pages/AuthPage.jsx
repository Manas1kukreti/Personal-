import React from "react";
import { useState } from "react";
import { FiBarChart2, FiLock, FiMail, FiShield, FiUser, FiUserPlus } from "react-icons/fi";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function AuthPage() {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("employee");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { isAuthenticated, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const fromLocation = location.state?.from;
  const requestedDestination = fromLocation
    ? `${fromLocation.pathname || ""}${fromLocation.search || ""}${fromLocation.hash || ""}`
    : "";
  const destination = requestedDestination || "/dashboard";

  if (isAuthenticated) return <Navigate to={destination} replace />;

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      let session;
      if (mode === "login") {
        session = await login({ email, password });
      } else {
        session = await register({ name, email, password, role });
      }
      const roleHome = session?.user?.role === "admin" ? "/admin" : session?.user?.role === "manager" ? "/manager" : "/dashboard";
      navigate(requestedDestination || roleHome, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication failed. Check your details and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page-shell">
      <section className="auth-page-hero">
        <div className="auth-page-hero__brand">
          <div className="auth-page-hero__logo auth-depth-chip">
            <FiBarChart2 size={20} />
          </div>
          <div>
            <div className="auth-page-hero__brand-name">LedgerFlow</div>
            <div className="auth-page-hero__brand-sub">Analytics Platform</div>
          </div>
        </div>

        <div className="auth-page-hero__copy">
          <h1>Controlled uploads,</h1>
          <h1>visible approvals,</h1>
          <div className="auth-page-hero__headline-row">
            <span>cleaner</span>
            <span className="auth-page-hero__headline-chip auth-depth-chip">analytics.</span>
          </div>
          <p>
            Sign in to upload spreadsheets, review manager queues, and keep every approved row tied to the right person.
          </p>
        </div>

      <div className="auth-page-hero__footer">PostgreSQL-backed workflow workspace</div>
      </section>

      <section className="auth-page-form-wrap">
        <form className="auth-page-form elevated-panel fintech-card auth-depth-panel" onSubmit={submit}>
          <div className="auth-page-form__header">
            <h2>{mode === "login" ? "Welcome back" : "Create account"}</h2>
            <p>{mode === "login" ? "Sign in to your LedgerFlow account." : "Set up your workspace role."}</p>
          </div>

          <div className="auth-page-form__tabs">
            <button type="button" className={mode === "login" ? "is-active" : ""} onClick={() => setMode("login")}>Sign In</button>
            <button type="button" className={mode === "register" ? "is-active" : ""} onClick={() => setMode("register")}>Register</button>
          </div>

          <div className="auth-page-form__fields">
            {mode === "register" && (
              <Field label="Full Name" icon={<FiUserPlus size={15} />}>
                <input
                  className="form-input auth-page-form__input"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  minLength={2}
                  required
                  placeholder="Manas Kukreti"
                />
              </Field>
            )}

            <Field label="Email Address" icon={<FiMail size={15} />}>
              <input
                className="form-input auth-page-form__input"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                placeholder="name@company.com"
              />
            </Field>

            <Field label="Password" icon={<FiLock size={15} />}>
              <input
                className="form-input auth-page-form__input"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                required
                placeholder="Password"
              />
            </Field>

            {mode === "register" && (
              <Field label="Your Role" icon={<FiShield size={15} />}>
                <select className="form-input auth-page-form__input" value={role} onChange={(event) => setRole(event.target.value)}>
                  <option value="employee">Employee</option>
                  <option value="manager">Manager</option>
                </select>
              </Field>
            )}
          </div>

          {error && <div className="auth-page-form__error">{error}</div>}

          <button className="primary-button auth-page-form__submit" disabled={busy}>
            <FiLock size={16} />
            {busy ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
          </button>

          <p className="auth-page-form__switch">
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            <button type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}> 
              {mode === "login" ? "Sign up" : "Sign in"}
            </button>
          </p>
        </form>
      </section>
    </main>
  );
}

function Field({ label, icon, children }) {
  return (
    <label className="auth-page-form__field">
      <span>{label}</span>
      <div className="auth-page-form__field-control">
        <div className="auth-page-form__field-icon">{icon}</div>
        {children}
      </div>
    </label>
  );
}
