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
    <main className="grid min-h-screen bg-background lg:grid-cols-[1fr_380px]">
      {/* LEFT PANEL - Teal branding section (55% width on large screens) */}
      <section className="hidden flex-col justify-between px-12 py-10 lg:flex animate-slide-in-left relative overflow-hidden" style={{ background: "linear-gradient(135deg, #0D3B38 0%, #155E58 58%, #1E8278 100%)" }}>
        {/* Decorative circles */}
        <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-white" style={{ opacity: 0.07, animation: "floatSoft 7s ease-in-out infinite" }} />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-white" style={{ opacity: 0.05, animation: "floatSoft 8s ease-in-out infinite reverse" }} />
        <div className="absolute left-1/4 top-1/3 h-px w-2/3" style={{ background: "linear-gradient(90deg, transparent, rgba(58, 191, 177, 0.36), transparent)", animation: "shimmerLine 5s ease-in-out infinite" }} />
        
        <div className="relative z-10">
          {/* Logo */}
          <div className="flex items-center gap-3 animate-slide-in-left" style={{ animationDelay: "0.15s" }}>
            <div className="flex h-10 w-10 items-center justify-center text-white transition-all-smooth" style={{ borderRadius: 10, background: "rgba(255, 255, 255, 0.16)", border: "1px solid rgba(255,255,255,0.18)" }}>
              <FiBarChart2 size={20} />
            </div>
            <div>
              <div className="text-sm font-bold text-white">LedgerFlow</div>
              <div className="text-xs" style={{ color: "rgba(255, 255, 255, 0.6)" }}>Analytics Platform</div>
            </div>
          </div>

          {/* Animated headline */}
          <div className="max-w-xl mt-12">
            <h1 className="text-4xl font-medium leading-tight text-white" style={{ animation: "slideInFromLeft 0.6s ease-out 0.32s both" }}>
              Controlled uploads,
            </h1>
            <h1 className="text-4xl font-medium leading-tight text-white mt-3" style={{ animation: "slideInFromLeft 0.6s ease-out 0.49s both" }}>
              visible approvals,
            </h1>
            <div className="mt-3" style={{ animation: "slideInFromLeft 0.6s ease-out 0.66s both" }}>
              <span className="text-4xl font-medium leading-tight text-white">cleaner</span>
              <span 
                className="text-4xl font-medium ml-3 px-4 py-2 rounded-lg" 
                style={{ background: "rgba(58, 191, 177, 0.18)", color: "#C8FFF6", border: "1px solid rgba(58, 191, 177, 0.24)" }}
              >
                analytics.
              </span>
            </div>

            <p className="mt-6 text-base leading-relaxed" style={{ color: "rgba(255, 255, 255, 0.6)", animation: "fadeIn 0.6s ease-out 0.8s both" }}>
              Sign in to upload spreadsheets, review manager queues, and keep every approved row tied to the right person.
            </p>
          </div>
        </div>

        {/* Activity ticker - Real-time events */}
        <div className="relative z-10 space-y-3">
          <div className="flex items-center gap-2 mb-4" style={{ color: "rgba(255, 255, 255, 0.6)" }}>
            <div className="w-1 h-1 bg-white rounded-full" />
            <span className="text-xs font-medium uppercase">Live Activity</span>
          </div>
          <div className="space-y-2" style={{ animation: "tickerCycle 6s ease-in-out infinite" }}>
            <div className="flex items-center justify-between text-sm" style={{ color: "rgba(255, 255, 255, 0.8)" }}>
              <span>Upload approved from Finance team</span>
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-300 rounded text-xs font-medium">
                <span className="w-1 h-1 bg-green-400 rounded-full" /> Approved
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-xs relative z-10" style={{ color: "rgba(255, 255, 255, 0.3)" }}>
          PostgreSQL-backed workflow workspace
        </div>
      </section>

      {/* RIGHT PANEL - Form (360px fixed on large screens) */}
      <section className="flex items-center justify-center p-6" style={{ background: "#F7F5F0" }}>
        <form className="w-full max-w-sm elevated-panel fintech-card p-6 animate-fade-in-scale" onSubmit={submit} style={{ animationDelay: "0.2s" }}>
          {/* Form Header */}
          <div className="mb-6 animate-slide-in-top" style={{ animationDelay: "0.3s" }}>
            <h1 className="text-xl font-medium" style={{ color: "#0a3d2e" }}>
              {mode === "login" ? "Welcome back" : "Create account"}
            </h1>
            <p className="text-sm mt-1" style={{ color: "#6b9080" }}>
              {mode === "login" ? "Sign in to your LedgerFlow account." : "Set up your workspace role."}
            </p>
          </div>

          {/* Tab Switcher */}
          <div className="mb-6 grid grid-cols-2 gap-1 p-1" style={{ background: "#E7F5F1", borderRadius: 10 }}>
            <button 
              type="button" 
              className="px-3 py-2 text-sm font-medium transition-all-smooth rounded" 
              style={{
                background: mode === "login" ? "#ffffff" : "transparent",
                color: mode === "login" ? "#155E58" : "#6D837B",
                borderRadius: 8,
                boxShadow: mode === "login" ? "0 1px 3px rgba(0, 0, 0, 0.08)" : "none"
              }}
              onClick={() => setMode("login")}
            >
              Sign In
            </button>
            <button 
              type="button" 
              className="px-3 py-2 text-sm font-medium transition-all-smooth rounded" 
              style={{
                background: mode === "register" ? "#ffffff" : "transparent",
                color: mode === "register" ? "#155E58" : "#6D837B",
                borderRadius: 8,
                boxShadow: mode === "register" ? "0 1px 3px rgba(0, 0, 0, 0.08)" : "none"
              }}
              onClick={() => setMode("register")}
            >
              Register
            </button>
          </div>

          {/* Form Fields */}
          <div className="space-y-3">
            {mode === "register" && (
              <label className="block animate-slide-in-bottom" style={{ animationDelay: "0.35s" }}>
                <span className="mb-2 block text-xs font-medium uppercase tracking-wide" style={{ color: "#3a6655", letterSpacing: "0.06em" }}>Full Name</span>
                <div style={{ position: "relative" }}>
                  <FiUserPlus style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "#8ab8aa", fontSize: 15, pointerEvents: "none" }} />
                  <input 
                    className="form-input" 
                    value={name} 
                    onChange={(event) => setName(event.target.value)} 
                    minLength={2} 
                    required 
                    placeholder="John Doe"
                  />
                </div>
              </label>
            )}
            <label className="block animate-slide-in-bottom" style={{ animationDelay: mode === "register" ? "0.4s" : "0.35s" }}>
              <span className="mb-2 block text-xs font-medium uppercase tracking-wide" style={{ color: "#3a6655", letterSpacing: "0.06em" }}>Email Address</span>
              <div style={{ position: "relative" }}>
                <FiBarChart2 style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "#8ab8aa", fontSize: 15, pointerEvents: "none" }} />
                <input 
                  className="form-input" 
                  type="email" 
                  value={email} 
                  onChange={(event) => setEmail(event.target.value)} 
                  required 
                  placeholder="name@company.com"
                />
              </div>
            </label>
            <label className="block animate-slide-in-bottom" style={{ animationDelay: mode === "register" ? "0.45s" : "0.4s" }}>
              <span className="mb-2 block text-xs font-medium uppercase tracking-wide" style={{ color: "#3a6655", letterSpacing: "0.06em" }}>Password</span>
              <div style={{ position: "relative" }}>
                <FiLock style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "#8ab8aa", fontSize: 15, pointerEvents: "none" }} />
                <input 
                  className="form-input" 
                  type="password" 
                  value={password} 
                  onChange={(event) => setPassword(event.target.value)} 
                  minLength={8} 
                  required 
                  placeholder="••••••••"
                />
              </div>
            </label>
            {mode === "register" && (
              <label className="block animate-slide-in-bottom" style={{ animationDelay: "0.5s" }}>
                <span className="mb-2 block text-xs font-medium uppercase tracking-wide" style={{ color: "#3a6655", letterSpacing: "0.06em" }}>Your Role</span>
                <select 
                  className="form-input" 
                  value={role} 
                  onChange={(event) => setRole(event.target.value)}
                  style={{ paddingLeft: 36 }}
                >
                  <option value="employee">Employee</option>
                  <option value="manager">Manager</option>
                </select>
              </label>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div 
              className="mt-4 border p-3 text-sm animate-shake text-danger" 
              style={{ borderColor: "#a32d2d", background: "#fcebeb", borderRadius: 8 }}
            >
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button 
            className="primary-button mt-6 w-full justify-center animate-slide-in-bottom" 
            disabled={busy}
            style={{ animationDelay: mode === "register" ? "0.55s" : "0.45s" }}
          >
            <FiLock size={16} /> {busy ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
          </button>

          {/* Toggle Link */}
          <p className="mt-4 text-center text-xs animate-fade-in" style={{ color: "#8ab8aa", animationDelay: "0.6s" }}>
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            <button
              type="button"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="font-medium transition-colors-smooth"
              style={{ color: "#155E58" }}
            >
              {mode === "login" ? "Sign up" : "Sign in"}
            </button>
          </p>
        </form>
      </section>
    </main>
  );
}
