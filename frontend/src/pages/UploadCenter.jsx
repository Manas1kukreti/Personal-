import React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  FiAlertCircle,
  FiCheckCircle,
  FiClock,
  FiDownload,
  FiFileText,
  FiFolder,
  FiSearch,
  FiSliders,
  FiUpload,
  FiUploadCloud,
  FiX
} from "react-icons/fi";
import { api } from "../api/client.js";
import { useWebSocket } from "../hooks/useWebSocket.js";

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const PAGE_SIZE = 5;
const ACCEPTED_EXTENSIONS = [".xlsx", ".csv", ".json"];

const STATUS_META = {
  approved: { label: "Completed", className: "is-completed", progress: 100 },
  successful: { label: "Completed", className: "is-completed", progress: 100 },
  completed: { label: "Completed", className: "is-completed", progress: 100 },
  processing: { label: "Processing", className: "is-processing", progress: 67 },
  pending: { label: "Pending", className: "is-pending", progress: 0 },
  initiated: { label: "Initiated", className: "is-processing", progress: 45 },
  parse_failed: { label: "Failed", className: "is-failed", progress: 0 },
  declined: { label: "Failed", className: "is-failed", progress: 0 },
  failed: { label: "Failed", className: "is-failed", progress: 0 },
  reupload_requested: { label: "Needs Re-upload", className: "is-pending", progress: 0 }
};

