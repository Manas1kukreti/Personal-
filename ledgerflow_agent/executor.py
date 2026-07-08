"""
executor.py
Flat, sequential plan runner.

Receives the plan dict from orchestrator.plan() and an initial state,
then executes each step in order, hard-enforcing:

  • validate must run before push_ui  (structural invariant)
  • max_retries ceiling on repair cycles  (from project_config.yml)
  • DTCD errors route to notification, not another repair cycle
  • Unknown step names raise immediately rather than silently skipping

After each step the state is merged with the node's return dict.
The "route" step is resolved at runtime from the live validation_result.
"""
from __future__ import annotations

from typing import Any

from config_loader import get_workflow_config
from ledgerflow_agent.guardrails import safe_error_message
from ledgerflow_agent.routing import decide_after_ui, decide_after_validation


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
        "input": input_node,
        "extract": extraction_node,
        "validate": validation_node,
        "repair": repair_node,
        "ui": ui_node,
        "notification": notification_node,
        "finalize": finalize_node,
    }


def _max_retries() -> int:
    return int(get_workflow_config().get("max_retries", 5))


def run(
    plan_result: dict[str, Any],
    initial_state: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute the step list produced by orchestrator.plan().
    """
    node_map = _get_node_map()
    state: dict[str, Any] = dict(initial_state)
    hints = plan_result.get("hints", {})
    max_r = hints.get("max_repair_cycles") or _max_retries()

    steps: list[str] = list(plan_result.get("steps", []))
    repair_cycles = 0
    validated_before_ui = False

    step_index = 0
    while step_index < len(steps):
        step = steps[step_index]
        step_index += 1

        print(f"\n[Executor] -- Step {step_index}: {step.upper()} --")

        if step == "route":
            next_step = decide_after_validation(state)
            print(f"[Executor] Route resolved -> {next_step}")
            steps = steps[:step_index] + [next_step] + steps[step_index:]
            continue

        if step == "repair":
            if repair_cycles >= max_r:
                print(
                    f"[Executor] GUARDRAIL — repair_cycles ({repair_cycles}) >= "
                    f"max_retries ({max_r}). Overriding repair -> notification."
                )
                steps = ["notification", "finalize"]
                step_index = 0
                step = "notification"
            else:
                repair_cycles += 1
                print(f"[Executor] Repair cycle {repair_cycles}/{max_r}")

        if step == "ui" and not validated_before_ui:
            print(
                "[Executor] GUARDRAIL — 'ui' reached without a prior validate. "
                "Inserting validate step."
            )
            steps = steps[:step_index - 1] + ["validate", "ui"] + steps[step_index:]
            step = "validate"

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
            errors = list(state.get("errors") or [])
            errors.append({"step": step, "error": safe_error_message(exc)})
            state = {**state, "errors": errors, "processing_status": f"{step}_failed"}
            steps = ["finalize"]
            step_index = 0
            continue

        state = {**state, **update}

        if step == "validate":
            validated_before_ui = True
            next_step = decide_after_validation(state)
            remaining = steps[step_index:]
            if remaining and remaining[0] in {"route", next_step}:
                pass
            else:
                filtered = [s for s in remaining if s not in {"repair", "validate", "route"}]
                steps = steps[:step_index] + [next_step] + filtered
                print(
                    f"[Executor] Post-validate splice -> next={next_step}, "
                    f"remaining={steps[step_index:]}"
                )

        if step == "ui":
            next_step = decide_after_ui(state)
            remaining = steps[step_index:]
            if not remaining or remaining[0] != next_step:
                filtered = [s for s in remaining if s not in {"notification", "finalize"}]
                steps = steps[:step_index] + [next_step] + filtered
                print(f"[Executor] Post-ui splice -> next={next_step}")

    print("\n[Executor] Plan complete.")
    return state

