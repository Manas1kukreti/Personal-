from __future__ import annotations

from typing import Any

from config_loader import get_workflow_config
from ledgerflow_agent.utils import has_balance_errors, is_structured_transaction_data, normal_validation_errors


def required_fields() -> list[str]:
    return list(get_workflow_config().get("structured_data_required_fields", []))


def decide_after_start(state: dict[str, Any]) -> str:
    return "validate" if is_structured_transaction_data(state.get("extracted_data"), required_fields()) else "input"


def decide_after_input(state: dict[str, Any]) -> str:
    if state.get("processing_status") == "input_failed":
        return "notification"
    return "validate" if is_structured_transaction_data(state.get("extracted_data"), required_fields()) else "extract"


def decide_after_validation(state: dict[str, Any]) -> str:
    validation_result = state.get("validation_result", {}) or {}
    retry_count = int(state.get("retry_count", 0))
    max_r = int(state.get("max_retries", get_workflow_config().get("max_retries", 5)))

    if str(validation_result.get("status", "")).lower() == "valid":
        return "ui"
    if has_balance_errors(validation_result):
        return "ui"
    if retry_count >= max_r:
        return "notification"
    if normal_validation_errors(validation_result) or str(validation_result.get("status", "")).lower() == "invalid":
        return "repair"
    return "ui"


def decide_after_repair(state: dict[str, Any]) -> str:
    if state.get("processing_status") == "repaired":
        return "validate"
    return "notification"


def decide_after_ui(state: dict[str, Any]) -> str:
    if state.get("processing_status") in {"ui_pushed_with_alert", "ui_failed"}:
        return "notification"
    return "finalize"

