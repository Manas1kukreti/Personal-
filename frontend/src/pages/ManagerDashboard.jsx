import React from "react";
import { useCallback, useEffect, useState } from "react";
import { FiCheck, FiChevronRight, FiClock, FiMessageSquare, FiRefreshCw, FiRotateCcw, FiX } from "react-icons/fi";
import { api } from "../api/client.js";
import DataTable from "../components/DataTable.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";

export default function ManagerDashboard() {
  const [uploads, setUploads] = useState([]);
  const [selected, setSelected] = useState(null);
  const [comment, setComment] = useState("");
  const [acting, setActing] = useState("");

  const loadQueue = useCallback(async () => {
    const response = await api.get("/uploads");
    setUploads(response.data);
  }, []);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  useWebSocket("manager", useCallback((event) => {
    if (["new_upload", "upload.new", "upload_reviewed", "approval.decision"].includes(event.event)) loadQueue();
  }, [loadQueue]));

  async function openUpload(upload) {
    const response = await api.get(`/uploads/${upload.id}`);
    setSelected(response.data);
    setComment("");
  }

  async function review(decision) {
    if (!selected) return;
    setActing(decision);
    try {
      const endpoint = decision === "approve" ? "approve" : decision === "reupload" ? "request-reupload" : "reject";
      await api.post(`/approvals/${selected.upload_id}/${endpoint}`, { comment });
      setSelected(null);
      setComment("");
      loadQueue();
    } finally {
      setActing("");
    }
  }

  const pending = uploads.filter((upload) => upload.status === "pending").length;
  const approved = uploads.filter((upload) => upload.status === "approved").length;
  const rejected = uploads.filter((upload) => upload.status === "rejected").length;

  return (
    <div className="space-y-5">
      <section className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink">Manager Dashboard</h1>
          <p className="text-sm text-muted">Review pending uploads and manage approval decisions.</p>
        </div>
        <button className="secondary-button" onClick={loadQueue}><FiRefreshCw /> Refresh queue</button>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <Stat label="Pending Review" value={pending} tone="text-warning" />
        <Stat label="Approved" value={approved} tone="text-success" />
        <Stat label="Rejected" value={rejected} tone="text-danger" />
        <Stat label="Total Processed" value={uploads.length} tone="text-accent" />
      </section>

      <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
        <section className="elevated-panel overflow-hidden">
          <div className="flex items-center justify-between border-b border-line p-4">
            <div>
              <h2 className="text-base font-bold text-ink">Approval Queue</h2>
              <p className="text-sm text-muted">New uploads arrive here in real time.</p>
            </div>
            {pending > 0 && <span className="status-badge status-pending">{pending}</span>}
          </div>
          <div className="divide-y divide-line">
            {uploads.map((upload) => (
              <button
                key={upload.id}
                className={`w-full border-l-4 p-4 text-left transition hover:bg-slate-50 ${
                  selected?.upload_id === upload.id ? "border-brand bg-teal-50/60" : "border-transparent"
                }`}
                onClick={() => openUpload(upload)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="mono truncate text-xs font-bold text-accent">{upload.filename}</div>
                    <div className="mt-1 text-xs text-muted">
                      {upload.uploader_name || "Employee"} - {upload.total_rows} rows - {upload.total_columns} columns
                    </div>
                    <div className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                      <FiClock /> {new Date(upload.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <StatusBadge status={upload.status} />
                    <FiChevronRight className="text-slate-300" />
                  </div>
                </div>
              </button>
            ))}
            {!uploads.length && <div className="p-8 text-center text-sm text-muted">No uploads found.</div>}
          </div>
        </section>

        <section className="space-y-5">
          <div className="elevated-panel p-5">
            <h2 className="text-base font-bold text-ink">Review Upload</h2>
            {selected ? (
              <div className="mt-4 space-y-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <Tile label="File" value={selected.filename} />
                  <Tile label="Rows" value={selected.total_rows} />
                  <Tile label="Status" value={selected.status} />
                </div>
                <div>
                  <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Extracted Columns</div>
                  <div className="flex flex-wrap gap-2">
                    {selected.columns.map((column) => <span className="chip" key={column}>{column}</span>)}
                  </div>
                </div>
                <label className="block">
                  <span className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted">
                    <FiMessageSquare /> Manager Comment
                  </span>
                  <textarea
                    className="min-h-24 w-full border border-line bg-slate-50 p-3 text-sm text-ink outline-none transition focus:border-brand focus:bg-white"
                    style={{ borderRadius: 8 }}
                    placeholder="Add feedback or notes for the uploader..."
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                  />
                </label>
                <div className="flex flex-wrap gap-3">
                  <button className="secondary-button border-red-200 text-red-700 hover:border-red-500 hover:bg-red-50 hover:text-red-700" disabled={selected.status !== "pending" || !!acting} onClick={() => review("reject")}><FiX /> {acting === "reject" ? "Rejecting..." : "Reject"}</button>
                  <button className="secondary-button border-blue-200 text-accent hover:border-blue-500 hover:bg-blue-50 hover:text-accent" disabled={selected.status !== "pending" || !!acting} onClick={() => review("reupload")}><FiRotateCcw /> {acting === "reupload" ? "Requesting..." : "Request Re-upload"}</button>
                  <button className="primary-button min-w-40" disabled={selected.status !== "pending" || !!acting} onClick={() => review("approve")}><FiCheck /> {acting === "approve" ? "Approving..." : "Approve Upload"}</button>
                </div>
              </div>
            ) : (
              <div className="mt-4 flex min-h-48 items-center justify-center border border-line bg-slate-50 text-sm text-muted" style={{ borderRadius: 8 }}>
                Select an upload to review
              </div>
            )}
          </div>
          {selected && <DataTable columns={selected.columns} rows={selected.preview_rows} />}
        </section>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="elevated-panel p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-muted">{label}</div>
      <div className={`mono mt-2 text-2xl font-semibold ${tone}`}>{value}</div>
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

function Tile({ label, value }) {
  return (
    <div className="border border-line bg-slate-50 p-3" style={{ borderRadius: 8 }}>
      <div className="text-xs font-bold uppercase tracking-wide text-muted">{label}</div>
      <div className="mono mt-1 truncate text-sm font-bold text-ink">{value}</div>
    </div>
  );
}
