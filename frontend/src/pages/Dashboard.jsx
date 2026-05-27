import React from "react";
import { useState, useEffect, useRef, useCallback } from "react";
import { FiDownload, FiFilter, FiRefreshCw, FiX } from "react-icons/fi";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid,
  ResponsiveContainer, Tooltip, XAxis, YAxis, Legend
} from "recharts";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";
 
// ─── Color tokens (indigo theme) ─────────────────────────────────────────────
const C = {
  pageBg:      "#F0F1FA",
  cardBg:      "#ffffff",
  cardBorder:  "#E2E5F5",
  primary:     "#6366F1",
  primaryHov:  "#4F46E5",
  primaryLight:"#EEF2FF",
  textHead:    "#1E1F3B",
  textBody:    "#3D3F5C",
  textMuted:   "#1E1F3B",
  textFaint:   "#3D3F5C",
  divider:     "#E2E5F5",
  up:          "#22C55E",
  down:        "#EF4444",
  warn:        "#EF4444",
  chartBar1:   "#6366F1",
  chartBar2:   "#C7D2FE",
};
 
// ─── Helpers ──────────────────────────────────────────────────────────────────
const MONTHS = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"];
const DAYS   = ["Su","Mo","Tu","We","Th","Fr","Sa"];
const DATE_PRESETS = [
  { key: "all",           label: "All Time" },
  { key: "this_month",    label: "This Month" },
  { key: "six_months",    label: "6 Months" },
  { key: "twelve_months", label: "12 Months" },
  { key: "custom",        label: "Custom Range" },
];
 
function fmt(n) { return `₹${Number(n).toLocaleString("en-IN")}`; }
 
function datesForPreset(preset) {
  const today = new Date();
  const end   = toDateInputValue(today);
  if (preset === "this_month")
    return { dateFrom: toDateInputValue(new Date(today.getFullYear(), today.getMonth(), 1)), dateTo: end };
  if (preset === "six_months")
    return { dateFrom: toDateInputValue(new Date(today.getFullYear(), today.getMonth() - 5, 1)), dateTo: end };
  if (preset === "twelve_months")
    return { dateFrom: toDateInputValue(new Date(today.getFullYear(), today.getMonth() - 11, 1)), dateTo: end };
  return { dateFrom: "", dateTo: "" };
}
 
function toDateInputValue(date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString().slice(0, 10);
}
 
// ─── Delta Badge ──────────────────────────────────────────────────────────────
function DeltaBadge({ pct, up }) {
  if (pct == null) return null;
  return (
    <span style={{ fontSize: 12, fontWeight: 600, color: up ? C.up : C.down, display: "flex", alignItems: "center", gap: 2 }}>
      {up ? "↑" : "↓"} {Math.abs(pct)}%
    </span>
  );
}
 
// ─── Mini Calendar ────────────────────────────────────────────────────────────
function MiniCalendar({ year, month, selected, hovered, onDayClick, onDayHover, today }) {
  const firstDay    = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
 
  const inRange = (d) => {
    if (!d) return false;
    const anchor = selected.from, end = selected.to || hovered;
    if (!anchor || !end) return false;
    const [a, b] = anchor <= end ? [anchor, end] : [end, anchor];
    return d > a && d < b;
  };
  const isStart  = (d) => d && selected.from && d.toDateString() === selected.from.toDateString();
  const isEnd    = (d) => d && selected.to   && d.toDateString() === selected.to.toDateString();
  const isToday  = (d) => d && d.toDateString() === today.toDateString();
  const isFuture = (d) => d && d > today;
 
  return (
    <div style={{ flex: 1 }}>
      <div style={{ textAlign: "center", fontWeight: 600, fontSize: 13, color: C.textBody, marginBottom: 12 }}>
        {MONTHS[month]} {year}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2 }}>
        {DAYS.map(d => (
          <div key={d} style={{ textAlign: "center", fontSize: 10, fontWeight: 600, color: C.textMuted, padding: "4px 0", textTransform: "uppercase", letterSpacing: "0.05em" }}>{d}</div>
        ))}
        {cells.map((d, i) => {
          const sel = isStart(d) || isEnd(d), range = inRange(d), disabled = isFuture(d);
          return (
            <div key={i}
              onClick={() => d && !disabled && onDayClick(d)}
              onMouseEnter={() => d && !disabled && onDayHover(d)}
              style={{
                textAlign: "center", height: 34, lineHeight: "34px", fontSize: 13,
                borderRadius: sel ? 8 : range ? 0 : 8,
                background: sel ? C.primary : range ? C.primaryLight : "transparent",
                color: sel ? "#fff" : disabled ? C.cardBorder : isToday(d) ? C.primary : C.textBody,
                fontWeight: isToday(d) && !sel ? 700 : 400,
                cursor: d && !disabled ? "pointer" : "default", userSelect: "none",
              }}
            >
              {d ? d.getDate() : ""}
            </div>
          );
        })}
      </div>
    </div>
  );
}
 
