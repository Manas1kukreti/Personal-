import React from "react";
import { FiCheck, FiClock, FiX } from "react-icons/fi";

export default function ProgressMilestones({ status = "pending", createdAt, reviewedAt }) {
  const normalized = status || "pending";
  const decisionLabel = normalized === "approved" ? "Approved" : normalized === "declined" ? "Rejected" : normalized === "reupload_requested" ? "Re-upload" : "Decision";
  const activeIndex = normalized === "pending" ? 1 : 2;
  const decisionTime = reviewedAt || (normalized !== "pending" ? createdAt : null);
  const steps = [
    { key: "submitted", label: "Submitted", date: createdAt, state: "done" },
    { key: "pending", label: "Pending", date: normalized === "pending" ? createdAt : null, state: activeIndex >= 1 ? "done" : "todo" },
    { key: "decision", label: decisionLabel, date: decisionTime, state: normalized === "pending" ? "todo" : normalized === "declined" ? "declined" : "done" }
  ];

  return (
    <div className="overflow-x-auto py-2">
      <div className="grid min-w-[520px] grid-cols-3 items-start">
        {steps.map((step, index) => {
          const isReached = step.state === "done" || step.state === "declined";
          const isDeclined = step.state === "declined";
          const lineReached = index < activeIndex;
          const Icon = isDeclined ? FiX : isReached ? FiCheck : FiClock;
          const formatted = formatDateTime(step.date);
        return (
          <div
            key={step.key}
            className={`relative flex flex-col ${index === 0 ? "items-start" : index === steps.length - 1 ? "items-end" : "items-center"}`}
          >
            {index < steps.length - 1 && (
              <span
                className={`absolute top-5 h-0.5 w-full ${lineReached ? "bg-brand" : "bg-line"}`}
                style={{ left: "50%" }}
              />
            )}
            <span
              className={`z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 ${
                isDeclined
                  ? "border-danger bg-danger text-white"
                  : isReached
                    ? "border-brand bg-brand text-white"
                    : "border-line bg-white text-muted"
              }`}
            >
              <Icon />
            </span>
            <div className={`mt-3 max-w-40 ${index === 0 ? "text-left" : index === steps.length - 1 ? "text-right" : "text-center"}`}>
              <div className="text-sm font-bold text-ink">{step.label}</div>
              {formatted ? (
                <>
                  <div className="mt-1 text-xs font-medium text-muted">{formatted.time}</div>
                  <div className="text-sm font-bold text-ink">{formatted.date}</div>
                </>
              ) : (
                <div className="mt-1 text-xs font-semibold text-muted">Waiting</div>
              )}
            </div>
          </div>
        );
      })}
      </div>
    </div>
  );
}

function formatDateTime(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return {
    time: date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true, timeZoneName: "short" }),
    date: date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
  };
}
