"""
repair_agent.py
───────────────
LLM-powered triage layer for the repair step.

Receives the full error list from the validator + orchestrator hints and
returns a prioritised RepairPlan list — one entry per repairable field —
telling the repair_node:

    - WHICH fields to attempt  (skipping DTCD errors and unrecoverables)
    - IN WHAT ORDER            (account_key before account_class, etc.)
    - WITH WHAT STRATEGY       ("rule_based" or "llm")

The LLM earns its place here: ranking by dependency and picking strategy
per field is a genuine judgment call that depends on the actual data content.

If the LLM call fails or returns invalid JSON, triage() falls back to the
original blind-loop order so the repair_node always makes progress.
"""
from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


# ─────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────

class RepairItem(BaseModel):
    """A single field-level repair instruction."""

    field: str = Field(description="The name of the field to repair.")
    strategy: Literal["rule_based", "llm", "skip"] = Field(
        description=(
            "'rule_based' — use deterministic accounting rules first; "
            "'llm' — go straight to LLM (field has no deterministic rule); "
            "'skip' — do not attempt repair (DTCD error, unrecoverable, etc.)."
        )
    )
    priority: int = Field(
        description="1 = highest priority. Fix lower numbers first."
    )
    reason: str | None = Field(
        default=None,
        description="Optional human-readable explanation of the decision.",
    )


class RepairPlan(BaseModel):
    """Triage output — ordered list of field-level instructions."""

    items: list[RepairItem]


# ─────────────────────────────────────────────────────────────────────────────
# HARD RULES INJECTED INTO THE PROMPT
# ─────────────────────────────────────────────────────────────────────────────

_TRIAGE_SYSTEM_PROMPT = """\
You are a financial-data repair triage specialist.

HARD RULES (non-negotiable):
1. Any error containing "not balanced" or "difference" → strategy: "skip".
   DTCD imbalance cannot be patched by field repair.
2. If a field has no source value at all (current_value is null/empty and
   the error says "missing") and no sibling field can derive it →
   strategy: "skip", reason: "unrecoverable without source data".
3. account_key must always come before account_class and account_subclass
   (dependency: class/subclass are derived from key).
4. voucher_date errors → use strategy "rule_based" if the date can be
   parsed from a neighbouring format field; otherwise "llm".
5. debit_amount / credit_amount → "rule_based" if amount field is present;
   otherwise "skip".
6. If a field appears in the priority_repair_fields hint → assign priority 1
   regardless of its natural order.
7. Return a JSON object with key "items" — a list of objects each having:
   "field", "strategy", "priority" (integer, 1 = first), "reason" (string or null).
8. Include only errors that have a "failed_field" key. Ignore all others.
"""

_TRIAGE_USER_TEMPLATE = """\
ERRORS (from validator):
{errors_json}

ORCHESTRATOR HINTS:
{hints_json}

Return ONLY the JSON triage plan. No markdown. No explanation outside the JSON.
"""


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK: blind-loop order (mirrors original repair_node behaviour)
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_plan(errors: list[dict[str, Any]]) -> list[RepairItem]:
    """
    Original repair_node ordering — iterate errors as-is, skip DTCD entries.
    Used when the LLM call fails or returns unusable output.
    """
    items: list[RepairItem] = []
    for i, err in enumerate(errors):
        text = str(err.get("error", "")).lower()
        if "not balanced" in text or "difference" in text:
            continue
        field = err.get("failed_field")
        if not field:
            continue
        items.append(
            RepairItem(
                field=field,
                strategy="rule_based",
                priority=i + 1,
                reason="fallback ordering (LLM triage unavailable)",
            )
        )
    return items


# ─────────────────────────────────────────────────────────────────────────────
# DEDUPLICATION HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _deduplicate(items: list[RepairItem]) -> list[RepairItem]:
    """Keep the first occurrence of each field name."""
    seen: set[str] = set()
    out: list[RepairItem] = []
    for item in items:
        if item.field not in seen:
            seen.add(item.field)
            out.append(item)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def triage(
    errors: list[dict[str, Any]],
    hints: dict[str, Any],
    state: dict[str, Any],  # noqa: ARG001  — available for future use
) -> list[RepairItem]:
    """
    Produce a prioritised, deduplicated list of RepairItem instructions.

    Parameters
    ----------
    errors:
        The ``errors`` list from validation_result.
    hints:
        The ``hints`` dict from the orchestrator plan output.
    state:
        Full LedgerFlowState (available for richer context in future).

    Returns
    -------
    List of RepairItem sorted by ascending priority (1 = fix first).
    Empty list → nothing to repair (all errors are DTCD or unrecoverable).
    """
    # Fast path: no errors at all
    if not errors:
        return []

    # Filter to only field-level errors before calling LLM
    field_errors = [e for e in errors if e.get("failed_field")]
    if not field_errors:
        return []

    # ── Attempt LLM triage ────────────────────────────────────────────────
    try:
        from ledgerflow_agent.llm import get_chat_llm

        llm = get_chat_llm()
        structured_llm = llm.with_structured_output(RepairPlan)

        user_msg = _TRIAGE_USER_TEMPLATE.format(
            errors_json=json.dumps(field_errors, indent=2, default=str),
            hints_json=json.dumps(
                {
                    "priority_repair_fields": hints.get("priority_repair_fields", []),
                    "known_bad_account_keys": hints.get("known_bad_account_keys", []),
                },
                indent=2,
            ),
        )

        prompt = f"{_TRIAGE_SYSTEM_PROMPT}\n\n{user_msg}"
        result: RepairPlan = structured_llm.invoke(prompt)

        items = sorted(result.items, key=lambda x: x.priority)
        items = _deduplicate(items)

        # Honour orchestrator priority overrides: if a field is in
        # priority_repair_fields, bump it to the front.
        priority_fields: list[str] = hints.get("priority_repair_fields") or []
        if priority_fields:
            front = [i for i in items if i.field in priority_fields]
            back = [i for i in items if i.field not in priority_fields]
            items = front + back
            # Re-number priorities sequentially after reorder
            for seq, item in enumerate(items, start=1):
                item = item.model_copy(update={"priority": seq})
                items[seq - 1] = item

        print(f"[RepairAgent] Triage complete — {len(items)} field(s) to process.")
        for item in items:
            print(
                f"  priority={item.priority}  field={item.field:<20} "
                f"strategy={item.strategy:<12}  reason={item.reason}"
            )

        return items

    except ValidationError as exc:
        print(f"[RepairAgent] LLM returned invalid RepairPlan schema: {exc}")
    except Exception as exc:
        print(f"[RepairAgent] LLM triage failed, using fallback order: {exc}")

    # ── Fallback: original blind-loop order ───────────────────────────────
    fallback = _fallback_plan(errors)
    print(f"[RepairAgent] Fallback plan — {len(fallback)} field(s).")
    return fallback