// ─── Date Range Modal ─────────────────────────────────────────────────────────
function DateRangeModal({ onClose, onApply }) {
  const today     = new Date();
  const initMonth = today.getMonth() === 0 ? 11 : today.getMonth() - 1;
  const initYear  = today.getMonth() === 0 ? today.getFullYear() - 1 : today.getFullYear();
  const [viewYear,  setViewYear]  = useState(initYear);
  const [viewMonth, setViewMonth] = useState(initMonth);
  const [selected,  setSelected]  = useState({ from: null, to: null });
  const [hovered,   setHovered]   = useState(null);
  const ref = useRef(null);
 
  const month2 = viewMonth === 11 ? 0 : viewMonth + 1;
  const year2  = viewMonth === 11 ? viewYear + 1 : viewYear;
  const prevMonth = () => { if (viewMonth === 0) { setViewMonth(11); setViewYear(y=>y-1); } else setViewMonth(m=>m-1); };
  const nextMonth = () => { if (viewMonth === 11) { setViewMonth(0); setViewYear(y=>y+1); } else setViewMonth(m=>m+1); };
 
  const handleDayClick = (d) => {
    if (!selected.from || selected.to) setSelected({ from: d, to: null });
    else if (d < selected.from) setSelected({ from: d, to: selected.from });
    else setSelected({ from: selected.from, to: d });
  };
 
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [onClose]);
 
  const fmtL   = (d) => d ? `${MONTHS[d.getMonth()].slice(0,3)} ${String(d.getDate()).padStart(2,"0")}, ${d.getFullYear()}` : "";
  const canApply = selected.from && selected.to;
 
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.18)", zIndex: 200, display: "flex", alignItems: "flex-start", justifyContent: "flex-end", paddingTop: 64, paddingRight: 24 }}>
      <div ref={ref} style={{ background: "#fff", border: `1px solid ${C.cardBorder}`, borderRadius: 16, boxShadow: "0 8px 40px rgba(99,102,241,0.13)", padding: 24, width: 560 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: C.textBody }}>Select Date Range</span>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: C.textMuted, padding: 4 }}><FiX size={16} /></button>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 4 }}>
            <NavBtn onClick={() => setViewYear(y=>y-1)}>‹‹</NavBtn>
            <NavBtn onClick={prevMonth}>‹</NavBtn>
          </div>
          <span style={{ fontSize: 13, fontWeight: 600, color: C.textBody }}>{viewYear}</span>
          <div style={{ display: "flex", gap: 4 }}>
            <NavBtn onClick={nextMonth}>›</NavBtn>
            <NavBtn onClick={() => setViewYear(y=>y+1)}>››</NavBtn>
          </div>
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          <MiniCalendar year={viewYear} month={viewMonth} selected={selected} hovered={hovered} onDayClick={handleDayClick} onDayHover={setHovered} today={today} />
          <MiniCalendar year={year2}    month={month2}    selected={selected} hovered={hovered} onDayClick={handleDayClick} onDayHover={setHovered} today={today} />
        </div>
        <div style={{ borderTop: `1px solid ${C.divider}`, marginTop: 16, paddingTop: 14, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: C.textMuted }}>
            {canApply ? `${fmtL(selected.from)} – ${fmtL(selected.to)}` : "Pick a start and end date"}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={onClose} style={{ padding: "7px 16px", fontSize: 12, fontWeight: 500, background: "#F6F7FD", border: `1px solid ${C.cardBorder}`, borderRadius: 9, cursor: "pointer", color: C.textBody }}>Cancel</button>
            <button onClick={() => canApply && onApply(selected)} style={{ padding: "7px 16px", fontSize: 12, fontWeight: 600, background: canApply ? C.primary : C.cardBorder, color: "#fff", border: "none", borderRadius: 9, cursor: canApply ? "pointer" : "not-allowed" }}>Apply</button>
          </div>
        </div>
      </div>
    </div>
  );
}
 