export default function UploadCenter() {
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const selectAllUploadsRef = useRef(null);
  const activeUploadIdRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState("");
  const [uploads, setUploads] = useState([]);
  const [selectedUploadIds, setSelectedUploadIds] = useState(() => new Set());
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const loadUploads = useCallback(async () => {
    const response = await api.get("/uploads");
    const nextUploads = Array.isArray(response.data) ? response.data : [];
    setUploads(nextUploads.filter((upload) => normalizeStatus(upload.status) !== "parse_failed"));
  }, []);

  useEffect(() => {
    loadUploads().catch(() => setUploads([]));
  }, [loadUploads]);

  useEffect(() => {
    const uploadIds = new Set(uploads.map((upload, index) => uploadKey(upload, index)));
    setSelectedUploadIds((current) => {
      const next = new Set([...current].filter((id) => uploadIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [uploads]);

  useWebSocket(
    "uploads",
    useCallback(
      (event) => {
        if (
          (event.event === "upload_progress" || event.event === "upload.progress") &&
          event.payload?.upload_id === activeUploadIdRef.current
        ) {
          setProgress(event.payload.progress || 0);
          setMessage(event.payload.filename ? `${event.payload.filename} processing` : "Upload processing");
        }
        if (event.event === "upload_status" || event.event === "approval.decision") {
          setMessage(`Upload ${formatStatus(event.payload.status)}`);
        }
        if (event.event === "upload.complete" && event.payload?.upload_id === activeUploadIdRef.current) {
          api
            .get(`/uploads/${event.payload.upload_id}`)
            .then((response) => {
              setPreview(response.data);
              setProgress(100);
              setMessage("Validated and sent to manager review");
            })
            .catch(() => {
              setMessage("Upload completed. Refresh to load the preview.");
            });
        }
        if (event.event === "upload.failed" && event.payload?.upload_id === activeUploadIdRef.current) {
          setProgress(100);
          const detail = event.payload.error;
          setError(typeof detail === "string" ? detail : "Upload validation failed. Please check the file and try again.");
          setMessage("Upload validation failed");
        }
        if (["upload.processing", "upload.complete", "upload.failed", "approval.decision", "upload_status"].includes(event.event)) {
          loadUploads().catch(() => setUploads([]));
        }
      },
      [loadUploads]
    )
  );

  const isValid = useMemo(
    () => file && ACCEPTED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext)),
    [file]
  );
  const isTooLarge = file && file.size > MAX_FILE_SIZE;
  const canSubmit = isValid && !isTooLarge;

  const stats = useMemo(() => {
    const completed = uploads.filter((upload) => isCompletedStatus(upload.status)).length;
    const processing = uploads.filter((upload) => normalizeStatus(upload.status) === "processing").length;
    const failed = uploads.filter((upload) => isFailedStatus(upload.status)).length;
    return [
      { label: "Files Uploaded", value: uploads.length, delta: `+${uploads.length}` },
      { label: "Processing", value: processing, delta: `+${processing}` },
      { label: "Completed", value: completed, delta: `+${completed}` },
      { label: "Failed", value: failed, delta: `+${failed}` }
    ];
  }, [uploads]);

  const filteredUploads = useMemo(() => {
    const query = search.trim().toLowerCase();
    const sorted = [...uploads].sort((a, b) => {
      const first = new Date(a.created_at || a.updated_at || 0).getTime();
      const second = new Date(b.created_at || b.updated_at || 0).getTime();
      return second - first;
    });

    return sorted.filter((upload) => {
      if (!query) return true;
      return [
        upload.filename,
        upload.status,
        upload.transaction_id,
        upload.upload_id,
        upload.id
      ]
        .some((value) => String(value || "").toLowerCase().includes(query));
    });
  }, [uploads, search]);

  const pageCount = Math.max(1, Math.ceil(filteredUploads.length / PAGE_SIZE));
  const pageRows = filteredUploads.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
  const visibleSelectedCount = pageRows.filter((upload, index) => selectedUploadIds.has(uploadKey(upload, page * PAGE_SIZE + index))).length;
  const selectedUploadCount = filteredUploads.filter((upload, index) => selectedUploadIds.has(uploadKey(upload, index))).length;
  const allVisibleUploadsSelected = pageRows.length > 0 && visibleSelectedCount === pageRows.length;

  useEffect(() => {
    setPage(0);
  }, [search]);

  useEffect(() => {
    if (!selectAllUploadsRef.current) return;
    selectAllUploadsRef.current.indeterminate = visibleSelectedCount > 0 && !allVisibleUploadsSelected;
  }, [allVisibleUploadsSelected, visibleSelectedCount]);

  async function submitUpload() {
    if (!canSubmit) return;
    const form = new FormData();
    form.append("file", file);
    setProgress(8);
    setError("");
    setMessage("Uploading file");

    try {
      const response = await api.post("/uploads", form, { headers: { "Content-Type": "multipart/form-data" } });
      setPreview(response.data);
      activeUploadIdRef.current = response.data?.upload_id ?? null;
      setProgress(40);
      setMessage("File received. Validation is running in the background.");
      await loadUploads();
    } catch (err) {
      setProgress(0);
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Upload failed. Please check the file and try again.");
    }
  }

  function onDrop(event) {
    event.preventDefault();
    setDrag(false);
    const nextFile = event.dataTransfer.files?.[0];
    if (nextFile) selectFile(nextFile);
  }

  function selectFile(nextFile) {
    setFile(nextFile);
    setPreview(null);
    activeUploadIdRef.current = null;
    setProgress(0);
    setError("");
    setMessage("");
  }

  function reset() {
    activeUploadIdRef.current = null;
    setFile(null);
    setPreview(null);
    setProgress(0);
    setMessage("");
    setError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (folderInputRef.current) folderInputRef.current.value = "";
  }

  function toggleUploadSelection(upload, index) {
    const id = uploadKey(upload, index);
    setSelectedUploadIds((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function toggleVisibleUploadsSelection() {
    setSelectedUploadIds((current) => {
      const next = new Set(current);
      if (allVisibleUploadsSelected) {
        pageRows.forEach((upload, index) => next.delete(uploadKey(upload, page * PAGE_SIZE + index)));
      } else {
        pageRows.forEach((upload, index) => next.add(uploadKey(upload, page * PAGE_SIZE + index)));
      }
      return next;
    });
  }

  return (
    <div className="lf-upload-page">
      <input
        ref={fileInputRef}
        className="hidden"
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={(event) => event.target.files?.[0] && selectFile(event.target.files[0])}
      />
      <input
        ref={folderInputRef}
        className="hidden"
        type="file"
        webkitdirectory="true"
        directory="true"
        onChange={(event) => event.target.files?.[0] && selectFile(event.target.files[0])}
      />

      <section className="lf-upload-header">
        <div>
          <h1>Upload Center</h1>
          <p>Upload and manage your transaction files</p>
        </div>
        <button className="lf-upload-icon-button" type="button" onClick={() => fileInputRef.current?.click()}>
          <FiFileText size={16} />
        </button>
      </section>

      <section className="lf-upload-stats-grid">
        {stats.map((stat) => (
          <div className="lf-upload-stat-card" key={stat.label}>
            <span>{stat.label}</span>
            <div className="lf-upload-stat-row">
              <strong>{stat.value}</strong>
              <small>{stat.delta}</small>
            </div>
          </div>
        ))}
      </section>

      <section
        className={`lf-upload-dropzone ${drag ? "is-dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <div className="lf-upload-dropzone__icon">
          <FiUploadCloud size={34} />
        </div>
        <h2>Drop your files here</h2>
        <p>or click to browse from your computer</p>
        <div className="lf-upload-dropzone__actions">
          <button className="lf-upload-primary" type="button" onClick={() => fileInputRef.current?.click()}>
            Select Files
          </button>
          <button className="lf-upload-secondary" type="button" onClick={() => folderInputRef.current?.click()}>
            Browse Folder
          </button>
        </div>
        <span>Supported formats: CSV, XLSX, JSON • Max file size: 10MB</span>
      </section>

      {file && (
        <section className="lf-upload-current-file">
          <div className="lf-upload-current-file__meta">
            <div className="lf-upload-file-tile">
              <FiFileText size={18} />
            </div>
            <div>
              <strong>{file.name}</strong>
              <p>{formatFileSize(file.size)}{preview ? ` • ${preview.total_rows || 0} rows` : ""}</p>
            </div>
          </div>
          <div className="lf-upload-current-file__actions">
            <div className="lf-upload-inline-progress">
              <div className="lf-upload-inline-progress__label">
                <span>{preview?.status === "processing" ? "Processing" : "Upload progress"}</span>
                <span>{progress}%</span>
              </div>
              <div className="lf-upload-inline-progress__track">
                <div className="lf-upload-inline-progress__fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
            <button className="lf-upload-primary" type="button" disabled={!canSubmit || Boolean(preview)} onClick={submitUpload}>
              Upload
            </button>
            <button className="lf-upload-close" type="button" onClick={reset}>
              <FiX size={16} />
            </button>
          </div>
        </section>
      )}

      {message && <div className="lf-upload-feedback is-success">{message}</div>}
      {(error || isTooLarge) && (
        <div className="lf-upload-feedback is-error">
          <FiAlertCircle size={16} />
          <span>{error || "File is larger than the 10 MB limit."}</span>
        </div>
      )}

      <section className="lf-upload-table-card">
        <div className="lf-upload-table-card__header">
          <div>
            <h2>Recent Uploads</h2>
            <p>{selectedUploadCount ? `${selectedUploadCount} selected` : `${filteredUploads.length} files`}</p>
          </div>
          <div className="lf-upload-table-card__tools">
            <label className="lf-upload-search">
              <FiSearch size={18} />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search files..." />
            </label>
            <button className="lf-upload-filter-button" type="button">
              <FiSliders size={16} />
            </button>
          </div>
        </div>

        <div className="lf-upload-table-wrap">
          <table className="lf-upload-table">
            <thead>
              <tr>
                <th className="is-check">
                  <input
                    ref={selectAllUploadsRef}
                    type="checkbox"
                    aria-label="Select all visible uploads"
                    checked={allVisibleUploadsSelected}
                    onChange={toggleVisibleUploadsSelection}
                  />
                </th>
                <th>File Name</th>
                <th>Size</th>
                <th>Records</th>
                <th>Progress</th>
                <th>Status</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.length ? (
                pageRows.map((upload, index) => {
                  const statusMeta = getStatusMeta(upload.status);
                  return (
                    <tr key={upload.id || upload.upload_id || `${upload.filename}-${index}`}>
                      <td className="is-check">
                        <input
                          type="checkbox"
                          aria-label={`Select ${upload.filename || "upload"}`}
                          checked={selectedUploadIds.has(uploadKey(upload, page * PAGE_SIZE + index))}
                          onChange={() => toggleUploadSelection(upload, page * PAGE_SIZE + index)}
                        />
                      </td>
                      <td>
                        <div className="lf-upload-file-cell">
                          <div className={`lf-upload-file-icon ${fileIconClass(upload.filename)}`}>
                            <FiFileText size={16} />
                          </div>
                          <span>{upload.filename || `upload_${index + 1}`}</span>
                        </div>
                      </td>
                      <td>{formatUploadSize(upload)}</td>
                      <td>{formatRecordCount(upload)}</td>
                      <td>
                        <UploadProgressCell upload={upload} statusMeta={statusMeta} />
                      </td>
                      <td>
                        <span className={`lf-upload-status-pill ${statusMeta.className}`}>{statusMeta.label}</span>
                      </td>
                      <td>{formatRelativeUploadTime(upload.created_at || upload.updated_at)}</td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7}>
                    <div className="lf-upload-empty">No uploads found yet.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="lf-upload-pagination">
          <span>
            Showing {filteredUploads.length ? page * PAGE_SIZE + 1 : 0} to {Math.min(filteredUploads.length, page * PAGE_SIZE + PAGE_SIZE)} of {filteredUploads.length} files
          </span>
          <div className="lf-upload-pagination__controls">
            <button className="lf-upload-page-button is-ghost" type="button" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>
              Previous
            </button>
            {Array.from({ length: pageCount }, (_, index) => (
              <button
                key={index}
                className={`lf-upload-page-button ${page === index ? "is-active" : "is-ghost"}`}
                type="button"
                onClick={() => setPage(index)}
              >
                {index + 1}
              </button>
            ))}
            <button className="lf-upload-page-button is-ghost" type="button" disabled={page + 1 >= pageCount} onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))}>
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function uploadKey(upload, index) {
  return String(upload.id || upload.upload_id || `${upload.filename || "upload"}-${upload.created_at || upload.updated_at || index}`);
}

function UploadProgressCell({ upload, statusMeta }) {
  const progress = upload.progress ?? statusMeta.progress ?? inferProgress(upload.status);
  const label = progress >= 100 ? "100%" : `${progress}%`;

  return (
    <div className="lf-upload-progress-cell">
      <div className="lf-upload-progress-track">
        <div className={`lf-upload-progress-fill ${statusMeta.className}`} style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }} />
      </div>
      <div className={`lf-upload-progress-label ${statusMeta.className}`}>
        {progress >= 100 ? <FiCheckCircle size={14} /> : progress > 0 ? <FiClock size={14} /> : <FiDownload size={14} />}
        <span>{label}</span>
      </div>
    </div>
  );
}

function normalizeStatus(status) {
  return String(status || "pending").toLowerCase();
}

function getStatusMeta(status) {
  return STATUS_META[normalizeStatus(status)] || { label: formatStatus(status), className: "is-pending", progress: inferProgress(status) };
}

function inferProgress(status) {
  const normalized = normalizeStatus(status);
  if (["approved", "successful", "completed"].includes(normalized)) return 100;
  if (["processing"].includes(normalized)) return 67;
  if (["initiated"].includes(normalized)) return 45;
  return 0;
}

function isCompletedStatus(status) {
  return ["approved", "successful", "completed"].includes(normalizeStatus(status));
}

function isFailedStatus(status) {
  return ["failed", "declined", "parse_failed"].includes(normalizeStatus(status));
}

function fileIconClass(filename) {
  const name = String(filename || "").toLowerCase();
  if (name.endsWith(".json")) return "is-json";
  if (name.endsWith(".xlsx")) return "is-xlsx";
  return "is-csv";
}

function formatUploadSize(upload) {
  const raw = Number(upload.file_size || upload.size || 0);
  if (raw > 0) return formatFileSize(raw);
  const rows = Number(upload.total_rows || upload.rows || 0);
  if (rows >= 1000) return `${(rows / 6400).toFixed(1)} MB`;
  return "-";
}

function formatRecordCount(upload) {
  return Number(upload.total_rows || upload.rows || 0).toLocaleString("en-IN") || "-";
}

function formatRelativeUploadTime(value) {
  if (!value) return "-";
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return "-";
  const diff = Date.now() - timestamp;
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function formatFileSize(size) {
  if (!size) return "0 KB";
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}

function formatStatus(status) {
  return String(status || "-")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
