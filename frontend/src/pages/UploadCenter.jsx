import React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  FiActivity,
  FiAlertCircle,
  FiBarChart2,
  FiCheck,
  FiCheckCircle,
  FiClock,
  FiColumns,
  FiDownload,
  FiFileText,
  FiChevronLeft,
  FiChevronRight,
  FiRefreshCw,
  FiSend,
  FiShield,
  FiSearch,
  FiUpload,
  FiUploadCloud,
  FiX
} from "react-icons/fi";
import { api } from "../api/client.js";
import { useWebSocket } from "../hooks/useWebSocket.js";

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const FILTERS = ["All", "Payment", "Debit", "Credit", "Transfer", "Refund"];
const PAGE_SIZE = 10;

const TABLE_COLUMNS = [
  { key: "merchant_name", label: "Merchant", width: "18%" },
  { key: "transaction_id", label: "Transaction ID", width: "14%" },
  { key: "transaction_date", label: "Date", width: "12%" },
  { key: "amount", label: "Amount", width: "11%" },
  { key: "transaction_type", label: "Type", width: "13%" },
  { key: "payment_method", label: "Method", width: "14%" },
  { key: "status", label: "Status", width: "12%" },
  { key: "invoice_id", label: "Invoice", width: "11%" }
];

const TYPE_STYLES = {
  Payment: { bg: "#E7F5F1", color: "#155E58" },
  Debit: { bg: "#faeeda", color: "#854f0b" },
  Credit: { bg: "#D5F1EA", color: "#1E8278" },
  Transfer: { bg: "#EEF8F5", color: "#277A73" },
  Refund: { bg: "#fbeaf0", color: "#993556" }
};

const STATUS_STYLES = {
  Successful: { bg: "#E7F5F1", color: "#155E58" },
  Pending: { bg: "#faeeda", color: "#854f0b" },
  Failed: { bg: "#fcebeb", color: "#a32d2d" },
  Initiated: { bg: "#EEF8F5", color: "#277A73" },
  pending: { bg: "#faeeda", color: "#854f0b" },
  approved: { bg: "#E7F5F1", color: "#155E58" },
  declined: { bg: "#fcebeb", color: "#a32d2d" },
  reupload_requested: { bg: "#EEF8F5", color: "#277A73" }
};