function NavBtn({ onClick, children }) {
  return (
    <button onClick={onClick} style={{ padding: "4px 10px", background: "#F6F7FD", border: `1px solid ${C.cardBorder}`, borderRadius: 6, cursor: "pointer", color: C.textMuted, fontSize: 13, fontWeight: 600 }}>
      {children}
    </button>
  );
}
 
// ─── Filter Panel ─────────────────────────────────────────────────────────────
function FilterPanel({ filters, onFilterChange, datePreset, onPresetChange, customLabel }) {
  return (
    <div style={{ background: "#F6F7FD", border: `1px solid ${C.divider}`, borderRadius: 12, padding: "16px 20px", marginBottom: 20, display: "flex", gap: 32, alignItems: "flex-start", flexWrap: "wrap" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: C.textMuted, textTransform: "uppercase", letterSpacing: "0.06em" }}>GL Date Range</span>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {DATE_PRESETS.map(p => {
            const active = datePreset === p.key;
            return (
              <button key={p.key} onClick={() => onPresetChange(p.key)} style={{
                padding: "7px 12px", fontSize: 12, fontWeight: 500, borderRadius: 10,
                background: active ? C.primary : "#fff",
                color:      active ? "#fff"    : C.textMuted,
                border:     `1px solid ${active ? C.primary : C.cardBorder}`,
                cursor: "pointer"
              }}>
                {p.key === "custom" && customLabel ? customLabel : p.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
 
// ─── KPI Card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, delta }) {
  return (
    <div style={{ background: C.cardBg, border: `1px solid ${C.cardBorder}`, borderRadius: 14, padding: "18px 20px", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.textMuted, letterSpacing: "0.08em", textTransform: "uppercase" }}>{label}</div>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <div style={{ fontSize: 26, fontWeight: 700, color: C.textHead, lineHeight: 1 }}>{value}</div>
        {delta && <DeltaBadge pct={delta.pct} up={delta.up} />}
      </div>
      <div style={{ fontSize: 11, color: C.textFaint }}>vs previous period</div>
    </div>
  );
}
 
// ─── Amount Card ──────────────────────────────────────────────────────────────
function AmountCard({ label, amount, sub, delta, warn }) {
  return (
    <div style={{ background: C.cardBg, border: `1px solid ${C.cardBorder}`, borderRadius: 14, padding: "18px 22px" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.textMuted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: C.textHead }}>{fmt(amount)}</div>
        {delta && <DeltaBadge pct={delta.pct} up={delta.up} />}
      </div>
      <div style={{ fontSize: 12, color: warn ? C.warn : C.textFaint, marginTop: 4 }}>{sub}</div>
    </div>
  );
}
 
// ─── Custom Tooltip ───────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label, currency }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#fff", border: `1px solid ${C.cardBorder}`, borderRadius: 10, padding: "10px 14px", boxShadow: "0 4px 16px rgba(99,102,241,0.10)", fontSize: 12 }}>
      <div style={{ fontWeight: 600, color: C.textBody, marginBottom: 6 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color, display: "inline-block" }} />
          <span style={{ color: C.textMuted }}>{p.name}:</span>
          <span style={{ fontWeight: 600, color: C.textBody }}>{currency ? fmt(p.value) : p.value}</span>
        </div>
      ))}
    </div>
  );
}
 
// ─── Header Button ────────────────────────────────────────────────────────────
function HeaderBtn({ icon, label, onClick, active }) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 7, padding: "8px 14px",
      fontSize: 13, fontWeight: 500, borderRadius: 10,
      border: `1px solid ${active ? C.primary : C.cardBorder}`,
      background: active ? C.primaryLight : "#fff",
      color: active ? C.primary : C.textBody,
      cursor: "pointer"
    }}>
      {icon && <span style={{ display: "flex", alignItems: "center" }}>{icon}</span>}
      {label}
    </button>
  );
}
 
// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const { user } = useAuth();
 
  const [data,        setData]        = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [showPicker,  setShowPicker]  = useState(false);
  const [datePreset,  setDatePreset]  = useState("all");
  const [filters,     setFilters]     = useState({ dateFrom: "", dateTo: "" });
  const [txMetric,    setTxMetric]    = useState("total");
  const [txPreset,    setTxPreset]    = useState("all");
 
  const loadKpis = useCallback(async () => {
    const params = new URLSearchParams();
    if (filters.dateFrom) params.set("date_from", `${filters.dateFrom}T00:00:00`);
    if (filters.dateTo)   params.set("date_to",   `${filters.dateTo}T23:59:59`);
    const response = await api.get(
      `/analytics/kpis${params.toString() ? `?${params.toString()}` : ""}`
    );
    setData(response.data);
  }, [filters]);
 
  useEffect(() => { loadKpis(); }, [loadKpis]);
 
  useWebSocket(
    "dashboard",
    useCallback(
      (event) => { if (event.event === "dashboard_refresh" || event.event === "kpi.update") loadKpis(); },
      [loadKpis]
    )
  );
 
  const handlePresetChange = (key) => {
    setDatePreset(key);
    if (key === "custom") { setShowPicker(true); }
    else { setCustomLabel(null); setShowPicker(false); setFilters(f => ({ ...f, ...datesForPreset(key) })); }
  };
 
  const handleCustomApply = ({ from, to }) => {
    setFilters(f => ({ ...f, dateFrom: toDateInputValue(from), dateTo: toDateInputValue(to) }));
    const f2 = `${MONTHS[from.getMonth()].slice(0,3)} ${from.getDate()}`;
    const t2 = `${MONTHS[to.getMonth()].slice(0,3)} ${to.getDate()}, ${to.getFullYear()}`;
    setCustomLabel(`${f2} – ${t2}`);
    setShowPicker(false);
  };
 
  const exportCsv = () => {
    if (!data) return;
    const t = data.totals || {};
    const rows = [
      ["Metric","Value"],
      ["Total Rows", t.rows ?? 0],
      ["Total Debits", t.total_debits ?? 0],
      ["Total Credits", t.total_credits ?? 0],
      ["Net", t.net ?? 0],
      ["Total Entry Groups", t.total_entry_groups ?? 0],
      ["Balanced Entry Groups", t.balanced_entry_groups ?? 0],
      ["Unbalanced Entry Groups", t.unbalanced_entry_groups ?? 0],
      ["Uploads", t.uploads ?? 0],
      ["Approved", t.approved ?? 0],
      ["Pending", t.pending ?? 0],
      ["Declined", t.declined ?? 0],
      ["Approval Rate", `${t.approval_rate ?? 0}%`],
    ];
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([rows.map(r=>r.join(",")).join("\n")], { type: "text/csv" }));
    a.download = `ledgerflow-dashboard-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  };
 
  const totals = data?.totals || {};
 
  // ── Chart data ──────────────────────────────────────────────────────────────
  // Daily debit/credit trend
  const dailyTrend = (data?.daily_trends || []).map(item => ({
    day:     new Date(item.date).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
    debits:  Number(item.debits  || 0),
    credits: Number(item.credits || 0),
  }));
 
  // Account class breakdown bar chart
  const classBreakdown = (data?.account_class_breakdown || []).map(item => ({
    name:    item.account_class || "Unknown",
    debits:  Number(item.debits  || 0),
    credits: Number(item.credits || 0),
  }));

  const txPresetDates = (preset) => {
    const today = new Date();
    if (preset === "3m")  return new Date(today.getFullYear(), today.getMonth() - 3, 1);
    if (preset === "6m")  return new Date(today.getFullYear(), today.getMonth() - 6, 1);
    if (preset === "12m") return new Date(today.getFullYear(), today.getMonth() - 12, 1);
    return null;
  };

  const txTrend = (data?.daily_transaction_trends || [])
    .filter(item => {
      if (txPreset === "all") return true;
      const from = txPresetDates(txPreset);
      return from ? new Date(item.date) >= from : true;
    })
    .map(item => ({
      day:   new Date(item.date).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
      value: Number(item[txMetric] || 0),
    }));
 
  return (
    <div style={{ background: "transparent", minHeight: "100vh", padding: "28px 32px", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
 
      {showPicker && <DateRangeModal onClose={() => setShowPicker(false)} onApply={handleCustomApply} />}
 
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: C.textHead }}>Analytics Overview</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: C.textMuted }}>
            {user?.role === "employee" ? "Monitor your upload performance and key metrics" : "Monitor your general ledger performance and key metrics"}
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <HeaderBtn label="Custom range" onClick={() => { setDatePreset("custom"); setShowPicker(true); }} active={datePreset === "custom"} />
          <HeaderBtn icon={<FiFilter size={13} />} label="Filter"  onClick={() => setShowFilters(v => !v)} active={showFilters} />
          <HeaderBtn icon={<FiDownload size={13} />} label="Export" onClick={exportCsv} />
          <button onClick={loadKpis} title="Refresh" style={{ width: 38, height: 38, borderRadius: 10, border: `1px solid ${C.cardBorder}`, background: "#fff", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <FiRefreshCw size={15} color={C.textMuted} />
          </button>
        </div>
      </div>
 
      {/* Filters */}
      {showFilters && (
        <FilterPanel filters={filters} onFilterChange={(k,v) => setFilters(f=>({...f,[k]:v}))} datePreset={datePreset} onPresetChange={handlePresetChange} customLabel={customLabel} />
      )}
 
      {/* Loading guard */}
      {!data ? (
        <div style={{ textAlign: "center", padding: 60, color: C.textMuted, fontSize: 13 }}>Loading...</div>
      ) : (
        <>
          {/* KPI Cards — row 1: submission workflow counts */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 16 }}>
            <KpiCard label="In Review"       value={totals.pending             ?? 0} />
            <KpiCard label="Approved"        value={totals.approved            ?? 0} delta={{ pct: 12.5, up: true }} />
            <KpiCard label="Declined"        value={totals.declined            ?? 0} delta={{ pct: 15.6, up: false }} />
            <KpiCard label="Total GL Rows"   value={(totals.rows               ?? 0).toLocaleString("en-IN")} />
          </div>
 
          {/* Amount Cards — row 2: GL financials */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14, marginBottom: 20 }}>
            <AmountCard
              label="Total Debits"
              amount={totals.total_debits ?? 0}
              sub={`${(totals.rows ?? 0).toLocaleString("en-IN")} rows`}
            />
            <AmountCard
              label="Total Credits"
              amount={totals.total_credits ?? 0}
              sub={`${totals.approval_rate ?? 0}% approval rate`}
              delta={{ pct: 6.2, up: true }}
            />
            <AmountCard
              label="Net Position"
              amount={totals.net ?? 0}
              sub={`Debits minus credits`}
              warn={(totals.net ?? 0) < 0}
            />
            <div style={{ background: C.cardBg, border: `1px solid ${C.cardBorder}`, borderRadius: 14, padding: "18px 22px" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: C.textMuted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>Balanced Entries</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: C.textHead }}>{totals.balanced_entry_groups ?? 0}</div>
              <div style={{ fontSize: 12, color: (totals.unbalanced_entry_groups ?? 0) > 0 ? C.warn : C.textFaint, marginTop: 4 }}>
                {(totals.unbalanced_entry_groups ?? 0) > 0 ? `⚠ ${totals.unbalanced_entry_groups} unbalanced` : "All entries balanced ✓"}
              </div>
            </div>
            <div style={{ background: C.cardBg, border: `1px solid ${C.cardBorder}`, borderRadius: 14, padding: "18px 22px" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: C.textMuted, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>Under Investigation</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: (totals.unbalanced_entry_groups ?? 0) > 0 ? C.warn : C.textHead }}>
                {totals.unbalanced_entry_groups ?? 0}
              </div>
              <div style={{ fontSize: 12, color: (totals.unbalanced_entry_groups ?? 0) > 0 ? C.warn : C.textFaint, marginTop: 4 }}>
                {(totals.unbalanced_entry_groups ?? 0) > 0 ? "⚠ Entries need review" : "None flagged ✓"}
              </div>
            </div>
          </div>

          {/* Charts */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
 
            {/* Transaction Trend Chart */}
            <div style={{ background: C.cardBg, border: `1px solid ${C.cardBorder}`, borderRadius: 16, padding: "20px 22px" }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 12 }}>
                <div>
                  <h2 style={{ margin: "0 0 2px", fontSize: 14, fontWeight: 700, color: C.textHead }}>Transaction Trend</h2>
                  <p style={{ margin: 0, fontSize: 12, color: C.textMuted }}>Daily transaction counts over time</p>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  {[["all","All"],["3m","3M"],["6m","6M"],["12m","12M"]].map(([key, label]) => (
                    <button key={key} onClick={() => setTxPreset(key)} style={{
                      padding: "5px 10px", fontSize: 11, fontWeight: 600, borderRadius: 8, cursor: "pointer",
                      background: txPreset === key ? C.primary : "#F6F7FD",
                      color:      txPreset === key ? "#fff"    : C.textMuted,
                      border:     `1px solid ${txPreset === key ? C.primary : C.cardBorder}`,
                    }}>{label}</button>
                  ))}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                {[["total","Total Initiated","#6366F1"],["completed","Completed","#22C55E"],["under_investigation","Under Investigation","#EF4444"]].map(([key, label, color]) => (
                  <button key={key} onClick={() => setTxMetric(key)} style={{
                    padding: "6px 14px", fontSize: 12, fontWeight: 600, borderRadius: 10, cursor: "pointer",
                    background: txMetric === key ? color : "#F6F7FD",
                    color:      txMetric === key ? "#fff" : C.textMuted,
                    border:     `1px solid ${txMetric === key ? color : C.cardBorder}`,
                  }}>{label}</button>
                ))}
              </div>
              {txTrend.length === 0
                ? <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 220, fontSize: 13, color: C.textMuted }}>No data for selected range</div>
                : (
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={txTrend} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
                      <defs>
                        <linearGradient id="txFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor={txMetric === "completed" ? "#22C55E" : txMetric === "under_investigation" ? "#EF4444" : C.primary} stopOpacity={0.25} />
                          <stop offset="95%" stopColor={txMetric === "completed" ? "#22C55E" : txMetric === "under_investigation" ? "#EF4444" : C.primary} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke={C.divider} vertical={false} />
                      <XAxis dataKey="day" tick={{ fontSize: 10, fill: C.textMuted }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fontSize: 10, fill: C.textMuted }} tickLine={false} axisLine={false} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area type="monotone" dataKey="value"
                        name={txMetric === "completed" ? "Completed" : txMetric === "under_investigation" ? "Under Investigation" : "Total Initiated"}
                        stroke={txMetric === "completed" ? "#22C55E" : txMetric === "under_investigation" ? "#EF4444" : C.primary}
                        fill="url(#txFill)" strokeWidth={2.5}
                        dot={{ r: 3, strokeWidth: 0 }} activeDot={{ r: 5 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
            </div>
 
            {/* Account Class Breakdown */}
            <div style={{ background: C.cardBg, border: `1px solid ${C.cardBorder}`, borderRadius: 16, padding: "20px 22px" }}>
              <h2 style={{ margin: "0 0 2px", fontSize: 14, fontWeight: 700, color: C.textHead }}>Account Class Breakdown</h2>
              <p style={{ margin: "0 0 16px", fontSize: 12, color: C.textMuted }}>Debits vs credits by account class</p>
              {classBreakdown.length === 0
                ? <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 260, fontSize: 13, color: C.textMuted }}>No data for selected range</div>
                : (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={classBreakdown} margin={{ top: 4, right: 8, bottom: 0, left: -10 }} barGap={3}>
                      <CartesianGrid strokeDasharray="3 3" stroke={C.divider} vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: C.textMuted }} tickLine={false} axisLine={false} />
                      <YAxis               tick={{ fontSize: 10, fill: C.textMuted }} tickLine={false} axisLine={false} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                      <Tooltip content={<CustomTooltip currency />} />
                      <Legend verticalAlign="bottom" height={28} iconType="square" iconSize={10} formatter={(v) => <span style={{ fontSize: 11, color: C.textMuted }}>{v}</span>} />
                      <Bar dataKey="debits"  name="Debits"  fill={C.chartBar1} radius={[4,4,0,0]} />
                      <Bar dataKey="credits" name="Credits" fill={C.chartBar2} radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
            </div>
 
          </div>
        </>
      )}
 
    </div>
  );
}
 