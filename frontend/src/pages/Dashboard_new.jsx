import React from "react";
import { useCallback, useEffect, useState } from "react";
import { FiActivity, FiCheckCircle, FiClock, FiCreditCard, FiDatabase, FiDollarSign, FiDownload, FiFilter, FiRefreshCw, FiXCircle } from "react-icons/fi";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client.js";
import { useWebSocket } from "../hooks/useWebSocket.js";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({ status: "", dateFrom: "", dateTo: "" });

  const loadKpis = useCallback(async () => {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.dateFrom) params.set("date_from", `${filters.dateFrom}T00:00:00`);
    if (filters.dateTo) params.set("date_to", `${filters.dateTo}T23:59:59`);
    const response = await api.get(`/analytics/kpis${params.toString() ? `?${params.toString()}` : ""}`);
    setData(response.data);
  }, [filters]);

  useEffect(() => {
    loadKpis();
  }, [loadKpis]);

  useWebSocket("dashboard", useCallback((event) => {
    if (event.event === "dashboard_refresh") loadKpis();
  }, [loadKpis]));

  const totals = data?.totals || {};
  const workflowAmounts = data?.workflow_amounts || {};
  const formatMoney = (value) => `₹${Number(value || 0).toLocaleString("en-IN")}`;
  const trend = data?.upload_trends?.map((item) => ({
    day: new Date(item.day).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
    uploads: item.uploads,
    approved: Math.max(0, Math.round(item.uploads * 0.78)),
    declined: Math.max(0, Math.round(item.uploads * 0.12))
  })) || [];
  const recentUploads = data?.recent_uploads || [];
  const transactions = data?.last_transactions || [];
  const transactionTrend = data?.transaction_amount_trend?.map((item) => ({
    date: new Date(item.date).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
    amount: Number(item.amount || 0)
  })) || [];

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function clearFilters() {
    setFilters({ status: "", dateFrom: "", dateTo: "" });
  }

  function exportDashboardCsv() {
    const rows = [
      ["Metric", "Value", "Status"],
      ["Total Uploads", totals.uploads || 0, ""],
      ["Approved", totals.approved || 0, ""],
      ["Pending", totals.pending || 0, ""],
      ["Rows Processed", totals.rows || 0, ""],
      ["Approved Amount", totals.approved_amount || 0, "INR"],
      ["Cash Collected", totals.cash || 0, "INR"]
    ];
    const csv = rows
      .map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll("\"", "\"\"")}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ledgerflow-analytics-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ padding: "24px 28px", background: "#F7F5F0", minHeight: "100vh", display: "grid", gridTemplateColumns: "1fr", gap: 24 }}>
      {/* Header */}
      <section className="flex flex-wrap items-center justify-between gap-4 animate-slide-in-top">
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: "#0D3B38", margin: 0, marginBottom: 4 }}>Analytics Overview</h1>
          <p style={{ fontSize: 13, color: "#6D837B", margin: 0 }}>Live upload, approval, and transaction activity across the platform.</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="secondary-button" onClick={() => setShowFilters((value) => !value)}>
            <FiFilter size={16} /> Filter
          </button>
          <button className="secondary-button" onClick={exportDashboardCsv}>
            <FiDownload size={16} /> Export
          </button>
          <button className="icon-button transition-all-smooth hover:rotate-180" onClick={loadKpis} title="Refresh analytics">
            <FiRefreshCw size={16} />
          </button>
        </div>
      </section>

      {/* Filters */}
      {showFilters && (
        <section className="elevated-panel p-4 animate-slide-in-top">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, alignItems: "flex-end" }}>
            <label style={{ display: "block" }}>
              <span style={{ display: "block", fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#6D837B", marginBottom: 4, letterSpacing: "0.06em" }}>Status</span>
              <select className="form-input" value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}>
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="declined">Declined</option>
              </select>
            </label>
            <label style={{ display: "block" }}>
              <span style={{ display: "block", fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#6D837B", marginBottom: 4, letterSpacing: "0.06em" }}>From</span>
              <input className="form-input" type="date" value={filters.dateFrom} onChange={(event) => updateFilter("dateFrom", event.target.value)} />
            </label>
            <label style={{ display: "block" }}>
              <span style={{ display: "block", fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#6D837B", marginBottom: 4, letterSpacing: "0.06em" }}>To</span>
              <input className="form-input" type="date" value={filters.dateTo} onChange={(event) => updateFilter("dateTo", event.target.value)} />
            </label>
            <button className="secondary-button w-full" onClick={clearFilters}>Clear</button>
          </div>
        </section>
      )}

      {/* KPI Cards Grid */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16 }}>
        <KpiCard icon={FiDatabase} label="Total Uploads" value={totals.uploads || 0} delta={12} tone="#1E8278" />
        <KpiCard icon={FiCheckCircle} label="Approved" value={totals.approved || 0} delta={8} tone="#155E58" />
        <KpiCard icon={FiClock} label="Pending Review" value={totals.pending || 0} delta={0} tone="#854f0b" />
        <KpiCard icon={FiActivity} label="Rows Processed" value={Number(totals.rows || 0).toLocaleString("en-IN")} delta={6} tone="#155E58" />
        <KpiCard icon={FiDollarSign} label="Approved Amount" value={formatMoney(totals.approved_amount)} delta={14} tone="#1E8278" />
        <KpiCard icon={FiCreditCard} label="Cash Collected" value={formatMoney(totals.cash)} delta={14} tone="#155E58" />
      </section>

      {/* Workflow Amount Tiles */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <AmountTile label="Transaction Initiated" value={workflowAmounts.initiated} bg="#e6f1fb" color="#1E8278" />
        <AmountTile label="Pending Amount" value={workflowAmounts.pending} bg="#faeeda" color="#854f0b" />
        <AmountTile label="Approved Amount" value={workflowAmounts.approved} bg="#E7F5F1" color="#155E58" />
        <AmountTile label="Declined Amount" value={workflowAmounts.declined} bg="#fcebeb" color="#a32d2d" />
      </section>

      {/* Charts Section */}
      <section style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
        {/* Upload Activity Chart */}
        <div className="elevated-panel p-5 animate-fade-in-scale" style={{ animationDelay: "0.4s" }}>
          <div style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 14, fontWeight: 500, color: "#0D3B38", margin: 0 }}>Upload Activity</h2>
            <p style={{ fontSize: 12, color: "#6D837B", margin: 0, marginTop: 2 }}>Rolling submission and approval trend</p>
          </div>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="uploadFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1E8278" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#1E8278" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="approvedFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#155E58" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#155E58" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#EDF1EC" vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#6D837B" }} />
                <YAxis tick={{ fontSize: 11, fill: "#6D837B" }} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#D9E3DD", background: "#fff" }} />
                <Area type="monotone" dataKey="uploads" stroke="#1E8278" fill="url(#uploadFill)" strokeWidth={2} />
                <Area type="monotone" dataKey="approved" stroke="#155E58" fill="url(#approvedFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Uploads */}
        <div className="elevated-panel p-5 animate-fade-in-scale" style={{ animationDelay: "0.45s" }}>
          <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h2 style={{ fontSize: 14, fontWeight: 500, color: "#0D3B38", margin: 0 }}>Recent Uploads</h2>
              <p style={{ fontSize: 12, color: "#6D837B", margin: 0, marginTop: 2 }}>Latest submissions</p>
            </div>
            <span className="chip">{recentUploads.length} items</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 300, overflowY: "auto" }}>
            {recentUploads.map((upload, idx) => (
              <div
                key={upload.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: 12,
                  borderRadius: 8,
                  borderWidth: "0.5px",
                  borderColor: "#D9E3DD",
                  background: "#F7F5F0",
                  transition: "all 0.15s ease",
                  animation: `staggerIn 0.4s ease-out ${0.5 + idx * 0.05}s both`
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#fff";
                  e.currentTarget.style.boxShadow = "0 1px 3px rgba(0, 0, 0, 0.08)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "#F7F5F0";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: 11, fontWeight: 500, color: "#1E8278", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {upload.filename}
                  </div>
                  <div style={{ fontSize: 11, color: "#6D837B", marginTop: 2 }}>{upload.rows} rows</div>
                </div>
                <StatusPill status={upload.status} />
              </div>
            ))}
            {!recentUploads.length && (
              <div style={{ padding: 32, textAlign: "center", fontSize: 12, color: "#6D837B" }}>No uploads yet</div>
            )}
          </div>
        </div>
      </section>

      {/* Transaction Chart and Table */}
      <section style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 20 }}>
        {/* Revenue Chart */}
        <div className="elevated-panel p-5 animate-fade-in-scale" style={{ animationDelay: "0.5s" }}>
          <h2 style={{ fontSize: 14, fontWeight: 500, color: "#0D3B38", margin: 0, marginBottom: 4 }}>Transaction Amount Trend</h2>
          <p style={{ fontSize: 12, color: "#6D837B", margin: 0, marginBottom: 16 }}>Amount by transaction date</p>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={transactionTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EDF1EC" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6D837B" }} />
                <YAxis tick={{ fontSize: 11, fill: "#6D837B" }} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#D9E3DD", background: "#fff" }} />
                <Bar dataKey="amount" fill="#155E58" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Last 10 Transactions Table */}
        <div className="elevated-panel overflow-hidden animate-fade-in-scale" style={{ animationDelay: "0.55s" }}>
          <div style={{
            borderBottomWidth: "0.5px",
            borderBottomColor: "#D9E3DD",
            padding: "16px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <div>
              <h2 style={{ fontSize: 14, fontWeight: 500, color: "#0D3B38", margin: 0 }}>Last 10 Transactions</h2>
              <p style={{ fontSize: 12, color: "#6D837B", margin: 0, marginTop: 2 }}>Most recent uploaded data</p>
            </div>
            <button className="secondary-button">
              <FiDownload size={16} /> Export
            </button>
          </div>
          <div style={{ overflowX: "auto", maxHeight: 360, overflowY: "auto" }}>
            <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#F7F5F0", borderBottomWidth: "0.5px", borderBottomColor: "#D9E3DD" }}>
                  {["Transaction ID", "Date", "Merchant", "Type", "Method", "Amount", "Status"].map(header => (
                    <th key={header} style={{
                      padding: "10px 12px",
                      textAlign: "left",
                      fontSize: 11,
                      fontWeight: 500,
                      textTransform: "uppercase",
                      color: "#6D837B",
                      letterSpacing: "0.06em"
                    }}>
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {transactions.slice(0, 10).map((txn, idx) => (
                  <tr
                    key={`${txn.upload_id}-${txn.row_index}`}
                    style={{
                      borderBottomWidth: "0.5px",
                      borderBottomColor: "#EDF1EC",
                      transition: "background 0.15s ease"
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "#fafcfb"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <td style={{ padding: "10px 12px", fontSize: 11, fontFamily: "monospace", fontWeight: 500, color: "#1E8278" }}>
                      {txn.transaction_id || `Row ${txn.row_index}`}
                    </td>
                    <td style={{ padding: "10px 12px", color: "#6D837B" }}>
                      {formatDate(txn.transaction_date)}
                    </td>
                    <td style={{ padding: "10px 12px", color: "#0D3B38" }}>{txn.merchant_name || "-"}</td>
                    <td style={{ padding: "10px 12px", color: "#6D837B" }}>{txn.transaction_type || "-"}</td>
                    <td style={{ padding: "10px 12px", color: "#6D837B" }}>{txn.payment_method || "-"}</td>
                    <td style={{ padding: "10px 12px", fontFamily: "monospace", fontWeight: 500, color: "#0D3B38" }}>
                      {formatMoney(txn.amount)}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <StatusPill status={String(txn.status || "pending").toLowerCase()} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!transactions.length && (
              <div style={{ padding: 32, textAlign: "center", fontSize: 12, color: "#6D837B" }}>
                No transactions in the latest upload
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("en-IN");
}

function KpiCard({ icon: Icon, label, value, delta, tone }) {
  return (
    <div className="elevated-panel p-4 animate-stagger-in-1" style={{
      animationDelay: "0.1s",
      transition: "all 0.15s ease"
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.08)";
      e.currentTarget.style.transform = "translateY(-4px)";
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.boxShadow = "none";
      e.currentTarget.style.transform = "translateY(0)";
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{
          fontSize: 11,
          fontWeight: 500,
          textTransform: "uppercase",
          color: "#6D837B",
          letterSpacing: "0.06em"
        }}>
          {label}
        </div>
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 36,
          height: 36,
          borderRadius: 8,
          background: tone + "15",
          color: tone,
          fontSize: 16
        }}>
          <Icon />
        </div>
      </div>
      <div style={{
        marginTop: 12,
        fontSize: 20,
        fontWeight: 500,
        color: "#0D3B38",
        fontFamily: "monospace"
      }}>
        {value}
      </div>
      <div style={{
        marginTop: 8,
        display: "flex",
        alignItems: "center",
        gap: 4,
        fontSize: 11
      }}>
        {delta > 0 && <span style={{ fontWeight: 500, color: "#155E58" }}>+{delta}%</span>}
        {delta < 0 && <span style={{ fontWeight: 500, color: "#a32d2d" }}>{delta}%</span>}
        {delta === 0 && <FiXCircle style={{ fontSize: 12, color: "#854f0b" }} />}
        <span style={{ color: "#6D837B" }}>{delta === 0 ? "in queue now" : "vs last week"}</span>
      </div>
    </div>
  );
}

function AmountTile({ label, value, bg, color }) {
  return (
    <div style={{
      borderWidth: "0.5px",
      borderColor: color + "30",
      background: bg,
      borderRadius: 12,
      padding: 16,
      transition: "all 0.15s ease"
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.boxShadow = "0 1px 3px rgba(0, 0, 0, 0.08)";
      e.currentTarget.style.transform = "translateY(-2px)";
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.boxShadow = "none";
      e.currentTarget.style.transform = "translateY(0)";
    }}>
      <div style={{
        fontSize: 11,
        fontWeight: 500,
        textTransform: "uppercase",
        color: color,
        letterSpacing: "0.06em"
      }}>
        {label}
      </div>
      <div style={{
        marginTop: 12,
        fontSize: 18,
        fontWeight: 500,
        color: "#0D3B38",
        fontFamily: "monospace"
      }}>
        ₹{Number(value || 0).toLocaleString("en-IN")}
      </div>
    </div>
  );
}

function StatusPill({ status }) {
  const configs = {
    "approved": { bg: "#E7F5F1", color: "#155E58" },
    "pending": { bg: "#faeeda", color: "#854f0b" },
    "declined": { bg: "#fcebeb", color: "#a32d2d" },
    "failed": { bg: "#fcebeb", color: "#a32d2d" }
  };
  const config = configs[status] || { bg: "#E7F5F1", color: "#6D837B" };

  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "4px 8px",
      borderRadius: 4,
      fontSize: 11,
      fontWeight: 500,
      background: config.bg,
      color: config.color
    }}>
      <span style={{
        display: "inline-block",
        width: 4,
        height: 4,
        borderRadius: "50%",
        background: config.color
      }} />
      {status}
    </span>
  );
}

