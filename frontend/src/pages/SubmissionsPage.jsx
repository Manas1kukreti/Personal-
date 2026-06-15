import React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FiArchive, FiDownload, FiMoreVertical, FiSearch, FiSend, FiUploadCloud, FiX } from "react-icons/fi";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";

const TABS = [
  { label: "All", value: "" },
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "declined" },
];

const PAGE_SIZE = 10;

export default function SubmissionsPage() {
  const reuploadInputRef = useRef(null);
  const selectAllRef = useRef(null);
  const actionsMenuRef = useRef(null);
  const [uploads, setUploads] = useState([]);
  const [selectedSubmissionIds, setSelectedSubmissionIds] = useState(() => new Set());
  const [reuploadTarget, setReuploadTarget] = useState(null);
  const [reuploading, setReuploading] = useState("");
  const [reuploadError, setReuploadError] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [commentsSubmission, setCommentsSubmission] = useState(null);
  const [transactionsSubmission, setTransactionsSubmission] = useState(null);

  const loadUploads = useCallback(async () => {
    const response = await api.get("/uploads");
    setUploads(response.data.filter((upload) => upload.status !== "parse_failed"));
  }, []);

  useEffect(() => {
    loadUploads().catch(() => setUploads([]));
  }, [loadUploads]);

  useEffect(() => {
    const uploadIds = new Set(uploads.map((upload) => upload.id));
    setSelectedSubmissionIds((current) => {
      const next = new Set([...current].filter((id) => uploadIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [uploads]);

  // Reset to page 1 whenever filters change
  useEffect(() => {
    setPage(1);
  }, [query, status]);

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();
    return uploads.filter((upload, index) => {
      const submitted = formatSubmitted(upload.created_at);
      const matchesStatus = !status || upload.status === status;
      const matchesSearch =
        !search ||
        [
          upload.filename,
          upload.uploader_name,
          upload.status,
          upload.id,
          upload.sub_id,
          formatSubmissionCode(upload, index),
          formatSubmissionCode(upload, index, 6),
          upload.created_at,
          submitted.date,
          submitted.time,
        ].some(
          (value) => String(value || "").toLowerCase().includes(search)
        );
      return matchesStatus && matchesSearch;
    });
  }, [uploads, query, status]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginated = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const selectedUploads = filtered.filter((upload) => selectedSubmissionIds.has(upload.id));
  const visibleSelectionCount = paginated.filter((upload) => selectedSubmissionIds.has(upload.id)).length;
  const allVisibleSelected = paginated.length > 0 && visibleSelectionCount === paginated.length;

  useEffect(() => {
    if (!selectAllRef.current) return;
    selectAllRef.current.indeterminate = visibleSelectionCount > 0 && !allVisibleSelected;
  }, [allVisibleSelected, visibleSelectionCount]);

  useEffect(() => {
    if (!openMenuId) return;
    function closeMenu(event) {
      if (actionsMenuRef.current?.contains(event.target)) return;
      setOpenMenuId(null);
    }
    document.addEventListener("mousedown", closeMenu);
    return () => document.removeEventListener("mousedown", closeMenu);
  }, [openMenuId]);

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
    const exportRows = selectedUploads.length ? selectedUploads : filtered;
    const csv = [
      ["Filename", "Status", "Rows", "Columns", "Uploader", "Created At", "Reviewed At"],
      ...exportRows.map((upload) => [
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

  function toggleSubmissionSelection(uploadId) {
    setSelectedSubmissionIds((current) => {
      const next = new Set(current);
      if (next.has(uploadId)) {
        next.delete(uploadId);
      } else {
        next.add(uploadId);
      }
      return next;
    });
  }

  function toggleVisibleSelection() {
    setSelectedSubmissionIds((current) => {
      const next = new Set(current);
      if (allVisibleSelected) {
        paginated.forEach((upload) => next.delete(upload.id));
      } else {
        paginated.forEach((upload) => next.add(upload.id));
      }
      return next;
    });
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

  async function submitToManager(upload) {
    try {
      await api.post(`/uploads/${upload.id}/submit`, {});
      await loadUploads();
    } catch (err) {
      alert(err.response?.data?.detail || "Unable to submit to manager.");
    }
  }

  function openComments(upload, submissionCode) {
    setCommentsSubmission({ ...upload, submissionCode });
    setOpenMenuId(null);
  }

  function openTransactions(upload, submissionCode) {
    setTransactionsSubmission({ ...upload, submissionCode });
    setOpenMenuId(null);
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

      <h1 className="lf-submissions-title">Submissions</h1>

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
            className="secondary-button"
            onClick={exportCsv}
            disabled={!filtered.length}
            type="button"
          >
            <FiDownload /> {selectedUploads.length ? `Export (${selectedUploads.length})` : "Export"}
          </button>
        </div>
      </section>

      {reuploadError && <div className="lf-submissions-error">{reuploadError}</div>}

      <section className="lf-submissions-table-wrap">
        <table className="lf-submissions-table">
          <thead>
            <tr>
              <th className="is-checkbox">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  aria-label="Select all visible submissions"
                  checked={allVisibleSelected}
                  onChange={toggleVisibleSelection}
                />
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
              const submissionCode = formatSubmissionCode(upload, globalIndex);
              return (
                <tr
                  key={upload.id}
                  className={openMenuId === upload.id ? "is-selected" : ""}
                >
                  <td className="is-checkbox">
                    <input
                      type="checkbox"
                      aria-label={`Select ${upload.filename}`}
                      checked={selectedSubmissionIds.has(upload.id)}
                      onChange={() => toggleSubmissionSelection(upload.id)}
                    />
                  </td>
                  <td className="mono-cell">{submissionCode}</td>
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
                      <div className="lf-submissions-menu-wrap" ref={openMenuId === upload.id ? actionsMenuRef : null}>
                        <button
                          className="lf-submissions-kebab"
                          onClick={() => setOpenMenuId((current) => current === upload.id ? null : upload.id)}
                          type="button"
                          aria-label={`Open actions for ${submissionCode}`}
                          aria-expanded={openMenuId === upload.id}
                        >
                          <FiMoreVertical size={17} />
                        </button>
                        {openMenuId === upload.id && (
                          <div className="lf-submissions-row-menu">
                            <button type="button" onClick={() => openComments(upload, submissionCode)}>
                              Open comments
                            </button>
                            <button type="button" onClick={() => openTransactions(upload, submissionCode)}>
                              View transactions
                            </button>
                          </div>
                        )}
                      </div>
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
                      {upload.status === "initiated" && (
                        <button
                          className="lf-submissions-approve"
                          onClick={() => submitToManager(upload)}
                          type="button"
                          style={{
                            backgroundColor: "hsl(243, 75%, 59%)",
                            color: "#ffffff",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "6px 12px",
                            borderRadius: "8px",
                            fontSize: "0.8rem",
                            fontWeight: "600"
                          }}
                        >
                          <FiSend size={15} />
                          Submit to Manager
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

      {commentsSubmission && (
        <SubmissionCommentsModal
          submission={commentsSubmission}
          onClose={() => setCommentsSubmission(null)}
        />
      )}

      {transactionsSubmission && (
        <SubmissionTransactionsModal
          submission={transactionsSubmission}
          onClose={() => setTransactionsSubmission(null)}
        />
      )}
    </div>
  );
}

function SubmissionCommentsModal({ submission, onClose }) {
  const { user } = useAuth();
  const [comments, setComments] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const loadComments = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get(`/submissions/${submission.id}/comments`);
      setComments(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load comments.");
    } finally {
      setLoading(false);
    }
  }, [submission.id]);

  useEffect(() => {
    loadComments();
  }, [loadComments]);

  useWebSocket("comments", useCallback((event) => {
    if (event.event !== "new_comment" || event.payload?.submission_id !== submission.id) return;
    setComments((current) => {
      if (current.some((comment) => comment.id === event.payload.id)) return current;
      return [...current, event.payload];
    });
  }, [submission.id]));

  const sortedComments = useMemo(
    () => [...comments].sort((a, b) => new Date(a.created_at) - new Date(b.created_at)),
    [comments]
  );

  async function sendComment(event) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;
    setSending(true);
    setError("");
    try {
      const response = await api.post(`/submissions/${submission.id}/comments`, { message: trimmed });
      setComments((current) => current.some((comment) => comment.id === response.data.id) ? current : [...current, response.data]);
      setMessage("");
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to send comment.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="lf-submissions-modal-backdrop" onClick={onClose} role="presentation">
      <section className="lf-submissions-modal" role="dialog" aria-modal="true" aria-labelledby="submission-comments-title" onClick={(event) => event.stopPropagation()}>
        <ModalHeader title="Submission conversation" submission={submission} onClose={onClose} titleId="submission-comments-title" />
        <div className="lf-submissions-chat-list">
          {loading && <div className="lf-submissions-modal-empty">Loading comments...</div>}
          {!loading && sortedComments.map((comment) => {
            const mine = comment.user_id === user?.id;
            return (
              <article className={`lf-submissions-chat-bubble${mine ? " is-mine" : ""}`} key={comment.id}>
                <div>
                  <strong>{comment.user_name || "User"}</strong>
                  <time>{formatModalDate(comment.created_at)}</time>
                </div>
                <p>{comment.message}</p>
              </article>
            );
          })}
          {!loading && !sortedComments.length && (
            <div className="lf-submissions-modal-empty">No comments yet</div>
          )}
        </div>
        {error && <div className="lf-submissions-modal-error">{error}</div>}
        <form className="lf-submissions-comment-form" onSubmit={sendComment}>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Write a comment..."
            maxLength={2000}
          />
          <button className="primary-button" type="submit" disabled={sending || !message.trim()}>
            <FiSend size={16} />
            {sending ? "Sending..." : "Send"}
          </button>
        </form>
      </section>
    </div>
  );
}

function SubmissionTransactionsModal({ submission, onClose }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function loadTransactions() {
      setLoading(true);
      setError("");
      try {
        const response = await api.get(`/uploads/${submission.id}/transactions`);
        if (!cancelled) setRows(Array.isArray(response.data) ? response.data : []);
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || "Unable to load transactions.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadTransactions();
    return () => {
      cancelled = true;
    };
  }, [submission.id]);

  const transactionRows = useMemo(() => buildTransactionRows(rows, submission.status), [rows, submission.status]);

  return (
    <div className="lf-submissions-modal-backdrop" onClick={onClose} role="presentation">
      <section className="lf-submissions-modal lf-submissions-modal--wide" role="dialog" aria-modal="true" aria-labelledby="submission-transactions-title" onClick={(event) => event.stopPropagation()}>
        <ModalHeader title="Submission transactions" submission={submission} onClose={onClose} titleId="submission-transactions-title" />
        <div className="lf-submissions-sheet-wrap">
          <table className="lf-submissions-sheet-table">
            <thead>
              <tr>
                <th>Entry No</th>
                <th>Transaction ID</th>
                <th>Account Code</th>
                <th>Sub Account</th>
                <th>From Account (debit source)</th>
                <th>To Account (credit destination)</th>
                <th>Debit Amount</th>
                <th>Credit Amount</th>
                <th>Difference</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {transactionRows.map((row) => (
                <tr key={row.id}>
                  <td>{row.entryNo}</td>
                  <td>{row.transactionId}</td>
                  <td>{row.accountCode}</td>
                  <td>{row.subAccount}</td>
                  <td>{row.fromAccount}</td>
                  <td>{row.toAccount}</td>
                  <td>{formatCurrency(row.debitAmount)}</td>
                  <td>{formatCurrency(row.creditAmount)}</td>
                  <td>{formatCurrency(row.difference)}</td>
                  <td className={row.failed ? "is-failed" : "is-approved"}>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading && <div className="lf-submissions-modal-empty">Loading transactions...</div>}
          {!loading && error && <div className="lf-submissions-modal-error">{error}</div>}
          {!loading && !error && !transactionRows.length && (
            <div className="lf-submissions-modal-empty">No transactions found</div>
          )}
        </div>
      </section>
    </div>
  );
}

function ModalHeader({ title, submission, onClose, titleId }) {
  return (
    <header className="lf-submissions-modal-header">
      <div>
        <h2 id={titleId}>{title}</h2>
        <span>{submission.submissionCode}</span>
      </div>
      <button type="button" onClick={onClose} aria-label="Close modal">
        <FiX size={18} />
      </button>
    </header>
  );
}

function formatSubmissionCode(upload, index, minDigits = 5) {
  if (upload.sub_id) return `SUB-${String(upload.sub_id).padStart(minDigits, "0")}`;
  return `SUB-${String(index + 1).padStart(minDigits, "0")}`;
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

function formatModalDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

function formatCurrency(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  });
}

function buildTransactionRows(rows, submissionStatus) {
  const groups = rows.reduce((map, row) => {
    const key = row.entry_group ?? row.entry_no ?? row.id;
    const current = map.get(key) || [];
    current.push(row);
    map.set(key, current);
    return map;
  }, new Map());

  return rows.map((row) => {
    const groupRows = groups.get(row.entry_group ?? row.entry_no ?? row.id) || [row];
    const debitRow = groupRows.find((item) => Number(item.debit_amount || 0) > 0);
    const creditRow = groupRows.find((item) => Number(item.credit_amount || 0) > 0);
    const debitAmount = Number(row.debit_amount || 0);
    const creditAmount = Number(row.credit_amount || 0);
    const groupDebit = groupRows.reduce((sum, item) => sum + Number(item.debit_amount || 0), 0);
    const groupCredit = groupRows.reduce((sum, item) => sum + Number(item.credit_amount || 0), 0);
    const difference = groupDebit - groupCredit;
    const failed = String(submissionStatus || "").toLowerCase() === "declined" || Math.abs(difference) > 0.009;

    return {
      id: row.id,
      entryNo: `${row.entry_group ?? "-"}${row.entry_line ? `.${row.entry_line}` : ""}`,
      transactionId: `${row.submission_id || row.upload_id || "-"}:${row.entry_group ?? "-"}`,
      accountCode: row.account_code || "-",
      subAccount: row.sub_account || "-",
      fromAccount: debitRow ? `${debitRow.sub_account} (${debitRow.account_code})` : "-",
      toAccount: creditRow ? `${creditRow.sub_account} (${creditRow.account_code})` : "-",
      debitAmount,
      creditAmount,
      difference,
      failed,
      status: failed ? "Failed" : "Approved",
    };
  });
}

function StatusPill({ status }) {
  const normalized = String(status || "unknown").toLowerCase();
  const labelMap = {
    approved: "Approved",
    pending: "Pending",
    declined: "Rejected",
    reupload_requested: "Under Review",
    initiated: "Draft / Unsubmitted",
  };
  return (
    <span className={`lf-submissions-status lf-submissions-status-${normalized}`}>
      {labelMap[normalized] || normalized.replaceAll("_", " ")}
    </span>
  );
}
