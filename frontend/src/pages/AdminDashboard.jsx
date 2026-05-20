import React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FiRefreshCw, FiRepeat, FiSearch, FiUserCheck, FiUsers } from "react-icons/fi";
import { api } from "../api/client.js";

export default function AdminDashboard() {
  const [managers, setManagers] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [managerByEmployee, setManagerByEmployee] = useState({});
  const [message, setMessage] = useState("");
  const [busyEmployee, setBusyEmployee] = useState("");
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [assignmentFilter, setAssignmentFilter] = useState("");

  const loadAdminData = useCallback(async () => {
    const [managerResponse, employeeResponse] = await Promise.all([
      api.get("/admin/managers"),
      api.get("/admin/employees")
    ]);
    setManagers(managerResponse.data);
    setEmployees(employeeResponse.data);
    setManagerByEmployee(
      Object.fromEntries(employeeResponse.data.map((employee) => [employee.id, employee.manager_id || ""]))
    );
  }, []);

  useEffect(() => {
    loadAdminData();
  }, [loadAdminData]);

  const unassignedCount = useMemo(() => employees.filter((employee) => !employee.manager_id).length, [employees]);
  const filteredEmployees = useMemo(() => {
    const search = employeeSearch.trim().toLowerCase();
    return employees.filter((employee) => {
      const assigned = Boolean(employee.manager_id);
      const matchesAssignment = !assignmentFilter || (assignmentFilter === "assigned" ? assigned : !assigned);
      const matchesSearch = !search || [employee.name, employee.email, employee.assignment_status]
        .some((value) => String(value || "").toLowerCase().includes(search));
      return matchesAssignment && matchesSearch;
    });
  }, [assignmentFilter, employeeSearch, employees]);

  function updateSelection(employeeId, managerId) {
    setManagerByEmployee((current) => ({ ...current, [employeeId]: managerId }));
  }

  async function saveAssignment(employee) {
    const managerId = managerByEmployee[employee.id];
    if (!managerId) return;
    const endpoint = employee.manager_id ? "/admin/reassign" : "/admin/assign";
    setBusyEmployee(employee.id);
    setMessage("");
    try {
      await api.post(endpoint, { employee_id: employee.id, manager_id: managerId });
      setMessage(`${employee.name} assignment updated`);
      await loadAdminData();
    } finally {
      setBusyEmployee("");
    }
  }

  return (
    <div className="space-y-5 app-page">
      <section className="flex flex-wrap items-center justify-between gap-3 animate-slide-in-top">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Admin Dashboard</h1>
          <p className="text-sm text-muted">Assign employees to managers and monitor ownership coverage.</p>
        </div>
        <button className="secondary-button transition-all-smooth hover:rotate-180" onClick={loadAdminData}><FiRefreshCw /> Refresh</button>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="animate-stagger-in-1" style={{ animationDelay: "0.1s" }}>
          <Stat icon={FiUsers} label="Managers" value={managers.length} />
        </div>
        <div className="animate-stagger-in-2" style={{ animationDelay: "0.15s" }}>
          <Stat icon={FiUserCheck} label="Employees" value={employees.length} />
        </div>
        <div className="animate-stagger-in-3" style={{ animationDelay: "0.2s" }}>
          <Stat icon={FiRepeat} label="Unassigned" value={unassignedCount} />
        </div>
      </section>

      {message && <div className="border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-success animate-fade-in" style={{ borderRadius: 8 }}>{message}</div>}

      <section className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <div className="elevated-panel overflow-hidden animate-slide-in-left" style={{ animationDelay: "0.25s" }}>
          <div className="border-b border-line p-4">
            <h2 className="text-base font-bold text-ink">Managers</h2>
            <p className="text-sm text-muted">Available reviewers for assignment.</p>
          </div>
          <div className="divide-y divide-line">
            {managers.map((manager, index) => (
              <div 
                key={manager.id} 
                className="p-4 transition-all-smooth hover:bg-slate-50 hover:shadow-soft" 
                style={{ animation: `staggerIn 0.4s ease-out ${0.3 + index * 0.06}s both` }}
              >
                <div className="font-bold text-ink">{manager.name}</div>
                <div className="text-sm text-muted">{manager.email}</div>
                <div className="mt-2 text-xs font-semibold text-accent">{manager.assigned_employee_count} assigned employees</div>
              </div>
            ))}
            {!managers.length && <Empty label="No managers found" />}
          </div>
        </div>

        <div className="elevated-panel overflow-hidden animate-slide-in-right" style={{ animationDelay: "0.25s" }}>
          <div className="border-b border-line p-4">
            <h2 className="text-base font-bold text-ink">Employees</h2>
            <p className="text-sm text-muted">Assignment status and manager routing.</p>
          </div>
          <div className="queue-toolbar">
            <label className="upload-search">
              <FiSearch />
              <input value={employeeSearch} onChange={(event) => setEmployeeSearch(event.target.value)} placeholder="Search employees" />
            </label>
            <select className="form-input" value={assignmentFilter} onChange={(event) => setAssignmentFilter(event.target.value)}>
              <option value="">All</option>
              <option value="assigned">Assigned</option>
              <option value="unassigned">Unassigned</option>
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Employee</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Manager</th>
                  <th className="px-4 py-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {filteredEmployees.map((employee, index) => (
                  <tr 
                    key={employee.id} 
                    className="hover:bg-slate-50 transition-colors-smooth" 
                    style={{ animation: `staggerIn 0.3s ease-out ${0.35 + index * 0.04}s both` }}
                  >
                    <td className="px-4 py-3">
                      <div className="font-bold text-ink">{employee.name}</div>
                      <div className="text-xs text-muted">{employee.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`status-badge ${employee.manager_id ? "status-approved" : "status-pending"} transition-all-smooth`}>
                        <span className="status-dot bg-current" />
                        {employee.assignment_status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        className="form-input min-w-56"
                        value={managerByEmployee[employee.id] || ""}
                        onChange={(event) => updateSelection(employee.id, event.target.value)}
                      >
                        <option value="">Select manager</option>
                        {managers.map((manager) => (
                          <option key={manager.id} value={manager.id}>{manager.name}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        className="primary-button transition-all-smooth hover:shadow-lg active:scale-95"
                        disabled={!managerByEmployee[employee.id] || busyEmployee === employee.id}
                        onClick={() => saveAssignment(employee)}
                      >
                        {employee.manager_id ? <FiRepeat /> : <FiUserCheck />}
                        {employee.manager_id ? "Reassign" : "Assign"}
                      </button>
                    </td>
                  </tr>
                ))}
                {!filteredEmployees.length && <tr><td colSpan="4"><Empty label="No employees found" /></td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="elevated-panel p-4 transition-all-smooth hover:shadow-lg hover:-translate-y-1">
      <div className="flex items-center justify-between">
        <div className="text-xs font-bold uppercase tracking-wide text-muted">{label}</div>
        <div className="flex h-9 w-9 items-center justify-center bg-highlight-bg text-accent transition-all-smooth hover:bg-tab-bg" style={{ borderRadius: 8 }}><Icon size={20} /></div>
      </div>
      <div className="mono mt-4 text-2xl font-semibold text-ink">{value}</div>
    </div>
  );
}

function Empty({ label }) {
  return <div className="p-8 text-center text-sm text-muted">{label}</div>;
}