const MERCHANTS = {
  Flipkart: { bg: "#fff8f0", icon: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/flipkart.svg", initials: "FL", color: "#F74000" },
  Uber: { bg: "#f0f0f0", icon: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/uber.svg", initials: "UB", color: "#000" },
  Ola: { bg: "#ff8c00", initials: "OL", color: "#fff" },
  Swiggy: { bg: "#fff4ee", icon: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/swiggy.svg", initials: "SW", color: "#FC8019" },
  Amazon: { bg: "#fff8f0", icon: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/amazon.svg", initials: "AM", color: "#FF9900" },
  Zomato: { bg: "#fff0f0", icon: "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/zomato.svg", initials: "ZO", color: "#E23744" },
  Reliance: { bg: "#1a3a8c", initials: "RL", color: "#fff" },
  Tata: { bg: "#003087", initials: "TA", color: "#fff" }
};

export default function UploadCenter() {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState("");
  const [uploads, setUploads] = useState([]);
  const [activeFilter, setActiveFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState({ key: "transaction_date", direction: "asc" });
  const [page, setPage] = useState(0);
  const [showColumns, setShowColumns] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState(() => Object.fromEntries(TABLE_COLUMNS.map((column) => [column.key, true])));

  const loadUploads = useCallback(async () => {
    const response = await api.get("/uploads");
    setUploads(response.data);
  }, []);

  useEffect(() => {
    loadUploads().catch(() => setUploads([]));
  }, [loadUploads]);

  useWebSocket("uploads", useCallback((event) => {
    if (event.event === "upload_progress" || event.event === "upload.progress") {
      setProgress(event.payload.progress || 0);
      setMessage(event.payload.filename ? `${event.payload.filename} processed` : "Upload processing");
    }
    if (event.event === "upload_status" || event.event === "approval.decision") {
      setMessage(`Upload ${formatStatus(event.payload.status)}`);
    }
    if (["upload.complete", "approval.decision", "upload_status"].includes(event.event)) {
      loadUploads().catch(() => setUploads([]));
    }
  }, [loadUploads]));

  const isValid = useMemo(() => file && [".xlsx", ".csv"].some((ext) => file.name.toLowerCase().endsWith(ext)), [file]);
  const isTooLarge = file && file.size > MAX_FILE_SIZE;
  const canSubmit = isValid && !isTooLarge;
  const rows = preview?.preview_rows || [];
  const uploadStats = useMemo(() => {
    const pending = uploads.filter((upload) => upload.status === "pending").length;
    const approved = uploads.filter((upload) => upload.status === "approved").length;
    const totalRows = uploads.reduce((sum, upload) => sum + Number(upload.total_rows || upload.rows || 0), 0);
    return [
      { label: "Submissions", value: uploads.length, detail: "Last 100 files", icon: FiFileText },
      { label: "Pending Review", value: pending, detail: "Manager queue", icon: FiClock },
      { label: "Approved", value: approved, detail: "Cleared files", icon: FiCheckCircle },
      { label: "Rows Processed", value: totalRows.toLocaleString("en-IN"), detail: "Uploaded records", icon: FiBarChart2 }
    ];
  }, [uploads]);

  const filteredRows = useMemo(() => {
    const query = search.trim().toLowerCase();
    const nextRows = rows.filter((row) => {
      const matchesType = activeFilter === "all" || String(row.transaction_type || "").toLowerCase() === activeFilter;
      const matchesQuery = !query || [
        row.merchant_name,
        row.transaction_id,
        row.invoice_id,
        row.payment_method,
        row.status,
        row.amount
      ].some((value) => String(value || "").toLowerCase().includes(query));
      return matchesType && matchesQuery;
    });

    return [...nextRows].sort((a, b) => compareRows(a, b, sort));
  }, [rows, activeFilter, search, sort]);

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const pageRows = filteredRows.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
  const activeColumns = TABLE_COLUMNS.filter((column) => visibleColumns[column.key]);

  useEffect(() => {
    setPage(0);
  }, [activeFilter, search, sort, preview?.upload_id]);

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
      setActiveFilter("all");
      setProgress(100);
      setMessage("Validated and sent to manager review");
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
    setProgress(0);
    setError("");
    setMessage("");
    setActiveFilter("all");
    setSearch("");
    setPage(0);
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setProgress(0);
    setMessage("");
    setError("");
    setActiveFilter("all");
    setSearch("");
    setPage(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function toggleSort(key) {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === "asc" ? "desc" : "asc"
    }));
  }

  function toggleColumn(key) {
    setVisibleColumns((current) => {
      const enabledCount = Object.values(current).filter(Boolean).length;
      if (current[key] && enabledCount <= 1) return current;
      return { ...current, [key]: !current[key] };
    });
  }

  function exportPreviewCsv() {
    if (!filteredRows.length) return;
    const headers = activeColumns.map((column) => column.label);
    const csv = [
      headers,
      ...filteredRows.map((row) => activeColumns.map((column) => formatCsvValue(row[column.key])))
    ]
      .map((line) => line.map((cell) => `"${String(cell ?? "").replaceAll("\"", "\"\"")}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ledgerflow-preview-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="upload-center-page app-page">
      <input
        ref={fileInputRef}
        className="hidden"
        type="file"
        accept=".xlsx,.csv"
        onChange={(event) => event.target.files?.[0] && selectFile(event.target.files[0])}
      />

      <section className="upload-topbar">
        <div>
          <h1 className="upload-title">Upload Center</h1>
          <p className="upload-subtitle">Upload .xlsx or .csv transaction files for review.</p>
        </div>
        <button className="primary-button" onClick={() => fileInputRef.current?.click()}>
          <FiUpload size={16} /> Upload file
        </button>
      </section>

      <section
        className={`upload-dropzone ${drag ? "is-dragging" : ""}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <div className="upload-drop-icon">
          <FiUploadCloud />
        </div>
        <div className="upload-drop-title">Drop your file here</div>
        <div className="upload-drop-sub">
          <span>Browse files</span> / .xlsx or .csv / Max 10 MB
        </div>
      </section>

      <section className="upload-signal-grid">
        {uploadStats.map((stat, index) => (
          <UploadSignal key={stat.label} {...stat} delay={index * 0.05} />
        ))}
      </section>

      <section className="upload-workflow-strip">
        <WorkflowStep active done={Boolean(file)} icon={FiUploadCloud} label="File intake" detail={file ? "Spreadsheet attached" : "Awaiting spreadsheet"} />
        <WorkflowStep active={Boolean(file)} done={Boolean(preview)} icon={FiShield} label="Schema validation" detail={preview ? "Validation passed" : "Required columns checked"} />
        <WorkflowStep active={Boolean(preview)} done={Boolean(preview)} icon={FiActivity} label="Preview extraction" detail={preview ? `${rows.length} rows rendered` : "Dynamic table generated"} />
        <WorkflowStep active={Boolean(preview)} done={Boolean(preview)} icon={FiSend} label="Manager routing" detail={preview ? "In review queue" : "Ready after validation"} />
      </section>

      {file && (
        <section className="upload-file-row">
          <div className="upload-file-icon">
            <FiFileText />
          </div>
          <div className="upload-file-copy">
            <div className="upload-file-name">{file.name}</div>
            <div className="upload-file-meta">
              {preview ? `${preview.total_rows} rows / ${preview.total_columns} columns / ` : ""}
              {formatFileSize(file.size)}
            </div>
          </div>
          <div className={`upload-file-badge ${canSubmit || preview ? "is-valid" : "is-invalid"}`}>
            {canSubmit || preview ? <FiCheck size={12} /> : <FiAlertCircle size={12} />}
            {preview ? "Validated" : canSubmit ? "Ready" : "Needs review"}
          </div>
          <button className="upload-remove-button" onClick={reset} title="Remove file">
            <FiX />
          </button>
        </section>
      )}

      {file && !preview && (
        <section className="upload-action-row">
          <div className="upload-progress-wrap">
            <div className="upload-progress-label">
              <span>Upload progress</span>
              <span>{progress}%</span>
            </div>
            <div className="upload-progress-track">
              <div className="upload-progress-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <button className="primary-button" disabled={!canSubmit} onClick={submitUpload}>
            <FiCheckCircle size={16} /> Validate preview
          </button>
          <button className="icon-button" onClick={reset} title="Reset upload">
            <FiRefreshCw />
          </button>
        </section>
      )}

      {message && <p className="upload-message">{message}</p>}
      {(error || isTooLarge) && (
        <div className="upload-error">
          <FiAlertCircle />
          <span>{error || "File is larger than the 10 MB limit."}</span>
        </div>
      )}

      <section className="upload-preview-header">
        <div>
          <h2 className="upload-section-title">Transaction preview</h2>
          <p className="upload-section-subtitle">
            {preview ? `${filteredRows.length} of ${rows.length} rows visible` : "Preview appears after validation."}
          </p>
        </div>
        <span className="upload-count-badge">{filteredRows.length} rows</span>
      </section>

      <section className="upload-filters" aria-label="Transaction type filters">
        {FILTERS.map((filter) => {
          const value = filter.toLowerCase();
          const active = activeFilter === value;
          return (
            <button
              key={filter}
              className={`upload-filter ${active ? "is-active" : ""}`}
              onClick={() => setActiveFilter(value)}
              disabled={!preview}
            >
              {filter}
            </button>
          );
        })}
      </section>

      <section className="upload-table-wrap">
        {preview ? (
          <>
            <div className="upload-table-toolbar">
              <label className="upload-search">
                <FiSearch />
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search merchant, ID, invoice, status..." />
              </label>
              <div className="upload-table-actions">
                <div className="upload-column-menu-wrap">
                  <button className="secondary-button" onClick={() => setShowColumns((value) => !value)}>
                    <FiColumns /> Columns
                  </button>
                  {showColumns && (
                    <div className="upload-column-menu">
                      {TABLE_COLUMNS.map((column) => (
                        <label key={column.key}>
                          <input type="checkbox" checked={visibleColumns[column.key]} onChange={() => toggleColumn(column.key)} />
                          {column.label}
                        </label>
                      ))}
                    </div>
                  )}
                </div>
                <button className="secondary-button" onClick={exportPreviewCsv} disabled={!filteredRows.length}>
                  <FiDownload /> Export CSV
                </button>
              </div>
            </div>
            <table className="upload-table">
              <thead>
                <tr>
                  {activeColumns.map((column) => (
                    <th key={column.key} style={{ width: column.width }}>
                      <button className="upload-sort-button" onClick={() => toggleSort(column.key)}>
                        {column.label}
                        <span>{sort.key === column.key ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}</span>
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row, index) => (
                  <tr key={row.id || `${row.transaction_id}-${index}`}>
                    {activeColumns.map((column) => (
                      <td key={column.key}>{renderCell(column.key, row, page * PAGE_SIZE + index)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="upload-pagination">
              <span>
                Showing <b>{filteredRows.length ? page * PAGE_SIZE + 1 : 0}-{Math.min(filteredRows.length, page * PAGE_SIZE + PAGE_SIZE)}</b> of <b>{filteredRows.length}</b>
              </span>
              <div>
                <button className="icon-button" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))} title="Previous page">
                  <FiChevronLeft />
                </button>
                <span className="upload-page-chip">Page {page + 1} / {pageCount}</span>
                <button className="icon-button" disabled={page + 1 >= pageCount} onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))} title="Next page">
                  <FiChevronRight />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="upload-empty-state">
            <div className="upload-empty-visual">
              <FiFileText />
              <span className="upload-empty-pulse" />
            </div>
            <div>
              <strong>No validated preview yet</strong>
              <p>Upload a spreadsheet to see extracted rows, validation status, transaction types, and approval routing here.</p>
            </div>
            <div className="upload-empty-metrics">
              <span><b>10 MB</b> max file</span>
              <span><b>XLSX/CSV</b> supported</span>
              <span><b>Live</b> queue refresh</span>
            </div>
          </div>
        )}
      </section>

      <section className="upload-submit-row">
        <div className="upload-submit-info">
          {preview ? (
            <>Submitting <span>{rows.length} transactions</span> for manager review</>
          ) : (
            <>Latest uploads in your queue: <span>{uploads.length}</span></>
          )}
        </div>
        <button className="primary-button upload-submit-button" disabled={!preview}>
          <FiSend size={16} /> {preview ? "In review queue" : "Submit for review"}
        </button>
      </section>
    </div>
  );
}

function renderCell(key, row, index) {
  const renderers = {
    merchant_name: <MerchantCell merchant={row.merchant_name} />,
    transaction_id: <span className="mono-cell">{row.transaction_id || `Row ${index + 1}`}</span>,
    transaction_date: formatDate(row.transaction_date),
    amount: <span className="amount-cell">{formatMoney(row.amount)}</span>,
    transaction_type: <TypePill type={row.transaction_type} />,
    payment_method: row.payment_method || "-",
    status: <StatusPill status={row.status || "Pending"} />,
    invoice_id: <span className="muted-cell">{row.invoice_id || "-"}</span>
  };
  return renderers[key] ?? "-";
}

function compareRows(a, b, sort) {
  const first = normalizeSortValue(a[sort.key], sort.key);
  const second = normalizeSortValue(b[sort.key], sort.key);
  if (first < second) return sort.direction === "asc" ? -1 : 1;
  if (first > second) return sort.direction === "asc" ? 1 : -1;
  return 0;
}

function normalizeSortValue(value, key) {
  if (key === "amount") return Number(value || 0);
  if (key === "transaction_date") return value ? new Date(value).getTime() : 0;
  return String(value || "").toLowerCase();
}

function formatCsvValue(value) {
  if (value === null || value === undefined) return "";
  return value;
}

function UploadSignal({ label, value, detail, icon: Icon, delay }) {
  return (
    <div className="upload-signal-card fintech-card" style={{ animation: `staggerIn 0.4s ease-out ${0.12 + delay}s both` }}>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
      <div className="upload-signal-icon">
        <Icon />
      </div>
    </div>
  );
}

function WorkflowStep({ active, done, icon: Icon, label, detail }) {
  return (
    <div className={`workflow-step ${active ? "is-active" : ""} ${done ? "is-done" : ""}`}>
      <div className="workflow-step-icon">
        <Icon />
      </div>
      <div>
        <strong>{label}</strong>
        <span>{detail}</span>
      </div>
    </div>
  );
}

function MerchantCell({ merchant }) {
  const name = merchant || "Unknown";
  const brandKey = Object.keys(MERCHANTS).find((key) => name.toLowerCase().includes(key.toLowerCase()));
  const config = MERCHANTS[brandKey] || {
    bg: "#155E58",
    color: "#fff",
    initials: name.split(" ").map((word) => word[0]).join("").toUpperCase().slice(0, 2) || "NA"
  };

  return (
    <div className="merchant-cell">
      <div className="merchant-logo" style={{ background: config.bg }}>
        {config.icon && (
          <img
            src={config.icon}
            alt=""
            onError={(event) => {
              event.currentTarget.style.display = "none";
              const fallback = event.currentTarget.nextElementSibling;
              if (fallback) fallback.style.display = "inline";
            }}
          />
        )}
        <span style={{ color: config.color, display: config.icon ? "none" : "inline" }}>
          {config.initials}
        </span>
      </div>
      <span className="merchant-name">{name}</span>
    </div>
  );
}

function TypePill({ type }) {
  const config = TYPE_STYLES[type] || { bg: "#E7F5F1", color: "#155E58" };
  return (
    <span className="upload-pill" style={{ background: config.bg, color: config.color }}>
      {type || "-"}
    </span>
  );
}

function StatusPill({ status }) {
  const config = STATUS_STYLES[status] || { bg: "#E7F5F1", color: "#155E58" };
  return (
    <span className="upload-pill" style={{ background: config.bg, color: config.color }}>
      <span className="upload-pill-dot" style={{ background: config.color }} />
      {formatStatus(status)}
    </span>
  );
}

function formatMoney(value) {
  return `\u20b9${Number(value || 0).toLocaleString("en-IN")}`;
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("en-IN");
}

function formatFileSize(size) {
  if (!size) return "0 KB";
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`;
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}

function formatStatus(status) {
  return String(status || "-").replaceAll("_", " ");
}
