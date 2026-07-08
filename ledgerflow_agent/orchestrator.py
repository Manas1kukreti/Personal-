"""
orchestrator.py
───────────────
Pure-Python planning layer.

Reads the current LedgerFlowState and a memory summary produced by
summarise_memory(), then emits:

    {
        "steps":  ["input", "extract", "validate", "repair", "validate",
                   "ui", "finalize"],
        "hints":  {
            "skip_extract":            True | False,
            "priority_repair_fields":  ["voucher_date", "account_key"],
            "login_retry":             True | False,
            "known_bad_account_keys":  ["ACC-001", ...],
            "pre_flagged_entities":    [...],
        },
    }

The executor consumes this dict and runs each step in order.
No LLM is called here — all decisions are threshold-based Python rules.
"""
from __future__ import annotations

from typing import Any

from config_loader import get_workflow_config
from ledgerflow_agent.utils import is_structured_transaction_data


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Number of recent runs that must ALL have skipped extraction before we
# drop the input+extract steps from the plan automatically.
_SKIP_EXTRACT_WINDOW = 5

# A field must appear in the top-N validation failures to be pre-prioritised.
_PRIORITY_FAILURE_TOP_N = 3

# If recent uploads have failed this many consecutive runs, add login_retry.
_LOGIN_RETRY_THRESHOLD = 2

# Max repair-validate cycles in a single plan (hard ceiling from config).
_MAX_REPAIR_CYCLES_DEFAULT = 5


def _max_retries() -> int:
    return int(get_workflow_config().get("max_retries", _MAX_REPAIR_CYCLES_DEFAULT))


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY ANALYSIS HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _last_n_runs(memory_summary: dict[str, Any], n: int) -> list[dict[str, Any]]:
    """Return up to the last *n* run records from memory."""
    return list(memory_summary.get("recent_runs") or [])[-n:]


def _all_skipped_extract(recent_runs: list[dict[str, Any]]) -> bool:
    """True if every run in the window skipped the extraction step.

    Requires the full window to be populated — avoids skipping extraction
    on the very first run (or when memory is sparse) just because no
    extraction tool appears in a single-entry history.
    """
    if len(recent_runs) < _SKIP_EXTRACT_WINDOW:
        return False
    return all(
        "extraction" not in (run.get("tools_used") or [])
        and "extract_data" not in (run.get("tools_used") or [])
        for run in recent_runs
    )


def _consecutive_upload_failures(recent_runs: list[dict[str, Any]], threshold: int) -> bool:
    """True if the last *threshold* runs all had a failed upload status."""
    if len(recent_runs) < threshold:
        return False
    tail = recent_runs[-threshold:]
    return all(
        str(run.get("upload_status", "")).lower() in {"failed", "error", ""}
        for run in tail
    )


def _priority_failure_fields(memory_summary: dict[str, Any], top_n: int) -> list[str]:
    """
    Extract field names from the top-N validation failure signatures.

    The memory stores full error messages like:
      "voucher_date is missing or empty"
      "debit_amount failed schema validation"
    We pull out the leading token (field name) when it looks like a schema field.
    """
    known_fields = {
        "voucher_date", "voucher_number", "voucher_type", "debit_amount",
        "credit_amount", "amount", "account", "account_key", "account_class",
        "account_subclass", "sub_account", "particulars", "narration",
        "country", "region", "ledger_name",
    }
    priority: list[str] = []
    for message, _count in (memory_summary.get("top_validation_failures") or [])[:top_n]:
        first_token = str(message).split()[0].rstrip("_:.,").lower()
        if first_token in known_fields and first_token not in priority:
            priority.append(first_token)
    return priority


def _known_bad_account_keys(memory_summary: dict[str, Any]) -> list[str]:
    """
    Return account_key values that appear repeatedly in the entity counter
    *and* also appear in top validation failures — likely consistently bad keys.
    """
    top_entities = dict(memory_summary.get("top_entities") or [])
    top_failures = " ".join(
        msg for msg, _ in (memory_summary.get("top_validation_failures") or [])
    ).lower()

    bad: list[str] = []
    for entity_key in top_entities:
        if entity_key.startswith("account_key:"):
            raw = entity_key.split(":", 1)[1].strip()
            if raw.lower() in top_failures:
                bad.append(raw)
    return bad


