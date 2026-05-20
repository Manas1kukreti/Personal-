import React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FiArchive, FiDownload, FiRefreshCw, FiSearch } from "react-icons/fi";
import { api } from "../api/client.js";

export default function SubmissionsPage() {
  const [uploads, setUploads] = useState([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");

  const loadUploads = useCallback(async () => {
    const response = await api.get("/uploads");
    setUploads(response.data);
  }, []);

  useEffect(() => {
    loadUploads().catch(() => setUploads([]));
  }, [loadUploads]);

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

  return (
    <div className="app-page submissions-page">
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
        <table className="submissions-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Rows</th>
              <th>Columns</th>
              <th>Uploader</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((upload) => (
              <tr key={upload.id}>
                <td>
                  <div className="submission-file">
                    <span><FiArchive /></span>
                    <strong>{upload.filename}</strong>
                  </div>
                </td>
                <td><span className={`status-badge status-${upload.status}`}>{upload.status}</span></td>
                <td className="mono">{Number(upload.total_rows || 0).toLocaleString("en-IN")}</td>
                <td className="mono">{upload.total_columns || 0}</td>
                <td>{upload.uploader_name || "-"}</td>
                <td>{upload.created_at ? new Date(upload.created_at).toLocaleString("en-IN") : "-"}</td>
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
    </div>
  );
}
