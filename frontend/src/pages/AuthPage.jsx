import React from "react";
import { useState } from "react";
import { FiBarChart2, FiLock, FiLogIn, FiUserPlus } from "react-icons/fi";
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
  const requestedDestination = location.state?.from?.pathname;
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
    <main className="grid min-h-screen bg-mist lg:grid-cols-[1fr_420px]">
      <section className="hidden bg-white px-12 py-10 lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center bg-brand text-white" style={{ borderRadius: 8 }}>
            <FiBarChart2 />
          </div>
          <div>
            <div className="text-sm font-bold text-ink">LedgerFlow</div>
            <div className="text-xs text-muted">Analytics Platform</div>
          </div>
        </div>
        <div className="max-w-xl">
          <h1 className="text-4xl font-bold tracking-tight text-ink">Controlled uploads, visible approvals, cleaner analytics.</h1>
          <p className="mt-4 text-base text-muted">Sign in to upload spreadsheets, review manager queues, and keep every approved row tied to the right person.</p>
        </div>
        <div className="text-xs text-muted">PostgreSQL backed workflow workspace</div>
      </section>

      <section className="flex items-center justify-center p-5">
        <form className="w-full max-w-md elevated-panel p-5" onSubmit={submit}>
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-ink">{mode === "login" ? "Sign in" : "Create account"}</h1>
              <p className="text-sm text-muted">{mode === "login" ? "Use your LedgerFlow account." : "Choose the role you need for this workspace."}</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center bg-teal-50 text-brand" style={{ borderRadius: 8 }}>
              {mode === "login" ? <FiLogIn /> : <FiUserPlus />}
            </div>
          </div>

          <div className="mb-5 grid grid-cols-2 gap-2 rounded-lg bg-slate-100 p-1">
            <button type="button" className={`px-3 py-2 text-sm font-semibold ${mode === "login" ? "bg-white text-ink shadow-soft" : "text-muted"}`} style={{ borderRadius: 8 }} onClick={() => setMode("login")}>Login</button>
            <button type="button" className={`px-3 py-2 text-sm font-semibold ${mode === "register" ? "bg-white text-ink shadow-soft" : "text-muted"}`} style={{ borderRadius: 8 }} onClick={() => setMode("register")}>Register</button>
          </div>

          <div className="space-y-3">
            {mode === "register" && (
              <label className="block">
                <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted">Name</span>
                <input className="form-input" value={name} onChange={(event) => setName(event.target.value)} minLength={2} required />
              </label>
            )}
            <label className="block">
              <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted">Email</span>
              <input className="form-input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted">Password</span>
              <input className="form-input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required />
            </label>
            {mode === "register" && (
              <label className="block">
                <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted">Role</span>
                <select className="form-input" value={role} onChange={(event) => setRole(event.target.value)}>
                  <option value="employee">Employee</option>
                  <option value="manager">Manager</option>
                </select>
              </label>
            )}
          </div>

          {error && <div className="mt-4 border border-red-200 bg-red-50 p-3 text-sm text-danger" style={{ borderRadius: 8 }}>{error}</div>}

          <button className="primary-button mt-5 w-full" disabled={busy}>
            <FiLock /> {busy ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
      </section>
    </main>
  );
}