# ─────────────────────────────────────────────────────────────────────────────
# STEP-LIST BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_steps(
    state: dict[str, Any],
    skip_extract: bool,
    max_repair_cycles: int,
) -> list[str]:
    """
    Produce the ordered step list.

    Rules:
    ┌─────────────────────────────────────────────────────────────────────┐
    │ 1. If state already has structured extracted_data → skip input+extract│
    │ 2. If memory says last N runs skipped extract → skip input+extract   │
    │ 3. Always validate before push_ui (executor enforces this too)       │
    │ 4. Plan at most max_repair_cycles repair→validate pairs              │
    │ 5. End with ui → finalize (or notification → finalize on hard fail)  │
    └─────────────────────────────────────────────────────────────────────┘
    The executor will dynamically decide after each validate whether another
    repair cycle is actually needed or if it can proceed to ui/notification.
    We plan for the worst case (one repair cycle) upfront; the executor
    short-circuits when validation passes early.
    """
    required_fields = list(get_workflow_config().get("structured_data_required_fields", []))
    already_structured = is_structured_transaction_data(
        state.get("extracted_data"), required_fields
    ) or is_structured_transaction_data(
        state.get("email_text"), required_fields
    )

    steps: list[str] = []

    # ── Phase 1: data acquisition ─────────────────────────────────────────
    if not already_structured and not skip_extract:
        steps.append("input")
        steps.append("extract")

    # ── Phase 2: first validation pass ───────────────────────────────────
    steps.append("validate")

    # ── Phase 3: repair + re-validate (worst-case one cycle; executor
    #            short-circuits when validation passes) ────────────────────
    # We plan exactly one repair cycle; the executor will loop if needed up
    # to max_repair_cycles using its internal counter.
    steps.append("repair")
    steps.append("validate")

    # ── Phase 4: output ───────────────────────────────────────────────────
    # "route" is a logical marker the executor resolves at runtime into
    # "ui" or "notification" based on validation_result.
    steps.append("route")
    steps.append("finalize")

    return steps


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def plan(
    state: dict[str, Any],
    memory_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Entry point called by the executor before any step runs.

    Parameters
    ----------
    state:
        The current LedgerFlowState (may be mostly empty on a fresh run).
    memory_summary:
        Output of ``summarise_memory(load_memory())``.

    Returns
    -------
    dict with keys:
        "steps"  – ordered list of step names
        "hints"  – context bag passed through to each node via state
    """
    recent = _last_n_runs(memory_summary, _SKIP_EXTRACT_WINDOW)

    # ── Decision: skip input + extract? ──────────────────────────────────
    skip_extract = _all_skipped_extract(recent)
    if skip_extract:
        print(
            f"[Orchestrator] Last {_SKIP_EXTRACT_WINDOW} runs all skipped extraction "
            "-> dropping input + extract from plan."
        )

    # ── Decision: login retry hint? ───────────────────────────────────────
    login_retry = _consecutive_upload_failures(recent, _LOGIN_RETRY_THRESHOLD)
    if login_retry:
        print(
            f"[Orchestrator] Last {_LOGIN_RETRY_THRESHOLD} uploads failed "
            "-> setting login_retry hint."
        )

    # ── Decision: which fields to prioritise in repair? ──────────────────
    priority_fields = _priority_failure_fields(memory_summary, _PRIORITY_FAILURE_TOP_N)
    if priority_fields:
        print(f"[Orchestrator] Priority repair fields from memory: {priority_fields}")

    # ── Decision: known bad account keys? ────────────────────────────────
    bad_keys = _known_bad_account_keys(memory_summary)
    if bad_keys:
        print(f"[Orchestrator] Known-bad account_keys from memory: {bad_keys}")

    max_repair = _max_retries()
    steps = _build_steps(state, skip_extract=skip_extract, max_repair_cycles=max_repair)

    hints: dict[str, Any] = {
        "skip_extract":            skip_extract,
        "priority_repair_fields":  priority_fields,
        "login_retry":             login_retry,
        "known_bad_account_keys":  bad_keys,
        "pre_flagged_entities":    list(
            entity for entity, _ in (memory_summary.get("top_entities") or [])
        ),
        "max_repair_cycles":       max_repair,
    }

    print(f"[Orchestrator] Plan -> {steps}")
    print(f"[Orchestrator] Hints -> {hints}")

    return {"steps": steps, "hints": hints}