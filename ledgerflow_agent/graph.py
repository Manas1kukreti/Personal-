from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from ledgerflow_agent.nodes import (
    extraction_node,
    finalize_node,
    input_node,
    notification_node,
    repair_node,
    route_after_input,
    route_after_repair,
    route_after_start,
    route_after_ui,
    route_after_validation,
    start_node,
    ui_node,
    validation_node,
)
from ledgerflow_agent.state import LedgerFlowState


def build_ledgerflow_graph():
    graph = StateGraph(LedgerFlowState)

    graph.add_node("start", start_node)
    graph.add_node("input", input_node)
    graph.add_node("extract", extraction_node)
    graph.add_node("validate", validation_node)
    graph.add_node("repair", repair_node)
    graph.add_node("ui", ui_node)
    graph.add_node("notification", notification_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("start")

    graph.add_conditional_edges(
        "start",
        route_after_start,
        {
            "input": "input",
            "validate": "validate",
        },
    )
    graph.add_conditional_edges(
        "input",
        route_after_input,
        {
            "extract": "extract",
            "validate": "validate",
        },
    )
    graph.add_edge("extract", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "ui": "ui",
            "repair": "repair",
            "notification": "notification",
        },
    )
    graph.add_conditional_edges(
        "repair",
        route_after_repair,
        {
            "validate": "validate",
            "extract": "extract",
            "notification": "notification",
        },
    )
    graph.add_conditional_edges(
        "ui",
        route_after_ui,
        {
            "notification": "notification",
            "finalize": "finalize",
        },
    )
    graph.add_edge("notification", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


ledgerflow_graph = build_ledgerflow_graph()


def run_ledgerflow_agent(initial_state: dict[str, Any] | None = None) -> LedgerFlowState:
    return ledgerflow_graph.invoke(initial_state or {"retry_count": 0})


def run_ledgerflow_agent_dynamic(
    initial_state: dict[str, Any] | None = None,
) -> LedgerFlowState:
    """
    Dynamic entry point — uses the orchestrator + executor instead of the
    compiled LangGraph fixed-edge graph.

    Flow:
        load_memory()
          → orchestrator.plan(state, memory_summary)
          → executor.run(plan, state)
          → final LedgerFlowState

    The compiled LangGraph (ledgerflow_graph / run_ledgerflow_agent) remains
    available as a fallback.
    """
    import time

    from ledgerflow_agent.executor import run as executor_run
    from ledgerflow_agent.memory import load_memory, summarise_memory
    from ledgerflow_agent.nodes import start_node
    from ledgerflow_agent.orchestrator import plan as orchestrate

    # ── 1. Bootstrap state (mirrors start_node) ───────────────────────────
    raw = dict(initial_state or {})
    raw.setdefault("retry_count", 0)

    # Run start_node to populate agent_metadata, memory fields, etc.
    state: dict[str, Any] = {**raw, **start_node(raw)}

    # ── 2. Load memory ─────────────────────────────────────────────────────
    memory = load_memory()
    memory_summary = summarise_memory(memory)
    state["memory_snapshot"] = memory
    state["memory_summary"] = memory_summary

    # ── 3. Orchestrator produces the plan ──────────────────────────────────
    plan_result = orchestrate(state, memory_summary)
    state["execution_plan"] = plan_result
    state["orchestrator_hints"] = plan_result.get("hints", {})

    # ── 4. Executor runs the plan ──────────────────────────────────────────
    final_state = executor_run(plan_result, state)

    return final_state  # type: ignore[return-value]
