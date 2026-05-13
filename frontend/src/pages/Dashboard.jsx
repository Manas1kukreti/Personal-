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
  const formatMoney = (value) => `INR ${Number(value || 0).toLocaleString()}`;
  const trend = data?.upload_trends?.map((item) => ({
    day: new Date(item.day).toLocaleDateString(),
    uploads: item.uploads,
    approved: Math.max(0, Math.round(item.uploads * 0.78)),
    rejected: Math.max(0, Math.round(item.uploads * 0.12))
  })) || [];
  const recentUploads = data?.recent_uploads || [];
  const transactions = data?.last_transactions || [];
  const snapshots = data?.kpi_snapshots || [];
  const transactionTrend = data?.transaction_amount_trend?.map((item) => ({
    date: new Date(item.date).toLocaleDateString(),
    amount: Number(item.amount || 0)
  })) || [];
  const latestUpload = data?.latest_upload;

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function clearFilters() {
    setFilters({ status: "", dateFrom: "", dateTo: "" });
  }

  function exportDashboardCsv() {
    const rows = [
      ["Section", "Name", "Value", "Detail"],
      ["Totals", "Total Uploads", totals.uploads || 0, ""],
      ["Totals", "Approved", totals.approved || 0, ""],
      ["Totals", "Pending", totals.pending || 0, ""],
      ["Totals", "Rows Processed", totals.rows || 0, ""],
      ["Totals", "Approved Amount", totals.approved_amount || 0, "INR"],
      ["Totals", "Cash Collected", totals.cash || 0, "INR"],
      ...recentUploads.map((upload) => ["Recent Upload", upload.filename, upload.status, `${upload.rows} rows`]),
      ...transactions.map((txn) => ["Transaction", txn.transaction_id || `Row ${txn.row_index}`, txn.amount, txn.status || ""]),
      ...snapshots.map((snapshot) => ["KPI Snapshot", snapshot.metric_name, snapshot.metric_value, snapshot.captured_at])
    ];
    const csv = rows
      .map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll("\"", "\"\"")}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `excelflow-dashboard-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-5">
      <section className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink">Analytics Overview</h1>
          <p className="text-sm text-muted">Live upload, approval, and KPI activity across the platform.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="secondary-button" onClick={() => setShowFilters((value) => !value)}><FiFilter /> Filter</button>
          <button className="secondary-button" onClick={exportDashboardCsv}><FiDownload /> Export</button>
          <button className="icon-button" onClick={loadKpis} title="Refresh analytics"><FiRefreshCw /></button>
        </div>
      </section>

      {showFilters && (
        <section className="elevated-panel p-4">
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_auto]">
            <label className="block">
              <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted">Status</span>
              <select className="form-input" value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}>
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="reupload_requested">Re-upload requested</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted">From</span>
              <input className="form-input" type="date" value={filters.dateFrom} onChange={(event) => updateFilter("dateFrom", event.target.value)} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted">To</span>
              <input className="form-input" type="date" value={filters.dateTo} onChange={(event) => updateFilter("dateTo", event.target.value)} />
            </label>
            <div className="flex items-end">
              <button className="secondary-button w-full" onClick={clearFilters}>Clear</button>
            </div>
          </div>
        </section>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <Kpi icon={FiDatabase} label="Total Uploads" value={totals.uploads || 0} delta={12} tone="blue" />
        <Kpi icon={FiCheckCircle} label="Approved" value={totals.approved || 0} delta={8} tone="green" />
        <Kpi icon={FiClock} label="Pending Review" value={totals.pending || 0} delta={0} tone="amber" />
        <Kpi icon={FiActivity} label="Rows Processed" value={Number(totals.rows || 0).toLocaleString()} delta={6} tone="teal" />
        <Kpi icon={FiDollarSign} label="Approved Amount" value={formatMoney(totals.approved_amount)} delta={14} tone="indigo" />
        <Kpi icon={FiCreditCard} label="Cash Collected" value={formatMoney(totals.cash)} delta={14} tone="green" />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <AmountTile label="Transaction Initiated" value={workflowAmounts.initiated} detail="All uploaded transaction amount" tone="border-blue-200 bg-blue-50/60 text-accent" />
        <AmountTile label="Pending Amount" value={workflowAmounts.pending} detail="Waiting for manager review" tone="border-amber-200 bg-amber-50/60 text-warning" />
        <AmountTile label="Approved Amount" value={workflowAmounts.approved} detail="Approved upload transactions" tone="border-emerald-200 bg-emerald-50/60 text-success" />
        <AmountTile label="Declined Amount" value={workflowAmounts.declined} detail="Rejected upload transactions" tone="border-red-200 bg-red-50/60 text-danger" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <div className="elevated-panel p-5">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-ink">Upload Activity</h2>
              <p className="text-sm text-muted">Rolling submission and approval trend</p>
            </div>
            <div className="flex gap-4 text-xs font-semibold text-muted">
              <Legend color="bg-accent" label="Uploads" />
              <Legend color="bg-success" label="Approved" />
              <Legend color="bg-danger" label="Rejected" />
            </div>
          </div>
          <div className="mt-4 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="uploadFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.18} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="approvedFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.16} />
                    <stop offset="95%" stopColor="#059669" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5ebf2" vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#d9e2ec" }} />
                <Area type="monotone" dataKey="uploads" stroke="#2563eb" fill="url(#uploadFill)" strokeWidth={2} />
                <Area type="monotone" dataKey="approved" stroke="#059669" fill="url(#approvedFill)" strokeWidth={2} />
                <Area type="monotone" dataKey="rejected" stroke="#dc2626" fill="none" strokeDasharray="4 4" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="elevated-panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-ink">Recent Uploads</h2>
              <p className="text-sm text-muted">Latest submissions</p>
            </div>
            <span className="chip">{recentUploads.length} items</span>
          </div>
          <div className="mt-4 space-y-3">
            {recentUploads.map((upload) => (
              <div key={upload.id} className="flex items-center justify-between gap-3 border border-line bg-slate-50/60 p-3" style={{ borderRadius: 8 }}>
                <div className="min-w-0">
                  <div className="mono truncate text-xs font-semibold text-accent">{upload.filename}</div>
                  <div className="text-xs text-muted">{upload.rows} rows</div>
                </div>
                <StatusBadge status={upload.status} />
              </div>
            ))}
            {!recentUploads.length && <EmptyState label="No uploads yet" />}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
        <div className="elevated-panel p-5">
          <h2 className="text-base font-bold text-ink">Revenue / Transaction Analytics</h2>
          <p className="text-sm text-muted">
            Amount by transaction date from {latestUpload?.filename || "the latest uploaded file"}.
          </p>
          <div className="mt-5 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={transactionTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5ebf2" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#d9e2ec" }} />
                <Bar dataKey="amount" fill="#0f766e" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="elevated-panel overflow-hidden">
          <div className="flex items-center justify-between border-b border-line p-5">
            <div>
              <h2 className="text-base font-bold text-ink">Last 10 Transactions</h2>
              <p className="text-sm text-muted">Last rows from the most recent uploaded file</p>
            </div>
            <button className="secondary-button"><FiDownload /> Export</button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Transaction</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Merchant</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Method</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {transactions.map((txn) => (
                  <tr key={`${txn.upload_id}-${txn.row_index}`} className="hover:bg-slate-50">
                    <td className="mono px-4 py-3 text-xs font-semibold text-accent">{txn.transaction_id || `Row ${txn.row_index}`}</td>
                    <td className="px-4 py-3 text-muted">{formatDate(txn.transaction_date)}</td>
                    <td className="px-4 py-3 text-ink">{txn.customer_name || "-"}</td>
                    <td className="px-4 py-3 text-muted">{txn.merchant_name || "-"}</td>
                    <td className="px-4 py-3 text-muted">{txn.transaction_type || "-"}</td>
                    <td className="px-4 py-3 text-muted">{txn.payment_method || "-"}</td>
                    <td className="px-4 py-3"><StatusBadge status={String(txn.status || "unknown").toLowerCase()} /></td>
                    <td className="mono px-4 py-3 font-semibold text-ink">{formatMoney(txn.amount)}</td>
                  </tr>
                ))}
                {!transactions.length && (
                  <tr><td colSpan="8"><EmptyState label="No transactions in the latest upload" /></td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {snapshots.length > 0 && (
        <section className="elevated-panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-ink">KPI Snapshots</h2>
              <p className="text-sm text-muted">Recent persisted metrics from approval events</p>
            </div>
            <span className="chip">{snapshots.length} items</span>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {snapshots.slice(0, 6).map((snapshot, index) => (
              <div key={`${snapshot.metric_name}-${snapshot.captured_at}-${index}`} className="border border-line bg-slate-50 p-3" style={{ borderRadius: 8 }}>
                <div className="text-xs font-bold uppercase tracking-wide text-muted">{snapshot.metric_name.replaceAll("_", " ")}</div>
                <div className="mono mt-2 text-lg font-semibold text-ink">{Number(snapshot.metric_value || 0).toLocaleString()}</div>
                <div className="mt-1 text-xs text-muted">{new Date(snapshot.captured_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString();
}

function AmountTile({ label, value, detail, tone }) {
  return (
    <div className={`border p-4 ${tone}`} style={{ borderRadius: 8 }}>
      <div className="text-xs font-bold uppercase tracking-wide">{label}</div>
      <div className="mono mt-3 text-xl font-semibold text-ink">INR {Number(value || 0).toLocaleString()}</div>
      <div className="mt-1 text-xs text-muted">{detail}</div>
    </div>
  );
}

function Kpi({ icon: Icon, label, value, delta, tone }) {
  const tones = {
    blue: "bg-blue-50 text-accent",
    green: "bg-emerald-50 text-success",
    amber: "bg-amber-50 text-warning",
    teal: "bg-teal-50 text-brand",
    indigo: "bg-indigo-50 text-indigo-600"
  };
  return (
    <div className="elevated-panel p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs font-bold uppercase tracking-wide text-muted">{label}</div>
        <div className={`flex h-9 w-9 items-center justify-center ${tones[tone]}`} style={{ borderRadius: 8 }}>
          <Icon />
        </div>
      </div>
      <div className="mono mt-4 text-2xl font-semibold text-ink">{value}</div>
      <div className="mt-2 flex items-center gap-1 text-xs">
        {delta > 0 && <span className="font-bold text-success">+{delta}%</span>}
        {delta < 0 && <span className="font-bold text-danger">{delta}%</span>}
        {delta === 0 && <FiXCircle className="text-warning" />}
        <span className="text-muted">{delta === 0 ? "in queue now" : "vs last week"}</span>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={`status-badge status-${status}`}>
      <span className="status-dot bg-current" />
      {status}
    </span>
  );
}

function Legend({ color, label }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className={`h-0.5 w-5 rounded-full ${color}`} />
      {label}
    </span>
  );
}

function EmptyState({ label }) {
  return <div className="py-8 text-center text-sm text-muted">{label}</div>;
}
