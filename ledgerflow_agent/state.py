from __future__ import annotations

from typing import Any, TypedDict


class LedgerFlowState(TypedDict, total=False):
    email_text: str
    extracted_data: list[dict[str, Any]] | dict[str, Any]
    validation_result: dict[str, Any]
    ui_result: dict[str, Any]
    notification_result: dict[str, Any]
    retry_count: int
    max_retries: int
    processing_status: str
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    tools_used: list[str]
    tool_results: dict[str, Any]
    metrics: dict[str, Any]
    agent_metadata: dict[str, Any]
    agent_prompts: dict[str, dict[str, str]]
    active_agent: str
    active_agent_prompt: str
    memory_snapshot: dict[str, Any]
    memory_summary: dict[str, Any]
    user_preferences: dict[str, Any]
    started_at: float
    completed_at: float
    final_output: dict[str, Any]
    execution_plan: dict[str, Any]       # plan dict from orchestrator.plan()
    orchestrator_hints: dict[str, Any]   # hints sub-dict extracted from plan
    repair_plan: list[dict[str, Any]]    # triage output from repair_agent.triage()
