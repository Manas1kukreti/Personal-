import React from "react";
import { useMemo, useState } from "react";
import { FiChevronDown, FiSearch } from "react-icons/fi";

export default function DataTable({ columns = [], rows = [], pageSize = 8 }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);

  const filteredRows = useMemo(() => {
    const normalized = query.toLowerCase();
    if (!normalized) return rows;
    return rows.filter((row) => JSON.stringify(row).toLowerCase().includes(normalized));
  }, [query, rows]);

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const visibleRows = filteredRows.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div className="elevated-panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-4">
        <div>
          <div className="text-sm font-bold text-ink">Extracted Data Preview</div>
          <div className="text-xs text-muted">{filteredRows.length} rows available</div>
        </div>
        <label className="flex min-w-64 items-center gap-2 border border-line bg-slate-50 px-3 py-2" style={{ borderRadius: 8 }}>
          <FiSearch className="text-muted" />
          <input
            className="w-full border-0 bg-transparent text-sm text-ink outline-none placeholder:text-slate-400"
            placeholder="Search preview"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(0);
            }}
          />
        </label>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-muted">
            <tr>
              {columns.map((column) => (
                <th key={column} className="whitespace-nowrap px-4 py-3 font-bold">
                  <span className="inline-flex items-center gap-1">
                    {column}
                    <FiChevronDown className="text-slate-300" />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {visibleRows.map((row, index) => (
              <tr key={`${page}-${index}`} className="hover:bg-slate-50">
                {columns.map((column) => (
                  <td key={column} className="max-w-72 truncate px-4 py-3 text-slate-700">{String(row[column] ?? "")}</td>
                ))}
              </tr>
            ))}
            {!visibleRows.length && (
              <tr>
                <td colSpan={Math.max(1, columns.length)} className="px-4 py-10 text-center text-sm text-muted">
                  No rows match the current search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t border-line p-4 text-sm">
        <button className="secondary-button" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>
          Previous
        </button>
        <span className="text-slate-500">Page {page + 1} of {pageCount}</span>
        <button className="secondary-button" disabled={page + 1 >= pageCount} onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))}>
          Next
        </button>
      </div>
    </div>
  );
}
