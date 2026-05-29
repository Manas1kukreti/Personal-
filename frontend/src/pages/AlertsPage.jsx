importimport React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FiAlertTriangle, FiArrowRight, FiMoreVertical, FiRefreshCw, FiSearch, FiX } from "react-icons/fi";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useWebSocket } from "../hooks/useWebSocket.js";

export default function AlertsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [entryFilter, setEntryFilter] = useState(searchParams.get("entry") || "");
  const [accountFilter, setAccountFilter] = useState(searchParams.get("account") || "");
  const [statusFilter, setStatusFilter] = useState("");
  const [openMenuId, setOpenMenuId] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);

  const syncUrlFilters = useCallback(
    (nextEntry, nextAccount) => {
      const params = new URLSearchParams();
      if (nextEntry.trim()) params.set("entry", nextEntry.trim());
      if (nextAccount.trim()) params.set("account", nextAccount.trim());
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (entryFilter.trim()) params.set("entry", entryFilter.trim());
      if (accountFilter.trim()) params.set("account", accountFilter.trim());
      const response = await api.get(`/alerts${params.toString() ? `?${params.toString()}` : ""}`);
      setAlerts(Array.isArray(response.data) ? response.data : []);
    } finally {
      setLoading(false);
    }
  }, [accountFilter, entryFilter]);

  useEffect(() => {
    setEntryFilter(searchParams.get("entry") || "");
    setAccountFilter(searchParams.get("account") || "");
  }, [searchParams]);

  useEffect(() => {
    loadAlerts().catch(() => setAlerts([]));
  }, [loadAlerts]);

  useWebSocket(
    "notifications",
    useCallback((event) => {
      if (event.event !== "dtcd_alert") return;
      setAlerts((current) => [event.payload, ...current.filter((alert) => alert.id !== event.payload.id)]);
    }, []),
  );

  const filteredAlerts = useMemo(() => {
    const normalizedStatus = statusFilter.trim().toLowerCase();
    return alerts.filter((alert) => !normalizedStatus || String(alert.status || "").toLowerCase() === normalizedStatus);
  }, [alerts, statusFilter]);

  function updateEntryFilter(value) {
    setEntryFilter(value);
    syncUrlFilters(value, accountFilter);
  }

  function updateAccountFilter(value) {
    setAccountFilter(value);
    syncUrlFilters(entryFilter, value);
  }

  function clearFilters() {
    setEntryFilter("");
    setAccountFilter("");
    setStatusFilter("");
    setSearchParams({}, { replace: true });
  }

  function openDetails(alert) {
    setSelectedAlert(alert);
    setOpenMenuId(null);
  }

  return (
    <div className="lf-alerts-page">
      <section className="lf-alerts-header">
        <div>
          <h1>Validation Alerts</h1>
          <p>Debit and Credit Transaction failures that need review before ledger processing continues.</p>
        </div>
        <button className="secondary-button" onClick={loadAlerts} disabled={loading} type="button">
          <FiRefreshCw size={16} />
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </section>

      <section className="lf-alerts-filters">
        <label className="lf-alerts-search">
          <FiSearch size={17} />
          <input value={entryFilter} onChange={(event) => updateEntryFilter(event.target.value)} placeholder="Filter Entry No" />
        </label>
        <label className="lf-alerts-search">
          <FiSearch size={17} />
          <input value={accountFilter} onChange={(event) => updateAccountFilter(event.target.value)} placeholder="Filter Account Code" />
        </label>
        <select className="form-input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="">All statuses</option>
          <option value="failed">Failed</option>
        </select>
        <button className="secondary-button" onClick={clearFilters} type="button">
          <FiX size={16} />
          Clear
        </button>
      </section>

      <section className="lf-alerts-table-wrap">
        <table className="lf-alerts-table">
          <thead>
            <tr>
              <th>Entry No</th>
              <th>Account Code</th>
              <th>Sub Account</th>
              <th>Difference</th>
              <th>Status</th>
              <th>Received At</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {filteredAlerts.map((alert) => (
              <tr key={alert.id}>
                <td className="mono-cell">{alert.entry_no}</td>
                <td className="mono-cell">{alert.account_code}</td>
                <td>{alert.sub_account}</td>
                <td>{formatCurrency(alert.difference)}</td>
                <td><span className="lf-alert-status">{alert.status || "FAILED"}</span></td>
                <td>{formatReceivedAt(alert.created_at)}</td>
                <td className="lf-alert-actions-cell">
                  <button
                    className="lf-alert-kebab"
                    type="button"
                    aria-label="Open alert actions"
                    aria-expanded={openMenuId === alert.id}
                    onClick={() => setOpenMenuId((current) => (current === alert.id ? null : alert.id))}
                  >
                    <FiMoreVertical size={16} />
                  </button>
                  {openMenuId === alert.id && (
                    <div className="lf-alert-row-menu">
                      <button type="button" onClick={() => openDetails(alert)}>
                        View details
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!filteredAlerts.length && (
          <div className="lf-alerts-empty">
            <FiAlertTriangle size={22} />
            <strong>No validation alerts found</strong>
            <span>DTCD failures will appear here as soon as the agent posts them.</span>
          </div>
        )}
      </section>

      {selectedAlert && (
        <TransactionDetailModal alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
      )}
    </div>
  );
}

function TransactionDetailModal({ alert, onClose }) {
  const debit = getDebitDetail(alert);
  const credit = getCreditDetail(alert);
  const detailRows = [
    ["Transaction ID", alert.transaction_id || alert.transactionId || alert.id],
    ["Upload ID", alert.upload_id || alert.uploadId || "-"],
    ["Entry No", alert.entry_no || "-"],
    ["Received At", formatReceivedAt(alert.created_at || alert.received_at)],
    ["Status", alert.status || "FAILED"],
    ["Difference", formatCurrency(alert.difference)],
  ];

  return (
    <div className="lf-alert-detail-overlay" role="presentation" onClick={onClose}>
      <section
        className="lf-alert-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="alert-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="lf-alert-detail-header">
          <div>
            <h2 id="alert-detail-title">Transaction Detail</h2>
            <p>{alert.entry_no ? `Entry ${alert.entry_no}` : "Validation alert"}</p>
          </div>
          <button className="lf-alert-detail-close" type="button" aria-label="Close details" onClick={onClose}>
            <FiX size={18} />
          </button>
        </header>

        <div className="lf-alert-flow">
          <FlowCard tone="debit" title="From (Debit)" detail={debit} amountLabel="Debit amount" />
          <div className="lf-alert-flow-arrow">
            <FiArrowRight size={22} />
            <span>Δ {formatCurrency(alert.difference)}</span>
          </div>
          <FlowCard tone="credit" title="To (Credit)" detail={credit} amountLabel="Credit amount" />
        </div>

        <dl className="lf-alert-detail-grid">
          {detailRows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value || "-"}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}

function FlowCard({ tone, title, detail, amountLabel }) {
  return (
    <article className={`lf-alert-flow-card lf-alert-flow-card--${tone}`}>
      <span>{title}</span>
      <strong>{detail.name}</strong>
      <p>{detail.code}</p>
      <div>
        <small>{amountLabel}</small>
        <b>{formatCurrency(detail.amount)}</b>
      </div>
    </article>
  );
}

function getDebitDetail(alert) {
  return {
    name: alert.debit_account_name || alert.from_account_name || alert.sub_account || "-",
    code: alert.debit_account_code || alert.from_account_code || alert.account_code || "-",
    amount: alert.debit_amount ?? alert.from_amount ?? alert.difference ?? 0,
  };
}

function getCreditDetail(alert) {
  return {
    name: alert.credit_account_name || alert.to_account_name || alert.credit_sub_account || "-",
    code: alert.credit_account_code || alert.to_account_code || "-",
    amount: alert.credit_amount ?? alert.to_amount ?? 0,
  };
}

function formatCurrency(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  });
}

function formatReceivedAt(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}
