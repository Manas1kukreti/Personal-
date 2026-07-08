from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import time
from typing import Any, Literal

logger = logging.getLogger("ledgerflow.nodes")

from pydantic import BaseModel, Field

from config_loader import get_workflow_config
from ledgerflow_agent.guardrails import safe_error_message, validate_final_output
from ledgerflow_agent.memory import load_memory, save_memory, summarise_memory, update_memory
from ledgerflow_agent.prompts import SUPERVISOR_PROMPT, get_agent_prompt, get_all_agent_profiles
from ledgerflow_agent.registry import call_tool
from ledgerflow_agent.routing import (
    decide_after_input,
    decide_after_repair,
    decide_after_start,
    decide_after_ui,
    decide_after_validation,
)
from ledgerflow_agent.state import LedgerFlowState
from ledgerflow_agent.utils import (
    append_tool,
    ensure_json_string,
    has_balance_errors,
    is_structured_transaction_data,
    metric_duration_ms,
    normal_validation_errors,
    coerce_transaction_payload,
    utc_now_iso,
)


def _get_agent_output(response: Any) -> str:
    if isinstance(response, dict):
        return response.get("output", str(response))
    return str(response)


def _call_tool_with_timeout(agent_name: str, tool_name: str, *args: Any, timeout: int = 30) -> Any:
    """Execute call_tool in a background thread with a timeout constraint."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(call_tool, tool_name, *args, agent_name=agent_name)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            logger.error("Tool call '%s' timed out after %d seconds.", tool_name, timeout)
            raise TimeoutError(f"Tool call '{tool_name}' timed out after {timeout} seconds") from exc


class RouteDecision(BaseModel):
    next_node: str = Field(description="The exact name of the next valid StateGraph node to transition to.")


def _max_retries() -> int:
    return int(get_workflow_config().get("max_retries", 5))


def _required_fields() -> list[str]:
    return list(get_workflow_config().get("structured_data_required_fields", []))


def start_node(state: LedgerFlowState) -> dict[str, Any]:
    memory_snapshot = load_memory()
    return {
        "started_at": state.get("started_at") or time.time(),
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", _max_retries()),
        "processing_status": "started",
        "tools_used": list(state.get("tools_used") or []),
        "tool_results": dict(state.get("tool_results") or {}),
        "errors": list(state.get("errors") or []),
        "warnings": list(state.get("warnings") or []),
        "agent_metadata": {
            "agent_name": "LedgerFlow Agent",
            "agent_version": "2.1.0",
            "architecture": "LangGraph supervised financial ETL",
            "execution_timestamp": utc_now_iso(),
        },
        "agent_prompts": get_all_agent_profiles(),
        "active_agent": "supervisor",
        "active_agent_prompt": get_agent_prompt("supervisor"),
        "memory_snapshot": memory_snapshot,
        "memory_summary": summarise_memory(memory_snapshot),
        "user_preferences": dict(state.get("user_preferences") or {}),
    }


def input_node(state: LedgerFlowState) -> dict[str, Any]:
    # ── LOCAL FILE BYPASS (for testing without email) ──────────────────────
    local_file = os.getenv("LOCAL_FILE")
    if local_file:
        logger.info("[DEV] Skipping email fetch. Using local file: %s", local_file)
        result = call_tool("read_excel", local_file, agent_name="input")
        update = append_tool(state, "fetch_email", {"chars": len(str(result))})
        return {
            **update,
            "email_text": str(result),
            "processing_status": "input_ready",
            "active_agent": "input",
            "active_agent_prompt": get_agent_prompt("input"),
        }
    # ── END BYPASS ─────────────────────────────────────────────────────────

    existing_email_text = state.get("email_text")
    result = existing_email_text or ""

    if not result:
        try:
            result = call_tool("fetch_email", agent_name="input")
        except Exception as exc:
            return {
                "email_text": existing_email_text or "",
                "processing_status": "input_failed",
                "errors": [{"error": "Input fetch failed", "details": safe_error_message(exc)}],
                "active_agent": "input",
                "active_agent_prompt": get_agent_prompt("input"),
            }

    structured_payload = coerce_transaction_payload(result)
    if structured_payload:
        update = append_tool(state, "fetch_email", {"chars": len(result or "")})
        return {
            **update,
            "email_text": result or "",
            "extracted_data": structured_payload,
            "processing_status": "structured_input_ready",
            "active_agent": "input",
            "active_agent_prompt": get_agent_prompt("input"),
        }

    update = append_tool(state, "fetch_email", {"chars": len(result or "")})
    output: dict[str, Any] = {
        **update,
        "email_text": result or "",
        "processing_status": "input_ready",
        "active_agent": "input",
        "active_agent_prompt": get_agent_prompt("input"),
    }

    return output


def preprocessing_tools_node(state: LedgerFlowState) -> dict[str, Any]:
    logger.info("Executing preprocessing tools node...")
    return {
        "processing_status": "preprocessing_completed",
        "active_agent": "input",
        "active_agent_prompt": get_agent_prompt("input"),
    }


def extraction_node(state: LedgerFlowState) -> dict[str, Any]:
    existing_data = state.get("extracted_data")
    if is_structured_transaction_data(existing_data, _required_fields()):
        return {
            "processing_status": "extraction_skipped",
            "active_agent": "extraction",
            "active_agent_prompt": get_agent_prompt("extraction"),
        }

    email_text = state.get("email_text", "")
    structured_email = coerce_transaction_payload(email_text)
    if structured_email:
        update = append_tool(state, "extract_data", "skipped_structured_source")
        return {
            **update,
            "extracted_data": structured_email,
            "processing_status": "extraction_skipped",
            "active_agent": "extraction",
            "active_agent_prompt": get_agent_prompt("extraction"),
        }

    try:
        from agents.react_agent import create_react_agent

        agent = create_react_agent("extraction")
        prompt = (
            f"{get_agent_prompt('extraction')}\n"
            f"Memory Summary: {json.dumps(state.get('memory_summary', {}), default=str)}\n"
            f"Extract structured financial transactions from this text: {email_text[:1200]}"
        )
        response = agent.invoke({"input": prompt})
        extracted = _get_agent_output(response)

        if "```json" not in extracted and not extracted.strip().startswith("["):
            extracted = call_tool("extract_data", email_text, agent_name="extraction")
    except Exception as exc:
        retry_count = int(state.get("retry_count", 0))
        return {
            "processing_status": "extraction_failed",
            "retry_count": retry_count,
            "errors": [{"error": "Extraction agent failed", "details": safe_error_message(exc)}],
            "active_agent": "extraction",
            "active_agent_prompt": get_agent_prompt("extraction"),
        }

    update = append_tool(state, "extract_data", {"chars": len(extracted or "")})
    structured_extracted = coerce_transaction_payload(extracted)
    return {
        **update,
        "extracted_data": structured_extracted if structured_extracted is not None else json.loads(ensure_json_string(extracted)) if isinstance(extracted, str) else extracted,
        "processing_status": "data_extracted",
        "active_agent": "extraction",
        "active_agent_prompt": get_agent_prompt("extraction"),
    }


def validation_node(state: LedgerFlowState) -> dict[str, Any]:
    email_text = state.get("email_text", "")
    extracted_data = state.get("extracted_data")
    if extracted_data is None:
        extracted_data = email_text
    result = None

    # ── Fast path: call validate_data directly (no LLM needed) ──────────
    try:
        result = call_tool(
            "validate_data",
            email_text,
            json.dumps(extracted_data, default=str),
            agent_name="validation",
        )
        logger.info("[ValidationNode] Direct validate_data call succeeded.")
    except Exception as exc:
        logger.warning("[ValidationNode] Direct validate_data failed: %s — trying ReAct fallback.", safe_error_message(exc))
        result = None

    # ── Slow path: ReAct agent fallback (only if direct call failed) ────
    if result is None:
        try:
            from agents.react_agent import create_react_agent

            agent = create_react_agent("validation")
            prompt = (
                f"{get_agent_prompt('validation')}\n"
                f"Memory Summary: {json.dumps(state.get('memory_summary', {}), default=str)}\n"
                f"Validate the following financial data for completeness and correctness:\n"
                f"Email: {email_text[:500]}\n"
                f"Extracted Data: {json.dumps(extracted_data, default=str)}\n"
                f"Check all required fields are present and valid."
            )
            response = agent.invoke({"input": prompt})
            raw_result = _get_agent_output(response)

            try:
                parsed = json.loads(raw_result)
                if isinstance(parsed, dict) and "status" in parsed:
                    result = parsed
            except Exception:
                result = None
        except Exception as exc:
            logger.warning("Validation agent failed: %s", safe_error_message(exc))
            result = None

    # ── Hard failure ────────────────────────────────────────────────────
    if result is None:
        retry_count = int(state.get("retry_count", 0)) + 1
        return {
            "processing_status": "validation_failed",
            "retry_count": retry_count,
            "validation_result": {
                "status": "invalid",
                "errors": [{"error": "Both direct validation and ReAct agent failed"}],
            },
            "active_agent": "validation",
            "active_agent_prompt": get_agent_prompt("validation"),
        }

    retry_count = int(state.get("retry_count", 0))
    has_errors = bool(normal_validation_errors(result)) or str(result.get("status", "")).lower() != "valid"
    if has_errors:
        retry_count += 1

    update = append_tool(state, "validate_data", result)
    return {
        **update,
        "validation_result": result,
        "retry_count": retry_count,
        "processing_status": "validation_failed" if has_errors else "validated",
        "warnings": list(result.get("warnings", [])),
        "active_agent": "validation",
        "active_agent_prompt": get_agent_prompt("validation"),
    }


def repair_node(state: LedgerFlowState) -> dict[str, Any]:
    validation_result = state.get("validation_result", {})
    extracted_data = state.get("extracted_data", [])

    try:
        parsed_data = extracted_data if isinstance(extracted_data, list) else json.loads(extracted_data)
    except Exception as exc:
        retry_count = int(state.get("retry_count", 0))
        return {
            "processing_status": "repair_failed",
            "retry_count": retry_count,
            "errors": [{"error": "Could not parse extracted data for repair", "details": safe_error_message(exc)}],
            "active_agent": "re_extraction",
            "active_agent_prompt": get_agent_prompt("re_extraction"),
        }

    if not isinstance(parsed_data, list):
        retry_count = int(state.get("retry_count", 0))
        return {
            "processing_status": "repair_failed",
            "retry_count": retry_count,
            "errors": [{"error": "Extracted data is not a transaction list"}],
            "active_agent": "re_extraction",
            "active_agent_prompt": get_agent_prompt("re_extraction"),
        }

    all_errors = validation_result.get("errors", [])
    hints = state.get("orchestrator_hints") or {}

    from agents.repair_agent import triage

    repair_plan = triage(all_errors, hints, state)

    error_index: dict[tuple[int, str], dict[str, Any]] = {}
    for err in all_errors:
        field = err.get("failed_field")
        idx = int(err.get("transaction_index", 0))
        if field:
            error_index[(idx, field)] = err

    repaired_fields: list[dict[str, Any]] = []

    for repair_item in repair_plan:
        if repair_item.strategy == "skip":
            logger.info("[RepairNode] Skipping field '%s': %s", repair_item.field, repair_item.reason)
            continue

        matching_errors = [
            (idx, err)
            for (idx, f), err in error_index.items()
            if f == repair_item.field
        ]

        if not matching_errors:
            continue

        for transaction_index, error in matching_errors:
            if transaction_index >= len(parsed_data):
                continue

            current_value = error.get("current_value", "")
            failed_transaction = parsed_data[transaction_index]

            logger.info(
                "[RepairNode] Fixing transaction %d field '%s' (strategy=%s)",
                transaction_index, repair_item.field, repair_item.strategy,
            )

            try:
                corrected_value = _call_tool_with_timeout("re_extraction", "re_extract_field", failed_transaction, repair_item.field, current_value, timeout=30)
            except Exception:
                corrected_value = None

            if corrected_value is None:
                logger.warning("[RepairNode] Could not recover field '%s'", repair_item.field)
                continue

            parsed_data[transaction_index][repair_item.field] = corrected_value
            repaired_fields.append(
                {
                    "transaction_index": transaction_index,
                    "field": repair_item.field,
                    "value": corrected_value,
                    "strategy": repair_item.strategy,
                }
            )

    if not repaired_fields:
        retry_count = int(state.get("retry_count", 0))
        return {
            "processing_status": "repair_failed",
            "retry_count": retry_count,
            "errors": [{"error": "No invalid fields could be repaired"}],
            "repair_plan": [item.model_dump() for item in repair_plan],
            "active_agent": "re_extraction",
            "active_agent_prompt": get_agent_prompt("re_extraction"),
        }

    update = append_tool(state, "re_extract_field", repaired_fields)
    return {
        **update,
        "extracted_data": parsed_data,
        "processing_status": "repaired",
        "repair_plan": [item.model_dump() for item in repair_plan],
        "active_agent": "re_extraction",
        "active_agent_prompt": get_agent_prompt("re_extraction"),
    }


def ui_node(state: LedgerFlowState) -> dict[str, Any]:
    validation_result = dict(state.get("validation_result", {}))

    data_list = validation_result.get("data")
    if isinstance(data_list, list):
        repaired_history = []
        re_extract_calls = state.get("tool_results", {}).get("re_extract_field", [])
        for call_result in re_extract_calls:
            if isinstance(call_result, list):
                repaired_history.extend(call_result)
            elif isinstance(call_result, dict):
                repaired_history.append(call_result)

        for row_idx, row in enumerate(data_list):
            repairs_for_row = [
                f"{r.get('field')} ({r.get('strategy')})"
                for r in repaired_history
                if int(r.get("transaction_index", -1)) == row_idx
            ]
            if repairs_for_row:
                row["Repairs Applied"] = ", ".join(repairs_for_row)

    ui_result = {"excel_generated": False, "api_uploaded": False, "status": "failed"}
    errors = []

    try:
        call_tool("save_json", validation_result, agent_name="ui")
        call_tool("generate_excel", validation_result, agent_name="ui")
        ui_result["excel_generated"] = True
    except Exception as exc:
        errors.append({"error": "UI agent failed to generate Excel", "details": safe_error_message(exc)})

    if ui_result["excel_generated"]:
        try:
            token = call_tool("login", agent_name="ui")
            upload_response = call_tool("upload_file", token=token, agent_name="ui")
            ui_result["api_uploaded"] = True
            ui_result["status"] = "success"
            ui_result["upload_response"] = upload_response
        except Exception as exc:
            errors.append({"error": "UI agent failed to upload API payload", "details": safe_error_message(exc)})
            ui_result["status"] = "failed"

    update = append_tool(state, "push_to_ui", ui_result)

    if ui_result["status"] == "success" and state.get("validation_result", {}).get("warnings"):
        if has_balance_errors(state.get("validation_result")):
            return {**update, "processing_status": "ui_pushed_with_alert", "ui_result": ui_result, "errors": errors}

    if ui_result["status"] == "success":
        return {**update, "processing_status": "completed", "ui_result": ui_result}

    return {**update, "processing_status": "ui_failed", "ui_result": ui_result, "errors": errors}


def notification_node(state: LedgerFlowState) -> dict[str, Any]:
    validation_result = state.get("validation_result", {})
    balance_errors = [
        error
        for error in validation_result.get("errors", [])
        if "not balanced" in str(error.get("error", "")).lower()
        or "difference" in str(error.get("error", "")).lower()
    ]

    ui_alert_result: dict[str, Any] = {"alerts_sent": 0, "status": "skipped"}
    if balance_errors:
        ui_alerts_sent = []
        try:
            token = call_tool("login", agent_name="notification")
            for error in balance_errors:
                payload = {
                    "Entry no": error.get("Entry no", "UNKNOWN"),
                    "Account code": error.get("Account code", "UNKNOWN"),
                    "Sub Account": error.get("Sub Account", "UNKNOWN"),
                    "difference": error.get("difference", 0),
                    "status": "FAILED",
                }
                ui_alerts_sent.append(
                    call_tool(
                        "push_validation_alert",
                        token=token,
                        alert_payload=payload,
                        agent_name="notification",
                    )
                )
            ui_alert_result = {"alerts_sent": len(ui_alerts_sent), "status": "success", "details": ui_alerts_sent}
        except Exception as exc:
            ui_alert_result = {"alerts_sent": 0, "status": "failed", "error": safe_error_message(exc)}

    smtp_result: dict[str, Any] = {"status": "skipped"}
    if not balance_errors:
        try:
            from agents.notification_agent import send_failure_notification
            email_response = send_failure_notification(validation_result)
            smtp_result = {"status": "success", "result": email_response}
        except Exception as exc:
            smtp_result = {"status": "failed", "error": safe_error_message(exc)}
    else:
        logger.info("DTCD balance errors detected — skipping SMTP manager email notification.")

    result = {
        "status": "manual_review_required",
        "ui_alert": ui_alert_result,
        "smtp_notification": smtp_result,
        "balance_errors": balance_errors,
    }
    update = append_tool(state, "push_validation_alert", result)
    return {
        **update,
        "notification_result": result,
        "processing_status": "manual_review_required",
        "active_agent": "notification",
        "active_agent_prompt": get_agent_prompt("notification"),
    }


def finalize_node(state: LedgerFlowState) -> dict[str, Any]:
    completed_at = time.time()
    metrics = {
        "total_duration_ms": metric_duration_ms(state.get("started_at")),
        "retry_count": int(state.get("retry_count", 0)),
        "tool_calls": len(state.get("tools_used") or []),
        "fallback_activated": state.get("processing_status") in {"repair_failed", "manual_review_required", "ui_failed"},
    }

    final_output = {
        "status": state.get("processing_status", "completed"),
        "validation_result": state.get("validation_result"),
        "ui_result": state.get("ui_result"),
        "notification_result": state.get("notification_result"),
        "tools_used": state.get("tools_used", []),
        "agent_metadata": state.get("agent_metadata", {}),
        "agent_prompts": state.get("agent_prompts", {}),
        "memory_summary": state.get("memory_summary", {}),
        "metrics": metrics,
        "completed_at": utc_now_iso(),
    }

    final_output = validate_final_output(final_output)

    failed_statuses = {"input_failed", "extraction_failed", "repair_failed", "ui_failed"}
    processing_status = str(state.get("processing_status", ""))
    is_failed_run = processing_status in failed_statuses or processing_status.endswith("_failed")

    if is_failed_run:
        logger.warning("finalize_node: run ended with status '%s' — skipping memory update to prevent state corruption.", processing_status)
        updated_memory = state.get("memory_snapshot", {})
    else:
        updated_memory = update_memory(state.get("memory_snapshot", {}), state, final_output)
        save_memory(updated_memory)

    return {
        "completed_at": completed_at,
        "metrics": metrics,
        "memory_snapshot": updated_memory,
        "memory_summary": summarise_memory(updated_memory),
        "final_output": final_output,
    }


def _llm_route(state: LedgerFlowState, valid_nodes: list[str], fallback: str, max_retries: int = 3) -> str:
    from agents.react_agent import get_supervisor_llm

    for attempt in range(1, max_retries + 1):
        try:
            prompt = f"""
{SUPERVISOR_PROMPT}

