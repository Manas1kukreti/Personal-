import React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FiCheck, FiChevronRight, FiClock, FiRefreshCw, FiRotateCcw, FiSearch, FiShield, FiX } from "react-icons/fi";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import CommentThread from "../components/CommentThread.jsx";
import DataTable from "../components/DataTable.jsx";
import ProgressMilestones from "../components/ProgressMilestones.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";

const DATE_PRESETS = [
  { key: "all", label: "All Time" },
  { key: "one_month", label: "1 Month" },
  { key: "three_months", label: "3 Months" },
  { key: "six_months", label: "6 Months" },
  { key: "twelve_months", label: "12 Months" },
  { key: "custom", label: "Custom Range" }
];

export default function ManagerDashboard() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const [uploads, setUploads] = useState([]);
  const [selected, setSelected] = useState(null);
  const [threadComments, setThreadComments] = useState([]);
  const [acting, setActing] = useState("");
  const [openedDeepLink, setOpenedDeepLink] = useState("");
  const [tokenError, setTokenError] = useState(null);
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueError, setQueueError] = useState("");
  const [queueSearch, setQueueSearch] = useState("");
  const [queueStatus, setQueueStatus] = useState("");
  const [datePreset, setDatePreset] = useState("all");
  const [dateFilters, setDateFilters] = useState({ dateFrom: "", dateTo: "" });

  const loadQueue = useCallback(async () => {
    setQueueLoading(true);
    setQueueError("");
    try {
      const params = new URLSearchParams();
      if (dateFilters.dateFrom) params.set("date_from", `${dateFilters.dateFrom}T00:00:00`);
      if (dateFilters.dateTo) params.set("date_to", `${dateFilters.dateTo}T23:59:59`);
      const response = await api.get(`/uploads${params.toString() ? `?${params.toString()}` : ""}`);
      setUploads(response.data);
    } catch (err) {
      setQueueError(err.response?.data?.detail || "Unable to load approvals. Please try again.");
    } finally {
      setQueueLoading(false);
    }
  }, [dateFilters]);

  useEffect(() => {
    if (user?.role !== "manager") return;
    loadQueue();
  }, [loadQueue, user?.id, user?.role]);

  useEffect(() => {
    const token = searchParams.get("token");
    if (!user?.id) return;

    if (token) {
      api.get(`/approvals/verify-token?token=${token}`)
        .then((res) => {
          const intendedManagerId = res.data.manager_id;
          if (intendedManagerId && user?.id !== intendedManagerId) {
            return logout().finally(() => {
              navigate("/login", { replace: true, state: { from: location } });
            });
          }

          const submissionId = res.data.submission_id;
          if (openedDeepLink === submissionId) return;
          return Promise.all([
            api.get(`/uploads/${submissionId}`),
            loadQueue()
          ]).then(([r]) => {
            setSelected(r.data);
            setThreadComments([]);
            setOpenedDeepLink(submissionId);
          });
        })
        .catch((err) => {
          setTokenError(err.response?.data?.detail || "This review link has expired or is invalid.");
        });
      return;
    }

    const submissionId = searchParams.get("submission_id");
    if (!submissionId || openedDeepLink === submissionId) return;

    async function openDeepLink() {
      const response = await api.get(`/uploads/${submissionId}`);
      setSelected(response.data);
      setThreadComments([]);
      setOpenedDeepLink(submissionId);
    }

    openDeepLink().catch(() => setOpenedDeepLink(submissionId));
  }, [loadQueue, openedDeepLink, searchParams, user?.id]);

  useWebSocket("manager", useCallback((event) => {
    if (["new_upload", "upload.new", "upload_reviewed", "approval.decision"].includes(event.event)) loadQueue();
  }, [loadQueue]));

  async function openUpload(upload) {
    const response = await api.get(`/uploads/${upload.id}`);
    setSelected(response.data);
    setThreadComments([]);
  }

  async function openVersion(versionId) {
    const response = await api.get(`/uploads/${versionId}`);
    setSelected(response.data);
    setThreadComments([]);
  }

  function selectDatePreset(preset) {
    setDatePreset(preset);
    if (preset !== "custom") {
      setDateFilters(datesForPreset(preset));
    }
  }

  function updateDateFilter(name, value) {
    setDatePreset("custom");
    setDateFilters((current) => ({ ...current, [name]: value }));
  }

  const handleThreadCommentsChange = useCallback((comments) => {
    setThreadComments(comments);
  }, []);

  async function review(decision) {
    if (!selected) return;
    setActing(decision);
    try {
      const endpoint = decision === "approve" ? "approve" : decision === "reupload" ? "request-reupload" : "reject";
      await api.post(`/approvals/${selected.upload_id}/${endpoint}`, {});
      setSelected(null);
      setThreadComments([]);
      loadQueue();
    } finally {
      setActing("");
    }
  }

  const pending = uploads.filter((upload) => upload.status === "pending").length;
  const approved = uploads.filter((upload) => upload.status === "approved").length;
  const declined = uploads.filter((upload) => upload.status === "declined").length;
  const hasManagerThreadFeedback = threadComments.some((comment) => comment.user_id === user?.id);

  const queueItems = useMemo(() => {
    const search = queueSearch.trim().toLowerCase();
    return uploads.filter((upload) => {
      const matchesStatus = !queueStatus || upload.status === queueStatus;
      const matchesSearch = !search || [upload.filename, upload.uploader_name, upload.status]
        .some((value) => String(value || "").toLowerCase().includes(search));
      return matchesStatus && matchesSearch;
    });
  }, [uploads, queueSearch, queueStatus]);

  return (
    <div className="app-page approvals-page">
      {tokenError && (
        <div className="approvals-banner approvals-banner-error">
          <FiX size={16} />
          <span>{tokenError}</span>
        </div>
      )}

      <section className="approvals-header">
        <div>
          <h1>Approval Workspace</h1>
          <p>Review inbound uploads, compare versions, and record approval decisions with clear audit context.</p>
        </div>
        <button className="secondary-button approvals-refresh" onClick={loadQueue} disabled={queueLoading}>
          <FiRefreshCw size={16} />
          {queueLoading ? "Refreshing..." : "Refresh queue"}
        </button>
      </section>

      <section className="approvals-kpi-grid">
        <ApprovalStat label="Pending Review" value={pending} tone="warning" />
        <ApprovalStat label="Approved" value={approved} tone="success" />
        <ApprovalStat label="Declined" value={declined} tone="danger" />
        <ApprovalStat label="Total Processed" value={uploads.length} tone="brand" />
      </section>

      <section className="approvals-layout">
        <aside className="elevated-panel approvals-queue-panel">
          <div className="approvals-panel-head approvals-queue-head">
            <div>
              <h2>Approval Queue</h2>
              <p>New uploads arrive here in real time.</p>
            </div>
            {pending > 0 && <span className="approvals-count-pill">{pending}</span>}
          </div>

          <div className="approvals-queue-controls">
            <label className="upload-search">
              <FiSearch />
              <input value={queueSearch} onChange={(event) => setQueueSearch(event.target.value)} placeholder="Search queue" />
            </label>
            <div className="approvals-queue-filters">
              <select className="form-input" value={queueStatus} onChange={(event) => setQueueStatus(event.target.value)}>
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="declined">Declined</option>
                <option value="reupload_requested">Re-upload</option>
              </select>
              <select className="form-input" value={datePreset} onChange={(event) => selectDatePreset(event.target.value)} aria-label="Transaction date range">
                {DATE_PRESETS.map((preset) => (
                  <option key={preset.key} value={preset.key}>{preset.label}</option>
                ))}
              </select>
            </div>
            {datePreset === "custom" && (
              <div className="approvals-date-range">
                <input className="form-input" type="date" value={dateFilters.dateFrom} onChange={(event) => updateDateFilter("dateFrom", event.target.value)} />
                <input className="form-input" type="date" value={dateFilters.dateTo} onChange={(event) => updateDateFilter("dateTo", event.target.value)} />
              </div>
            )}
          </div>

          <div className="approvals-queue-list">
            {queueError && <div className="approvals-banner approvals-banner-error">{queueError}</div>}
            {queueLoading && !queueItems.length && <div className="approvals-empty">Loading approvals...</div>}
            {!queueLoading && queueItems.map((upload) => {
              const active = selected?.upload_id === upload.id;
              return (
                <button
                  key={upload.id}
                  className={`approvals-queue-card${active ? " is-active" : ""}`}
                  onClick={() => openUpload(upload)}
                  type="button"
                >
                  <div className="approvals-queue-card__top">
                    <div className="approvals-queue-card__file">{upload.filename}</div>
                    <StatusBadge status={upload.status} />
                  </div>
                  <div className="approvals-queue-card__meta">
                    <span>{upload.uploader_name || "Employee"}</span>
                    <span>{upload.total_rows} rows</span>
                    <span>{upload.total_columns} cols</span>
                  </div>
                  <div className="approvals-queue-card__time">
                    <FiClock size={12} />
                    <span>{new Date(upload.created_at).toLocaleString("en-IN")}</span>
                    <FiChevronRight size={14} />
                  </div>
                </button>
              );
            })}
            {!queueLoading && !queueItems.length && !queueError && <div className="approvals-empty">No uploads found.</div>}
          </div>
        </aside>

        <div className="approvals-detail-column">
          <section className="elevated-panel approvals-review-panel">
            <div className="approvals-panel-head">
              <div>
                <h2>Review Upload</h2>
                <p>Inspect file metadata, version history, extracted columns, and reviewer discussion.</p>
              </div>
            </div>

            {selected ? (
              <div className="approvals-review-stack">
                <div className="approvals-info-grid">
                  <InfoTile label="File" value={selected.filename} />
                  <InfoTile label="Rows" value={selected.total_rows} />
                  <InfoTile label="Status" value={selected.status} />
                </div>

                <div className="approvals-section-shell">
                  <ProgressMilestones status={selected.status} createdAt={selected.created_at} reviewedAt={selected.reviewed_at} />
                </div>

                {selected.version_history?.length > 1 && (
                  <div className="approvals-section-shell">
                    <div className="approvals-section-label">Version history</div>
                    <div className="version-tabs">
                      {selected.version_history.map((version) => (
                        <button
                          key={version.id}
                          className={version.id === selected.upload_id ? "is-active" : ""}
                          onClick={() => openVersion(version.id)}
                          type="button"
                        >
                          v{version.version_number}
                          <span>{version.status}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="approvals-section-shell">
                  <div className="approvals-section-label">Extracted columns</div>
                  <div className="approvals-chip-wrap">
                    {selected.columns.map((column) => (
                      <span key={column} className="chip">{column}</span>
                    ))}
                  </div>
                </div>

                <CommentThread submissionId={selected.upload_id} title="Review conversation" onCommentsChange={handleThreadCommentsChange} />

                {!hasManagerThreadFeedback && selected.status === "pending" && (
                  <div className="comment-action-hint">
                    Add your feedback in the conversation thread before rejecting or requesting re-upload.
                  </div>
                )}

                <div className="approvals-action-row">
                  <button
                    className="approvals-action approvals-action-danger"
                    onClick={() => review("reject")}
                    disabled={selected.status !== "pending" || !!acting || !hasManagerThreadFeedback}
                    type="button"
                  >
                    <FiX size={16} />
                    {acting === "reject" ? "Rejecting..." : "Reject"}
                  </button>

                  <button
                    className="approvals-action approvals-action-secondary"
                    onClick={() => review("reupload")}
                    disabled={selected.status !== "pending" || !!acting || !hasManagerThreadFeedback}
                    type="button"
                  >
                    <FiRotateCcw size={16} />
                    {acting === "reupload" ? "Requesting..." : "Request Re-upload"}
                  </button>

                  <button
                    className="primary-button approvals-action-primary"
                    onClick={() => review("approve")}
                    disabled={selected.status !== "pending" || !!acting}
                    type="button"
                  >
                    <FiCheck size={16} />
                    {acting === "approve" ? "Approving..." : "Approve Upload"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="approvals-empty approvals-empty-panel">
                <FiShield size={22} />
                <strong>Select an upload to review</strong>
                <span>Your selected submission will show version history, comments, and extracted data here.</span>
              </div>
            )}
          </section>

          {selected && <DataTable columns={selected.columns} rows={selected.preview_rows} />}
        </div>
      </section>
    </div>
  );
}

function ApprovalStat({ label, value, tone }) {
  return (
    <div className={`elevated-panel approvals-stat approvals-stat-${tone}`}>
      <div className="approvals-stat__label">{label}</div>
      <div className="approvals-stat__value">{value}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={`status-badge status-${status}`}>
      <span className="status-dot bg-current" />
      {String(status || "unknown").replaceAll("_", " ")}
    </span>
  );
}

function InfoTile({ label, value }) {
  return (
    <div className="approvals-info-tile">
      <div className="approvals-info-tile__label">{label}</div>
      <div className="approvals-info-tile__value">{value}</div>
    </div>
  );
}

function datesForPreset(preset) {
  const today = new Date();
  const end = toDateInputValue(today);
  if (preset === "one_month") {
    return { dateFrom: toDateInputValue(new Date(today.getFullYear(), today.getMonth() - 1, today.getDate())), dateTo: end };
  }
  if (preset === "three_months") {
    return { dateFrom: toDateInputValue(new Date(today.getFullYear(), today.getMonth() - 3, today.getDate())), dateTo: end };
  }
  if (preset === "six_months") {
    return { dateFrom: toDateInputValue(new Date(today.getFullYear(), today.getMonth() - 6, today.getDate())), dateTo: end };
  }
  if (preset === "twelve_months") {
    return { dateFrom: toDateInputValue(new Date(today.getFullYear(), today.getMonth() - 12, today.getDate())), dateTo: end };
  }
  return { dateFrom: "", dateTo: "" };
}

function toDateInputValue(date) {
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return offsetDate.toISOString().slice(0, 10);
}
