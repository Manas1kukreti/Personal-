from __future__ import annotations

from typing import Iterable, Union

from ledgerflow_agent.guardrails import GuardrailViolation
from ledgerflow_agent.prompts import AgentPromptKey

AGENT_TOOL_POLICY: dict[str, dict[str, set[str]]] = {
    "supervisor": {
        "registry_tools": set(),
        "langchain_tools": set(),
    },
    "input": {
        "registry_tools": {"fetch_email", "read_excel"},
        "langchain_tools": {"email_extraction_tool", "read_file_tool"},
    },
    "extraction": {
        "registry_tools": {"extract_data"},
        "langchain_tools": {"financial_data_extractor", "read_file_tool"},
    },
    "validation": {
        "registry_tools": {"validate_data"},
        "langchain_tools": {"validator_tool"},
    },
    "re_extraction": {
        "registry_tools": {"re_extract_field"},
        "langchain_tools": set(),
    },
    "ui": {
        "registry_tools": {
            "push_to_ui", "login",
            "save_json", "save_json_tool",
            "generate_excel", "generate_excel_tool",
        },
        "langchain_tools": {"ui_push_tool"},
    },
    "notification": {
        "registry_tools": {"login", "push_validation_alert"},
        "langchain_tools": {"validation_alert_tool"},
    },
}


def _normalize_agent_name(agent: Union[str, AgentPromptKey]) -> str:
    """Accept either a raw string or an AgentPromptKey enum and return the canonical string name."""
    return agent.value if isinstance(agent, AgentPromptKey) else agent
def _policy_for(agent_name: Union[str, AgentPromptKey]) -> dict[str, set[str]]:
    name = _normalize_agent_name(agent_name)
    if name not in AGENT_TOOL_POLICY:
        raise GuardrailViolation(f"Unknown agent policy: {name}")
    return AGENT_TOOL_POLICY[name]



def allowed_registry_tools(agent_name: Union[str, AgentPromptKey]) -> set[str]:
    return set(_policy_for(agent_name)["registry_tools"])



def allowed_langchain_tools(agent_name: Union[str, AgentPromptKey]) -> set[str]:
    return set(_policy_for(agent_name)["langchain_tools"])



def ensure_tool_allowed(agent_name: Union[str, AgentPromptKey], tool_name: str) -> None:
    if tool_name not in allowed_registry_tools(agent_name):
        raise GuardrailViolation(
            f"Agent '{_normalize_agent_name(agent_name)}' is not allowed to call tool '{tool_name}'"
        )



def filter_langchain_tools(agent_name: Union[str, AgentPromptKey], tools: Iterable) -> list:
    allowed = allowed_langchain_tools(agent_name)
    return [tool for tool in tools if getattr(tool, "name", None) in allowed]