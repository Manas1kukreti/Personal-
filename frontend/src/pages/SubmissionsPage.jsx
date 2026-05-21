import React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FiArchive, FiDownload, FiMessageSquare, FiRefreshCw, FiSearch, FiUploadCloud } from "react-icons/fi";
import { api } from "../api/client.js";
import CommentThread from "../components/CommentThread.jsx";

export default function SubmissionsPage() {
  const reuploadInputRef = useRef(null);
  const [uploads, setUploads] = useState([]);
  const [selectedUpload, setSelectedUpload] = useState(null);
  const [reuploadTarget, setReuploadTarget] = useState(null);
  const [reuploading, setReuploading] = useState("");
  const [reuploadError, setReuploadError] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");

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

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();
    return uploads.filter((upload) => {
      const matchesStatus = !status || upload.status === status;
      const matchesSearch = !search || [upload.filename, upload.uploader_name, upload.status]
        .some((value) => String(value || "").toLowerCase().includes(search));
      return matchesStatus && matchesSearch;
    });
  }, [uploads, query, status]);

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
        upload.reviewed_at || ""
      ])
    ]
      .map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll("\"", "\"\"")}"`).join(","))
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
      await api.post(`/uploads/${reuploadTarget.id}/reupload`, form, { headers: { "Content-Type": "multipart/form-data" } });
      setReuploadTarget(null);
      await loadUploads();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setReuploadError(typeof detail === "string" ? detail : "Re-upload failed. Please check the file and try again.");
    } finally {
      setReuploading("");
    }
  }

  return (
    <div className="app-page submissions-page">
      <input
        ref={reuploadInputRef}
        className="hidden"
        type="file"
        accept=".xlsx,.csv"
        onChange={(event) => submitReupload(event.target.files?.[0])}
      />

      <section className="submissions-header">
        <div>
          <h1>Submissions</h1>
          <p>Audit upload history, review status, and exported transaction batches.</p>
        </div>
        <button className="secondary-button" onClick={loadUploads}>
          <FiRefreshCw /> Refresh
        </button>
      </section>

      <section className="submissions-toolbar elevated-panel">
        <label className="upload-search">
          <FiSearch />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search filename, uploader, status..." />
        </label>
        <select className="form-input" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="declined">Declined</option>
          <option value="reupload_requested">Re-upload requested</option>
        </select>
        <button className="primary-button" onClick={exportCsv} disabled={!filtered.length}>
          <FiDownload /> Export
        </button>
      </section>

      <section className="elevated-panel submissions-table-card">
        {reuploadError && <div className="comment-error">{reuploadError}</div>}
        <table className="submissions-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Rows</th>
              <th>Columns</th>
              <th>Uploader</th>
              <th>Created</th>
              <th>Version</th>
              <th>Conversation</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((upload) => (
              <tr key={upload.id} className={selectedUpload?.id === upload.id ? "is-selected" : ""}>
                <td>
                  <div className="submission-file">
                    <span><FiArchive /></span>
                    <div className="submission-file-copy">
                      <strong>{upload.filename}</strong>
                      {upload.status === "reupload_requested" && (
                        <em>Re-upload Required</em>
                      )}
                    </div>
                  </div>
                </td>
                <td><span className={`status-badge status-${upload.status}`}>{upload.status}</span></td>
                <td className="mono">{Number(upload.total_rows || 0).toLocaleString("en-IN")}</td>
                <td className="mono">{upload.total_columns || 0}</td>
                <td>{upload.uploader_name || "-"}</td>
                <td>{upload.created_at ? new Date(upload.created_at).toLocaleString("en-IN") : "-"}</td>
                <td><span className="version-chip">v{upload.version_number || 1}</span></td>
                <td>
                  <button className="secondary-button submission-comment-button" onClick={() => setSelectedUpload(upload)}>
                    <FiMessageSquare /> Open
                  </button>
                </td>
                <td>
                  {upload.status === "reupload_requested" ? (
                    <button className="primary-button submission-comment-button" onClick={() => startReupload(upload)} disabled={reuploading === upload.id}>
                      <FiUploadCloud /> {reuploading === upload.id ? "Uploading..." : "Re-upload"}
                    </button>
                  ) : (
                    <span className="muted-cell">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && (
          <div className="submissions-empty">
            <FiArchive />
            <strong>No submissions found</strong>
            <span>Upload activity and review history will appear here.</span>
          </div>
        )}
      </section>

      {selectedUpload && (
        <section className="elevated-panel submissions-conversation-panel">
          <div className="submissions-conversation-header">
            <div>
              <h2>{selectedUpload.filename}</h2>
              <p>{selectedUpload.status} - {Number(selectedUpload.total_rows || 0).toLocaleString("en-IN")} rows</p>
            </div>
            <button className="secondary-button" onClick={() => setSelectedUpload(null)}>Close</button>
          </div>
          <CommentThread submissionId={selectedUpload.id} title="Submission conversation" />
        </section>
      )}
    </div>
  );
}
