import React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FiCheck, FiChevronRight, FiClock, FiRefreshCw, FiRotateCcw, FiSearch, FiX } from "react-icons/fi";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import CommentThread from "../components/CommentThread.jsx";
import DataTable from "../components/DataTable.jsx";
import ProgressMilestones from "../components/ProgressMilestones.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";

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

  const loadQueue = useCallback(async () => {
    setQueueLoading(true);
    setQueueError("");
    try {
      const response = await api.get("/uploads");
      setUploads(response.data);
    } catch (err) {
      setQueueError(err.response?.data?.detail || "Unable to load approvals. Please try again.");
    } finally {
      setQueueLoading(false);
    }
  }, []);

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
          setTokenError(
            err.response?.data?.detail || "This review link has expired or is invalid."
          );
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
    <div className="app-page" style={{ padding: "24px 28px", background: "#F7F5F0", minHeight: "100vh", display: "grid", gridTemplateColumns: "1fr" }}>
      {tokenError && (
        <div style={{
          background: "#fcebeb",
          border: "0.5px solid #a32d2d",
          borderRadius: 8,
          padding: "12px 16px",
          color: "#a32d2d",
          fontSize: 13,
          marginBottom: 16,
          display: "flex",
          alignItems: "center",
          gap: 8
        }}>
          <FiX size={16} style={{ flexShrink: 0 }} />
          {tokenError}
        </div>
      )}
      {/* Header Section */}
      <section className="flex flex-wrap items-center justify-between gap-4 animate-slide-in-top" style={{ marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: "#0a3d2e", margin: 0, marginBottom: 4 }}>Manager Dashboard</h1>
          <p style={{ fontSize: 13, color: "#6b9080", margin: 0 }}>Review pending uploads and manage approval decisions.</p>
        </div>
        <button className="secondary-button" onClick={loadQueue} disabled={queueLoading}>
          <FiRefreshCw size={16} /> {queueLoading ? "Refreshing..." : "Refresh queue"}
        </button>
      </section>

      {/* KPI Cards */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16, marginBottom: 24 }}>
        <StatCard label="Pending Review" value={pending} tone="#854f0b" />
        <StatCard label="Approved" value={approved} tone="#155E58" />
        <StatCard label="Declined" value={declined} tone="#a32d2d" />
        <StatCard label="Total Processed" value={uploads.length} tone="#1E8278" />
      </section>

      {/* Main Content - Queue and Review */}
      <section className="manager-review-layout" style={{ display: "grid", gridTemplateColumns: "minmax(280px, 380px) 1fr", gap: 20, minWidth: 0 }}>
        {/* LEFT: Approval Queue */}
        <div className="elevated-panel overflow-hidden animate-slide-in-left" style={{ animationDelay: "0.1s" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottomWidth: "0.5px",
            borderBottomColor: "#D9E3DD",
            padding: "16px 20px"
          }}>
            <div>
              <h2 style={{ fontSize: 14, fontWeight: 500, color: "#0a3d2e", margin: 0 }}>Approval Queue</h2>
              <p style={{ fontSize: 12, color: "#6b9080", margin: 0, marginTop: 2 }}>New uploads arrive here in real time.</p>
            </div>
            {pending > 0 && (
              <span style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 24,
                height: 24,
                borderRadius: "50%",
                background: "#faeeda",
                color: "#854f0b",
                fontSize: 11,
                fontWeight: 500
              }}>
                {pending}
              </span>
            )}
          </div>
          <div className="queue-toolbar">
            <label className="upload-search">
              <FiSearch />
              <input value={queueSearch} onChange={(event) => setQueueSearch(event.target.value)} placeholder="Search queue" />
            </label>
            <select className="form-input" value={queueStatus} onChange={(event) => setQueueStatus(event.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="declined">Declined</option>
              <option value="reupload_requested">Re-upload</option>
            </select>
          </div>

          <div style={{ divideY: "1px", divideColor: "#D9E3DD" }}>
            {queueError && (
              <div style={{
                padding: 16,
                fontSize: 13,
                color: "#a32d2d",
                background: "#fcebeb",
                borderBottom: "0.5px solid #f2c7c7"
              }}>
                {queueError}
              </div>
            )}
            {queueLoading && !queueItems.length && (
              <div style={{
                padding: 32,
                textAlign: "center",
                fontSize: 13,
                color: "#6b9080"
              }}>
                Loading approvals...
              </div>
            )}
            {!queueLoading && queueItems.map((upload) => (
              <button
                key={upload.id}
                onClick={() => openUpload(upload)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  borderLeft: selected?.upload_id === upload.id ? "4px solid #155E58" : "4px solid transparent",
                  background: selected?.upload_id === upload.id ? "#E7F5F1" : "#fff",
                  padding: 16,
                  transition: "all 0.15s ease",
                  border: "none",
                  cursor: "pointer",
                  borderBottomWidth: "0.5px",
                  borderBottomColor: "#eef4f2"
                }}
                onMouseEnter={(e) => {
                  if (selected?.upload_id !== upload.id) e.currentTarget.style.background = "#fafcfb";
                }}
                onMouseLeave={(e) => {
                  if (selected?.upload_id !== upload.id) e.currentTarget.style.background = "#fff";
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{
                      fontSize: 11,
                      fontWeight: 500,
                      color: "#1E8278",
                      fontFamily: "monospace",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap"
                    }}>
                      {upload.filename}
                    </div>
                    <div style={{ marginTop: 4, fontSize: 11, color: "#6b9080" }}>
                      {upload.uploader_name || "Employee"} · {upload.total_rows} rows · {upload.total_columns} cols
                    </div>
                    <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#8ab8aa" }}>
                      <FiClock size={12} /> {new Date(upload.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, shrinkFlex: 0 }}>
                    <StatusBadge status={upload.status} />
                    <FiChevronRight size={16} style={{ color: "#D9E3DD" }} />
                  </div>
                </div>
              </button>
            ))}
            {!queueLoading && !queueItems.length && !queueError && (
              <div style={{
                padding: 32,
                textAlign: "center",
                fontSize: 13,
                color: "#6b9080"
              }}>
                No uploads found.
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: Review Section */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Review Panel */}
          <div className="elevated-panel p-5 animate-slide-in-right" style={{ animationDelay: "0.15s" }}>
            <h2 style={{ fontSize: 14, fontWeight: 500, color: "#0a3d2e", margin: 0, marginBottom: 16 }}>Review Upload</h2>
            
            {selected ? (
              <div style={{ space: 16, display: "grid", gap: 16 }}>
                {/* File Info Grid */}
                <div className="manager-info-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                  <InfoTile label="File" value={selected.filename} />
                  <InfoTile label="Rows" value={selected.total_rows} />
                  <InfoTile label="Status" value={selected.status} />
                </div>

                {/* Milestones */}
                <ProgressMilestones status={selected.status} createdAt={selected.created_at} reviewedAt={selected.reviewed_at} />

                {selected.version_history?.length > 1 && (
                  <div className="version-tabs">
                    {selected.version_history.map((version) => (
                      <button
                        key={version.id}
                        className={version.id === selected.upload_id ? "is-active" : ""}
                        onClick={() => openVersion(version.id)}
                      >
                        v{version.version_number}
                        <span>{version.status}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Columns */}
                <div>
                  <div style={{ fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#3a6655", marginBottom: 8, letterSpacing: "0.06em" }}>
                    Extracted Columns
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {selected.columns.map((column) => (
                      <span key={column} className="chip">
                        {column}
                      </span>
                    ))}
                  </div>
                </div>

                <CommentThread
                  submissionId={selected.upload_id}
                  title="Review conversation"
                  onCommentsChange={handleThreadCommentsChange}
                />

                {!hasManagerThreadFeedback && selected.status === "pending" && (
                  <div className="comment-action-hint">
                    Add your feedback in the conversation thread before rejecting or requesting re-upload.
                  </div>
                )}

                {/* Action Buttons */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                  <button
                    onClick={() => review("reject")}
                    disabled={selected.status !== "pending" || !!acting || !hasManagerThreadFeedback}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "9px 16px",
                      borderRadius: 9,
                      border: "1px solid #a32d2d",
                      background: "transparent",
                      color: "#a32d2d",
                      fontSize: 13,
                      fontWeight: 500,
                      cursor: selected.status === "pending" && !acting && hasManagerThreadFeedback ? "pointer" : "not-allowed",
                      transition: "all 0.15s ease",
                      opacity: selected.status === "pending" && !acting && hasManagerThreadFeedback ? 1 : 0.5
                    }}
                    onMouseEnter={(e) => {
                      if (selected.status === "pending" && !acting && hasManagerThreadFeedback) {
                        e.target.style.background = "#fcebeb";
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = "transparent";
                    }}
                  >
                    <FiX size={16} /> {acting === "reject" ? "Rejecting..." : "Reject"}
                  </button>

                  <button
                    onClick={() => review("reupload")}
                    disabled={selected.status !== "pending" || !!acting || !hasManagerThreadFeedback}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "9px 16px",
                      borderRadius: 9,
                      border: "1px solid #1E8278",
                      background: "transparent",
                      color: "#1E8278",
                      fontSize: 13,
                      fontWeight: 500,
                      cursor: selected.status === "pending" && !acting && hasManagerThreadFeedback ? "pointer" : "not-allowed",
                      transition: "all 0.15s ease",
                      opacity: selected.status === "pending" && !acting && hasManagerThreadFeedback ? 1 : 0.5
                    }}
                    onMouseEnter={(e) => {
                      if (selected.status === "pending" && !acting && hasManagerThreadFeedback) {
                        e.target.style.background = "#E7F5F1";
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = "transparent";
                    }}
                  >
                    <FiRotateCcw size={16} /> {acting === "reupload" ? "Requesting..." : "Request Re-upload"}
                  </button>

                  <button
                    onClick={() => review("approve")}
                    disabled={selected.status !== "pending" || !!acting}
                    className="primary-button"
                    style={{ minWidth: 160 }}
                  >
                    <FiCheck size={16} /> {acting === "approve" ? "Approving..." : "Approve Upload"}
                  </button>
                </div>
              </div>
            ) : (
              <div style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: 192,
                borderWidth: "0.5px",
                borderColor: "#D9E3DD",
                background: "#FBFAF6",
                fontSize: 13,
                color: "#6b9080",
                borderRadius: 8
              }}>
                Select an upload to review
              </div>
            )}
          </div>

          {/* Data Table */}
          {selected && <DataTable columns={selected.columns} rows={selected.preview_rows} />}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value, tone }) {
  return (
    <div className="elevated-panel p-4 animate-stagger-in-1" style={{ animationDelay: "0.1s" }}>
      <div style={{ fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#6b9080", letterSpacing: "0.06em" }}>
        {label}
      </div>
      <div style={{
        fontSize: 24,
        fontWeight: 500,
        color: tone,
        marginTop: 12,
        fontFamily: "monospace"
      }}>
        {value}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const configs = {
    "pending": { bg: "#faeeda", color: "#854f0b" },
    "approved": { bg: "#E7F5F1", color: "#155E58" },
    "declined": { bg: "#fcebeb", color: "#a32d2d" },
    "reupload_requested": { bg: "#EEF8F5", color: "#277A73" }
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

function InfoTile({ label, value }) {
  return (
    <div style={{
      borderWidth: "0.5px",
      borderColor: "#D9E3DD",
      background: "#FBFAF6",
      borderRadius: 8,
      padding: 12
    }}>
      <div style={{
        fontSize: 11,
        fontWeight: 500,
        textTransform: "uppercase",
        color: "#6b9080",
        letterSpacing: "0.06em",
        marginBottom: 4
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 13,
        fontWeight: 500,
        color: "#0a3d2e",
        fontFamily: "monospace",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap"
      }}>
        {value}
      </div>
    </div>
  );
}
