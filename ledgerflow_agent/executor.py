"""
executor.py
───────────
Flat, sequential plan runner.

Receives the plan dict from orchestrator.plan() and an initial state,
then executes each step in order, hard-enforcing:

  • validate must run before push_ui  (structural invariant)
  • max_retries ceiling on repair cycles  (from project_config.yml)
  • DTCD errors route to notification, not another repair cycle
  • Unknown step names raise immediately rather than silently skipping

After each step the state is merged with the node's return dict.
The "route" step is resolved at runtime from the live validation_result —
it is never planned statically.
"""
from __future__ import annotations

import json
from typing import Any

from config_loader import get_workflow_config
from ledgerflow_agent.guardrails import safe_error_message
from ledgerflow_agent.utils import has_balance_errors, normal_validation_errors


# ─────────────────────────────────────────────────────────────────────────────
# NODE MAP  (step name → node function, imported lazily to avoid cycles)
# ─────────────────────────────────────────────────────────────────────────────

def _get_node_map() -> dict[str, Any]:
    from ledgerflow_agent.nodes import (
        extraction_node,
        finalize_node,
        input_node,
        notification_node,
        repair_node,
        ui_node,
        validation_node,
    )
    return {
        "input":        input_node,
        "extract":      extraction_node,
        "validate":     validation_node,
        "repair":       repair_node,
        "ui":           ui_node,
        "notification": notification_node,
        "finalize":     finalize_node,
        # "route" is handled inline — not a real node
    }


# ─────────────────────────────────────────────────────────────────────────────
# GUARDRAIL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _max_retries() -> int:
    return int(get_workflow_config().get("max_retries", 5))


def _post_validate_route(state: dict[str, Any]) -> str:
    """
    Pure-Python routing decision made AFTER each validate step.

    This mirrors the LLM routing decision that used to live in
    route_after_validation, but keeps the logic deterministic here so the
    LLM is not called on every repair cycle.  The LLM routing call that
    appears in nodes.route_after_validation is preserved for the compiled
    LangGraph path — it is not used by the executor.

    Returns one of: "ui", "repair", "notification"
    """
    validation_result = state.get("validation_result") or {}
    retry_count = int(state.get("retry_count", 0))
    max_r = _max_retries()

    if validation_result.get("status") == "valid":
        return "ui"

    if has_balance_errors(validation_result):
        # DTCD imbalance → push to UI with alert, then notify
        return "ui"

    if normal_validation_errors(validation_result):
        if retry_count >= max_r:
            print(
                f"[Executor] max_retries ({max_r}) reached — "
                "routing to notification."
            )
            return "notification"
        return "repair"

    # No errors at all (edge case)
    return "ui"


def _post_ui_route(state: dict[str, Any]) -> str:
    """Route after ui_node: notification if there are balance errors, else finalize."""
    if state.get("processing_status") in {"ui_pushed_with_alert", "ui_failed"}:
        return "notification"
    return "finalize"


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTOR
# ─────────────────────────────────────────────────────────────────────────────

def run(
    plan_result: dict[str, Any],
    initial_state: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute the step list produced by orchestrator.plan().

    Parameters
    ----------
    plan_result:
        Dict with "steps" (list[str]) and "hints" (dict).
    initial_state:
        The initial LedgerFlowState (already contains memory_snapshot,
        memory_summary, execution_plan, orchestrator_hints injected by
        run_ledgerflow_agent_dynamic before calling us).

    Returns
    -------
    Final LedgerFlowState after all steps complete.
    """
    node_map = _get_node_map()
    state: dict[str, Any] = dict(initial_state)
    hints = plan_result.get("hints", {})
    max_r = hints.get("max_repair_cycles") or _max_retries()

    # Working copy of the plan — we may splice steps at runtime
    steps: list[str] = list(plan_result.get("steps", []))

    # Hard counters enforced by the executor regardless of plan contents
    repair_cycles = 0
    validated_before_ui = False  # invariant: must be True before "ui" runs

    step_index = 0
    while step_index < len(steps):
        step = steps[step_index]
        step_index += 1

        print(f"\n[Executor] -- Step {step_index}: {step.upper()} --")

        # ── Special step: "route" ─────────────────────────────────────────
        # Resolved at runtime from current validation_result.
        if step == "route":
            next_step = _post_validate_route(state)
            print(f"[Executor] Route resolved -> {next_step}")
            # Splice the resolved step in place and restart the loop
            steps = steps[:step_index] + [next_step] + steps[step_index:]
            continue

        # ── Hard guardrail: repair ceiling ───────────────────────────────
        if step == "repair":
            if repair_cycles >= max_r:
                print(
                    f"[Executor] GUARDRAIL — repair_cycles ({repair_cycles}) >= "
                    f"max_retries ({max_r}). Overriding repair -> notification."
                )
                step = "notification"
                # Remove any remaining repair/validate pairs that were queued
                steps = [s for s in steps[step_index:] if s not in {"repair", "validate"}]
                steps = ["notification", "finalize"]
                step_index = 0
            else:
                repair_cycles += 1
                print(f"[Executor] Repair cycle {repair_cycles}/{max_r}")

        # ── Hard guardrail: validate before ui ───────────────────────────
        if step == "ui" and not validated_before_ui:
            print(
                "[Executor] GUARDRAIL — 'ui' reached without a prior validate. "
                "Inserting validate step."
            )
            steps = steps[:step_index - 1] + ["validate", "ui"] + steps[step_index:]
            step = "validate"
            step_index = step_index  # re-run from validate

        # ── Execute the node ──────────────────────────────────────────────
        if step not in node_map:
            raise ValueError(
                f"[Executor] Unknown step '{step}'. "
                f"Valid steps: {sorted(node_map.keys())}"
            )

        node_fn = node_map[step]
        try:
            update = node_fn(state)
        except Exception as exc:
            print(f"[Executor] Step '{step}' raised: {safe_error_message(exc)}")
            # Record error in state and continue to finalize
            errors = list(state.get("errors") or [])
            errors.append({"step": step, "error": safe_error_message(exc)})
            state = {**state, "errors": errors, "processing_status": f"{step}_failed"}
            # Force straight to finalize on unexpected crash
            steps = ["finalize"]
            step_index = 0
            continue

        state = {**state, **update}

        # ── Post-validate: decide next step dynamically ───────────────────
        if step == "validate":
            validated_before_ui = True
            next_step = _post_validate_route(state)
            remaining = steps[step_index:]

            # If the next planned step is already correct, do nothing.
            if remaining and remaining[0] in {"route", next_step}:
                pass
            else:
                # Replace whatever was next with what the data actually needs
                # (e.g. plan said "repair" but validation already passed).
                filtered = [s for s in remaining if s not in {"repair", "validate", "route"}]
                steps = steps[:step_index] + [next_step] + filtered
                print(
                    f"[Executor] Post-validate splice -> next={next_step}, "
                    f"remaining={steps[step_index:]}"
                )

        # ── Post-ui: decide finalize vs notification ──────────────────────
        if step == "ui":
            next_step = _post_ui_route(state)
            remaining = steps[step_index:]
            if not remaining or remaining[0] != next_step:
                filtered = [s for s in remaining if s not in {"notification", "finalize"}]
                steps = steps[:step_index] + [next_step] + filtered
                print(f"[Executor] Post-ui splice -> next={next_step}")

    print("\n[Executor] Plan complete.")
    return state
