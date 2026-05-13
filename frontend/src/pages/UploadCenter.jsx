import React from "react";
import { useCallback, useMemo, useState } from "react";
import { FiAlertCircle, FiCheckCircle, FiFileText, FiRefreshCw, FiUploadCloud } from "react-icons/fi";
import { api } from "../api/client.js";
import DataTable from "../components/DataTable.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

export default function UploadCenter() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState("");

  useWebSocket("uploads", useCallback((event) => {
    if (event.event === "upload_progress" || event.event === "upload.progress") {
      setProgress(event.payload.progress || 0);
      setMessage(event.payload.filename ? `${event.payload.filename} processed` : "Upload processing");
    }
    if (event.event === "upload_status" || event.event === "approval.decision") {
      setMessage(`Upload ${event.payload.status}`);
    }
  }, []));

  const isValid = useMemo(() => file && [".xlsx", ".csv"].some((ext) => file.name.toLowerCase().endsWith(ext)), [file]);
  const isTooLarge = file && file.size > MAX_FILE_SIZE;
  const canSubmit = isValid && !isTooLarge;

  async function submitUpload() {
    if (!canSubmit) return;
    const form = new FormData();
    form.append("file", file);
    setProgress(5);
    setError("");
    try {
      const response = await api.post("/uploads", form, { headers: { "Content-Type": "multipart/form-data" } });
      setPreview(response.data);
      setProgress(100);
      setMessage("Preview generated and sent to manager queue");
    } catch (err) {
      setProgress(0);
      setError(err.response?.data?.detail || "Upload failed. Please check the file and try again.");
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
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setProgress(0);
    setMessage("");
    setError("");
  }

  return (
    <div className="space-y-5">
      <section className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink">Upload Center</h1>
          <p className="text-sm text-muted">Upload, validate, preview, and route spreadsheets to manager review.</p>
        </div>
        <div className="chip">
          <span className="status-dot bg-brand" />
          XLSX / CSV up to 10 MB
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[420px_1fr]">
        <div className="elevated-panel p-5">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-ink">Upload Workspace</h2>
              <p className="text-sm text-muted">Files enter staging before approval.</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center bg-teal-50 text-brand" style={{ borderRadius: 8 }}>
              <FiUploadCloud />
            </div>
          </div>
          <div
            className={`flex min-h-64 flex-col items-center justify-center border-2 border-dashed px-5 text-center transition ${
              drag ? "border-brand bg-teal-50" : "border-line bg-slate-50 hover:border-brand"
            }`}
            style={{ borderRadius: 8 }}
            onDragOver={(event) => {
              event.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={onDrop}
          >
            <FiFileText className="mb-3 text-4xl text-brand" />
            <label className="cursor-pointer text-sm font-bold text-ink">
              Drop spreadsheet or browse files
              <input className="hidden" type="file" accept=".xlsx,.csv" onChange={(event) => event.target.files?.[0] && selectFile(event.target.files[0])} />
            </label>
            <p className="mt-2 text-xs text-muted">Dynamic parsing supports .xlsx and .csv files.</p>
          </div>
          {file && (
            <div className="mt-4 border border-line bg-white p-3 text-sm" style={{ borderRadius: 8 }}>
              <div className="mono truncate text-xs font-bold text-accent">{file.name}</div>
              <div className="mt-1 flex flex-wrap gap-2 text-xs">
                <span className={isValid ? "text-success" : "text-danger"}>{isValid ? "File type accepted" : "Invalid file type"}</span>
                <span className={isTooLarge ? "text-danger" : "text-muted"}>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              </div>
            </div>
          )}
          <div className="mt-4">
            <div className="mb-2 flex justify-between text-xs font-semibold text-muted">
              <span>Upload progress</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 overflow-hidden bg-slate-100" style={{ borderRadius: 8 }}>
              <div className="h-full bg-brand transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button className="primary-button flex-1" disabled={!canSubmit} onClick={submitUpload}>
            <FiCheckCircle /> Submit for Preview
            </button>
            <button className="icon-button" onClick={reset} title="Reset upload"><FiRefreshCw /></button>
          </div>
          {message && <p className="mt-3 text-sm text-muted">{message}</p>}
          {(error || isTooLarge) && (
            <div className="mt-3 flex gap-2 border border-red-200 bg-red-50 p-3 text-sm text-danger" style={{ borderRadius: 8 }}>
              <FiAlertCircle className="mt-0.5 shrink-0" />
              <span>{error || "File is larger than the 10 MB limit."}</span>
            </div>
          )}
        </div>
        <div className="elevated-panel p-5">
          <h2 className="text-base font-bold text-ink">Dynamic Extracted Preview</h2>
          <p className="mb-4 text-sm text-muted">Columns, data types, and validation results are generated from the spreadsheet.</p>
          {preview ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Metric label="Rows" value={preview.total_rows} />
              <Metric label="Columns" value={preview.total_columns} />
              <Metric label="Status" value={preview.status} />
                <Metric label="Schema" value={preview.validation?.valid === false ? "Review" : "Valid"} />
              </div>
              <div className="border border-line bg-slate-50 p-3" style={{ borderRadius: 8 }}>
                <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Detected Types</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(preview.detected_types || {}).map(([column, type]) => (
                    <span className="chip bg-white" key={column}>{column}: <span className="mono text-accent">{type}</span></span>
                  ))}
                </div>
              </div>
              {preview.validation?.missing_columns?.length > 0 && (
                <div className="border border-amber-200 bg-amber-50 p-3 text-sm text-warning" style={{ borderRadius: 8 }}>
                  Missing required columns: {preview.validation.missing_columns.join(", ")}
                </div>
              )}
            </div>
          ) : (
            <div className="flex min-h-64 items-center justify-center border border-line bg-slate-50 text-sm text-muted" style={{ borderRadius: 8 }}>
              No preview yet
            </div>
          )}
        </div>
      </section>
      {preview && <DataTable columns={preview.columns} rows={preview.preview_rows} />}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="border border-line bg-white p-4 shadow-soft" style={{ borderRadius: 8 }}>
      <div className="text-xs font-bold uppercase tracking-wide text-muted">{label}</div>
      <div className="mono mt-2 truncate text-xl font-semibold text-ink">{value}</div>
    </div>
  );
}
