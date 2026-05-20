import React from "react";
import { useEffect, useMemo, useState } from "react";
import { FiChevronLeft, FiChevronRight, FiColumns, FiDownload, FiSearch } from "react-icons/fi";

export default function DataTable({ columns = [], rows = [], pageSize = 8, title = "Extracted Data Preview" }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState({ key: columns[0] || "", direction: "asc" });
  const [showColumns, setShowColumns] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState(() => Object.fromEntries(columns.map((column) => [column, true])));

  useEffect(() => {
    setVisibleColumns((current) => {
      const next = Object.fromEntries(columns.map((column) => [column, current[column] ?? true]));
      return next;
    });
    setSort((current) => ({ key: current.key || columns[0] || "", direction: current.direction || "asc" }));
  }, [columns]);

  const activeColumns = columns.filter((column) => visibleColumns[column]);

  const filteredRows = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const nextRows = normalized
      ? rows.filter((row) => JSON.stringify(row).toLowerCase().includes(normalized))
      : rows;

    if (!sort.key) return nextRows;
    return [...nextRows].sort((a, b) => {
      const first = normalizeSortValue(a[sort.key]);
      const second = normalizeSortValue(b[sort.key]);
      if (first < second) return sort.direction === "asc" ? -1 : 1;
      if (first > second) return sort.direction === "asc" ? 1 : -1;
      return 0;
    });
  }, [query, rows, sort]);

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const visibleRows = filteredRows.slice(page * pageSize, (page + 1) * pageSize);

  useEffect(() => {
    setPage(0);
  }, [query, sort, rows]);

  function toggleSort(column) {
    setSort((current) => ({
      key: column,
      direction: current.key === column && current.direction === "asc" ? "desc" : "asc"
    }));
  }

  function toggleColumn(column) {
    setVisibleColumns((current) => {
      const enabledCount = Object.values(current).filter(Boolean).length;
      if (current[column] && enabledCount <= 1) return current;
      return { ...current, [column]: !current[column] };
    });
  }

  function exportCsv() {
    if (!filteredRows.length) return;
    const csv = [
      activeColumns,
      ...filteredRows.map((row) => activeColumns.map((column) => row[column] ?? ""))
    ]
      .map((line) => line.map((cell) => `"${String(cell).replaceAll("\"", "\"\"")}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ledgerflow-table-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="elevated-panel data-table-card">
      <div className="data-table-header">
        <div>
          <div className="data-table-title">{title}</div>
          <div className="data-table-subtitle">{filteredRows.length} rows available</div>
        </div>
        <div className="data-table-actions">
          <label className="upload-search data-table-search">
            <FiSearch />
            <input
              placeholder="Search table"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <div className="upload-column-menu-wrap">
            <button className="secondary-button" onClick={() => setShowColumns((value) => !value)}>
              <FiColumns /> Columns
            </button>
            {showColumns && (
              <div className="upload-column-menu">
                {columns.map((column) => (
                  <label key={column}>
                    <input type="checkbox" checked={Boolean(visibleColumns[column])} onChange={() => toggleColumn(column)} />
                    {column}
                  </label>
                ))}
              </div>
            )}
          </div>
          <button className="secondary-button" onClick={exportCsv} disabled={!filteredRows.length}>
            <FiDownload /> Export
          </button>
        </div>
      </div>

      <div className="data-table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {activeColumns.map((column) => (
                <th key={column}>
                  <button className="upload-sort-button" onClick={() => toggleSort(column)}>
                    {column}
                    <span>{sort.key === column ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, index) => (
              <tr key={`${page}-${index}`}>
                {activeColumns.map((column) => (
                  <td key={column}>{String(row[column] ?? "")}</td>
                ))}
              </tr>
            ))}
            {!visibleRows.length && (
              <tr>
                <td colSpan={Math.max(1, activeColumns.length)}>
                  <div className="data-table-empty">
                    <strong>No matching rows</strong>
                    <span>Adjust search terms or column filters to widen the result set.</span>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="upload-pagination">
        <span>
          Showing <b>{filteredRows.length ? page * pageSize + 1 : 0}-{Math.min(filteredRows.length, page * pageSize + pageSize)}</b> of <b>{filteredRows.length}</b>
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
    </div>
  );
}

function normalizeSortValue(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return value;
  const asNumber = Number(value);
  if (!Number.isNaN(asNumber) && String(value).trim() !== "") return asNumber;
  const asDate = new Date(value).getTime();
  if (!Number.isNaN(asDate)) return asDate;
  return String(value).toLowerCase();
}