You are a routing expert. Analyze the current LedgerFlow state and decide the next node.

VALID NODES: {', '.join(valid_nodes)}

CURRENT STATE:
{json.dumps({
    "processing_status": state.get("processing_status"),
    "retry_count": state.get("retry_count"),
    "validation_result": state.get("validation_result", {}),
    "memory_summary": state.get("memory_summary", {}),
}, indent=2, default=str)}

You MUST respond with EXACTLY ONE valid node name from the list above.
No explanation. No markdown. Just the node name.
"""
            structured_llm = get_supervisor_llm().with_structured_output(RouteDecision)
            decision = structured_llm.invoke(prompt)

            if decision.next_node in valid_nodes:
                logger.info("✓ LLM Routing (Attempt %d/%d): %s", attempt, max_retries, decision.next_node)
                return decision.next_node
            else:
                logger.warning(
                    "LLM returned invalid node '%s' (Attempt %d/%d). Valid: %s",
                    decision.next_node, attempt, max_retries, valid_nodes,
                )

        except Exception as exc:
            logger.warning("LLM Routing attempt %d/%d failed: %s", attempt, max_retries, safe_error_message(exc))
            if attempt == max_retries:
                logger.warning("All %d LLM attempts exhausted. Using fallback: %s", max_retries, fallback)

    return fallback


def route_after_start(state: LedgerFlowState) -> Literal["input", "validate"]:
    return decide_after_start(state)  # type: ignore[return-value]


def route_after_input(state: LedgerFlowState) -> Literal["extract", "validate", "notification"]:
    fallback = decide_after_input(state)
    return _llm_route(state, ["extract", "validate", "notification"], fallback)  # type: ignore[return-value]


def route_after_validation(state: LedgerFlowState) -> Literal["ui", "repair", "notification"]:
    fallback = decide_after_validation(state)
    return _llm_route(state, ["ui", "repair", "notification"], fallback)  # type: ignore[return-value]


def route_after_repair(state: LedgerFlowState) -> Literal["validate", "extract", "notification"]:
    fallback = decide_after_repair(state)
    return _llm_route(state, ["validate", "extract", "notification"], fallback)  # type: ignore[return-value]


def route_after_ui(state: LedgerFlowState) -> Literal["notification", "finalize"]:
    return decide_after_ui(state)  # type: ignore[return-value]


def route_after_supervisor(state: LedgerFlowState) -> Literal[
    "fetch_email", "preprocessing_tools", "extract_data", "validate", "re_extract", "push_to_ui", "notification"
]:
    email_text = state.get("email_text", "")
    extracted_data = state.get("extracted_data")
    status = state.get("processing_status", "")

    if not email_text:
        fallback = "fetch_email"
    elif status == "input_ready" or (email_text and status not in ["preprocessing_completed", "data_extracted", "validated", "repaired", "repair_failed"]):
        fallback = "preprocessing_tools"
    elif status == "preprocessing_completed" or not extracted_data:
        fallback = "extract_data"
    elif status in ["data_extracted", "repaired", "extraction_skipped"] or extracted_data:
        fallback = "validate"
    else:
        fallback = "validate"

    valid_nodes = ["fetch_email", "preprocessing_tools", "extract_data", "validate", "re_extract", "push_to_ui", "notification"]
    return _llm_route(state, valid_nodes, fallback)  # type: ignore[return-value]


def route_after_validate(state: LedgerFlowState) -> Literal["re_extract", "push_to_ui", "notification"]:
    fallback_val = decide_after_validation(state)
    mapping = {
        "ui": "push_to_ui",
        "repair": "re_extract",
        "notification": "notification"
    }
    fallback = mapping.get(fallback_val, "re_extract")
    return _llm_route(state, ["re_extract", "push_to_ui", "notification"], fallback)  # type: ignore[return-value]


def route_after_push_to_ui(state: LedgerFlowState) -> Literal["notification", "__end__"]:
    fallback_val = decide_after_ui(state)
    if fallback_val == "notification":
        return "notification"
    return "__end__"
