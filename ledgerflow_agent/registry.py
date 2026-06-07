from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

from ledgerflow_agent.tool_policy import ensure_tool_allowed


@dataclass(frozen=True)
class LedgerFlowTool:
    name: str
    role: str
    module: str
    function: str

    def call(self, *args: Any, **kwargs: Any) -> Any:
        module = import_module(self.module)
        func = getattr(module, self.function)
        return func(*args, **kwargs)


TOOL_REGISTRY: dict[str, LedgerFlowTool] = {
    "fetch_email": LedgerFlowTool(
        name="fetch_email",
        role="Fetch latest email body and attachments.",
        module="agents.data_input",
        function="get_email_text",
    ),
    "read_excel": LedgerFlowTool(
        name="read_excel",
        role="Read and preprocess an Excel attachment file.",
        module="agents.data_input",
        function="extract_excel",
    ),
    "extract_data": LedgerFlowTool(
        name="extract_data",
        role="Convert source financial content into structured JSON.",
        module="agents.llm_extractor",
        function="extract_data",
    ),
    "validate_data": LedgerFlowTool(
        name="validate_data",
        role="Validate extracted transactions with schema and accounting rules.",
        module="agents.validator",
        function="validate_data",
    ),
    "re_extract_field": LedgerFlowTool(
        name="re_extract_field",
        role="Repair one failed field using deterministic rules and LLM fallback.",
        module="agents.re_extractor",
        function="re_extract_field",
    ),
    "push_to_ui": LedgerFlowTool(
        name="push_to_ui",
        role="Persist validated output and upload it to the dashboard.",
        module="agents.ui_agent",
        function="push_to_ui",
    ),
    "login": LedgerFlowTool(
        name="login",
        role="Authenticate with the dashboard for alert delivery.",
        module="agents.ui_agent",
        function="login_tool",
    ),
    "push_validation_alert": LedgerFlowTool(
        name="push_validation_alert",
        role="Send debit-credit difference alerts to the dashboard.",
        module="tools.pushing_validation_alert_tool",
        function="push_validation_alert_tool",
    ),
    # save_json / save_json_tool both resolve to the same ui_agent function.
    # nodes.py may call either name depending on version; both are registered.
    "save_json": LedgerFlowTool(
        name="save_json",
        role="Save validated transaction data as verified_data.json for audit.",
        module="agents.ui_agent",
        function="save_json_tool",
    ),
    "save_json_tool": LedgerFlowTool(
        name="save_json_tool",
        role="Save validated transaction data as verified_data.json for audit.",
        module="agents.ui_agent",
        function="save_json_tool",
    ),
    # generate_excel / generate_excel_tool both resolve to the same ui_agent function.
    "generate_excel": LedgerFlowTool(
        name="generate_excel",
        role="Generate a verified_data.xlsx GL Excel file from validated transactions.",
        module="agents.ui_agent",
        function="generate_excel_tool",
    ),
    "generate_excel_tool": LedgerFlowTool(
        name="generate_excel_tool",
        role="Generate a verified_data.xlsx GL Excel file from validated transactions.",
        module="agents.ui_agent",
        function="generate_excel_tool",
    ),
}


def call_tool(tool_name: str, *args: Any, agent_name: str | None = None, **kwargs: Any) -> Any:
    if agent_name:
        ensure_tool_allowed(agent_name, tool_name)
    if tool_name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{tool_name}' is not registered in TOOL_REGISTRY")
    return TOOL_REGISTRY[tool_name].call(*args, **kwargs)