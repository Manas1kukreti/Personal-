from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path to support direct execution
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from typing import Any

from langgraph.graph import END, StateGraph

from ledgerflow_agent.nodes import (
    start_node,
    input_node,
    preprocessing_tools_node,
    extraction_node,
    validation_node,
    repair_node,
    ui_node,
    notification_node,
    route_after_supervisor,
    route_after_validate,
    route_after_push_to_ui,
)
from ledgerflow_agent.state import LedgerFlowState


def build_ledgerflow_graph():
    graph = StateGraph(LedgerFlowState)

    graph.add_node("supervisor", start_node)
    graph.add_node("fetch_email", input_node)
    graph.add_node("preprocessing_tools", preprocessing_tools_node)
    graph.add_node("extract_data", extraction_node)
    graph.add_node("validate", validation_node)
    graph.add_node("re_extract", repair_node)
    graph.add_node("push_to_ui", ui_node)
    graph.add_node("notification", notification_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "fetch_email": "fetch_email",
            "preprocessing_tools": "preprocessing_tools",
            "extract_data": "extract_data",
            "validate": "validate",
            "re_extract": "re_extract",
            "push_to_ui": "push_to_ui",
            "notification": "notification",
        },
    )

    graph.add_edge("fetch_email", "supervisor")
    graph.add_edge("preprocessing_tools", "supervisor")
    graph.add_edge("extract_data", "supervisor")
    graph.add_edge("re_extract", "supervisor")

    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "re_extract": "re_extract",
            "push_to_ui": "push_to_ui",
            "notification": "notification",
        },
    )

    graph.add_conditional_edges(
        "push_to_ui",
        route_after_push_to_ui,
        {
            "notification": "notification",
            "__end__": END,
        },
    )

    graph.add_edge("notification", END)

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


if __name__ == "__main__":
    print("\n✓ ledgerflow_graph compiled successfully!")
    print("\nGraph Mermaid representation:")
    print(ledgerflow_graph.get_graph().draw_mermaid())
