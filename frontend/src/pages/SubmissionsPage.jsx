import React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FiArchive, FiDownload, FiFilter, FiMessageSquare, FiSearch, FiUploadCloud } from "react-icons/fi";
import { api } from "../api/client.js";
import CommentThread from "../components/CommentThread.jsx";

const TABS = [
  { label: "All", value: "" },
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "declined" },
];

const PAGE_SIZE = 10;

export default function SubmissionsPage() {
  const reuploadInputRef = useRef(null);
  const [uploads, setUploads] = useState([]);
  const [selectedUpload, setSelectedUpload] = useState(null);
  const [reuploadTarget, setReuploadTarget] = useState(null);
  const [reuploading, setReuploading] = useState("");
  const [reuploadError, setReuploadError] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(1);

  const loadUploads = useCallback(async () => {
    const response = await api.get("/uploads");
    setUploads(response.data);
  }, []);

  useEffect(() => {
    loadUploads().catch(() => setUploads([]));
  }, [loadUploads]);

  useEffect(() => {
    if (!selectedUpload) return;
    const freshUpload = uploads.find((upload) => upload.id === selectedUpload.id);
    if (freshUpload) setSelectedUpload(freshUpload);
  }, [selectedUpload, uploads]);

  // Reset to page 1 whenever filters change
  useEffect(() => {
    setPage(1);
  }, [query, status]);

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();
    return uploads.filter((upload) => {
      const matchesStatus = !status || upload.status === status;
      const matchesSearch =
        !search ||
        [upload.filename, upload.uploader_name, upload.status, upload.id].some((value) =>
          String(value || "").toLowerCase().includes(search)
        );
      return matchesStatus && matchesSearch;
    });
  }, [uploads, query, status]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function getPageNumbers() {
    const pages = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (safePage > 3) pages.push("...");
      for (let i = Math.max(2, safePage - 1); i <= Math.min(totalPages - 1, safePage + 1); i++) {
        pages.push(i);
      }
      if (safePage < totalPages - 2) pages.push("...");
      pages.push(totalPages);
    }
    return pages;
  }

  function exportCsv() {
    const csv = [
      ["Filename", "Status", "Rows", "Columns", "Uploader", "Created At", "Reviewed At"],
      ...filtered.map((upload) => [
        upload.filename,
        upload.status,
        upload.total_rows,
        upload.total_columns,
        upload.uploader_name || "",
        upload.created_at || "",
        upload.reviewed_at || "",
      ]),
    ]
      .map((row) =>
        row.map((cell) => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(",")
      )
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ledgerflow-submissions-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function startReupload(upload) {
    setReuploadTarget(upload);
    setReuploadError("");
    if (reuploadInputRef.current) {
      reuploadInputRef.current.value = "";
      reuploadInputRef.current.click();
    }
  }

  async function submitReupload(file) {
    if (!file || !reuploadTarget) return;
    const form = new FormData();
    form.append("file", file);
    setReuploading(reuploadTarget.id);
    setReuploadError("");
    try {
      await api.post(`/uploads/${reuploadTarget.id}/reupload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setReuploadTarget(null);
      await loadUploads();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setReuploadError(
        typeof detail === "string" ? detail : "Re-upload failed. Please check the file and try again."
      );
    } finally {
      setReuploading("");
    }
  }

  return (
    <div className="lf-submissions-page">
      <input
        ref={reuploadInputRef}
        className="hidden"
        type="file"
        accept=".xlsx,.csv"
        onChange={(event) => submitReupload(event.target.files?.[0])}
      />

      {/* ── Title ── */}
      <h1 className="lf-submissions-title">Submissions</h1>

      {/* ── Tabs ── */}
      <div className="lf-submissions-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            className={`lf-submissions-tab${status === tab.value ? " is-active" : ""}`}
            onClick={() => setStatus(tab.value)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Toolbar ── */}
      <section className="lf-submissions-toolbar">
        <label className="lf-submissions-search">
          <FiSearch size={18} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search submissions..."
          />
        </label>

        <div className="lf-submissions-toolbar__actions">
          <button
            className="lf-submissions-filter-button"
            onClick={() => setShowFilters((value) => !value)}
            type="button"
          >
            <FiFilter size={18} />
            <span>Filter</span>
          </button>
          <button
            className="secondary-button"
            onClick={exportCsv}
            disabled={!filtered.length}
            type="button"
          >
            <FiDownload /> Export
          </button>
        </div>
      </section>

      {showFilters && (
        <section className="lf-submissions-filter-row">
          <select
            className="form-input"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="declined">Declined</option>
            <option value="reupload_requested">Re-upload requested</option>
          </select>
        </section>
      )}

      {reuploadError && <div className="lf-submissions-error">{reuploadError}</div>}

      {/* ── Table ── */}
      <section className="lf-submissions-table-wrap">
        <table className="lf-submissions-table">
          <thead>
            <tr>
              <th className="is-checkbox">
                <input type="checkbox" aria-label="Select all" />
              </th>
              <th>ID</th>
              <th>User</th>
              <th>Type</th>
              <th>Status</th>
              <th>Submitted</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((upload, index) => {
              const parts = inferSubmissionType(upload);
              const timestamp = formatSubmitted(upload.created_at);
              const globalIndex = (safePage - 1) * PAGE_SIZE + index;
              return (
                <tr
                  key={upload.id}
                  className={selectedUpload?.id === upload.id ? "is-selected" : ""}
                >
                  <td className="is-checkbox">
                    <input type="checkbox" aria-label={`Select ${upload.filename}`} />
                  </td>
                  <td className="mono-cell">{formatSubmissionCode(upload, globalIndex)}</td>
                  <td className="lf-submissions-user">{upload.uploader_name || "Unknown User"}</td>
                  <td className="lf-submissions-type">{parts}</td>
                  <td>
                    <StatusPill status={upload.status} />
                  </td>
                  <td>
                    <div className="lf-submissions-date">{timestamp.date}</div>
                    <div className="lf-submissions-time">{timestamp.time}</div>
                  </td>
                  <td>
                    <div className="lf-submissions-actions">
                      <button
                        className="lf-submissions-view"
                        onClick={() => setSelectedUpload(upload)}
                        type="button"
                      >
                        View
                      </button>
                      {upload.status === "reupload_requested" && (
                        <button
                          className="lf-submissions-approve"
                          onClick={() => startReupload(upload)}
                          disabled={reuploading === upload.id}
                          type="button"
                        >
                          <FiUploadCloud size={15} />
                          {reuploading === upload.id ? "Uploading..." : "Re-upload"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {!filtered.length && (
          <div className="lf-submissions-empty">
            <FiArchive />
            <strong>No submissions found</strong>
            <span>Upload activity and review history will appear here.</span>
          </div>
        )}

        {/* ── Footer: results count + pagination ── */}
        {filtered.length > 0 && (
          <div className="lf-submissions-footer">
            <span className="lf-submissions-count">
              Showing <strong>{(safePage - 1) * PAGE_SIZE + 1}</strong> to{" "}
              <strong>{Math.min(safePage * PAGE_SIZE, filtered.length)}</strong> of{" "}
              <strong>{filtered.length}</strong> results
            </span>

            <div className="lf-submissions-pagination">
              <button
                className="lf-page-btn"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={safePage === 1}
                aria-label="Previous page"
              >
                ‹
              </button>

              {getPageNumbers().map((p, i) =>
                p === "..." ? (
                  <span key={`ellipsis-${i}`} className="lf-page-ellipsis">
                    …
                  </span>
                ) : (
                  <button
                    key={p}
                    className={`lf-page-btn${safePage === p ? " is-active" : ""}`}
                    onClick={() => setPage(p)}
                    type="button"
                  >
                    {p}
                  </button>
                )
              )}

              <button
                className="lf-page-btn"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={safePage === totalPages}
                aria-label="Next page"
              >
                ›
              </button>
            </div>
          </div>
        )}
      </section>

      {/* ── Detail panel ── */}
      {selectedUpload && (
        <section className="lf-submissions-conversation">
          <div className="lf-submissions-conversation__head">
            <div>
              <h2>{selectedUpload.filename}</h2>
              <p>
                {selectedUpload.status} ·{" "}
                {Number(selectedUpload.total_rows || 0).toLocaleString("en-IN")} rows · v
                {selectedUpload.version_number || 1}
              </p>
            </div>
            <button
              className="secondary-button"
              onClick={() => setSelectedUpload(null)}
              type="button"
            >
              Close
            </button>
          </div>
          <CommentThread submissionId={selectedUpload.id} title="Submission conversation" />
        </section>
      )}
    </div>
  );
}

function formatSubmissionCode(upload, index) {
  if (upload.id) {
    const digits = String(upload.id).replace(/\D/g, "").slice(-5).padStart(5, "0");
    return `SUB-${digits}`;
  }
  return `SUB-${String(index + 1).padStart(5, "0")}`;
}

function inferSubmissionType(upload) {
  const name = String(upload.filename || "").toLowerCase();
  if (name.includes("expense")) return "Expense Report";
  if (name.includes("invoice")) return "Invoice";
  if (name.includes("reimburse")) return "Reimbursement";
  if (name.includes("purchase")) return "Purchase Order";
  return "Submission";
}

function formatSubmitted(value) {
  if (!value) return { date: "-", time: "" };
  const date = new Date(value);
  return {
    date: date.toLocaleDateString("en-IN", { month: "short", day: "numeric", year: "numeric" }),
    time: date.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" }),
  };
}

function StatusPill({ status }) {
  const normalized = String(status || "unknown").toLowerCase();
  const labelMap = {
    approved: "Approved",
    pending: "Pending",
    declined: "Rejected",
    reupload_requested: "Under Review",
  };
  return (
    <span className={`lf-submissions-status lf-submissions-status-${normalized}`}>
      {labelMap[normalized] || normalized.replaceAll("_", " ")}
    </span>
  );
}