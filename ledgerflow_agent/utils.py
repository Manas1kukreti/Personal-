from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_json_string(data: Any) -> str:
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2, default=str)


def parse_json_maybe(data: Any) -> Any:
    if not data:
        return None
    if not isinstance(data, str):
        return data
    try:
        return json.loads(data)
    except Exception:
        # Some email bodies concatenate HTML/text with an embedded JSON payload.
        # Try to recover a JSON array/object from the surrounding text.
        for open_char, close_char in (("[", "]"), ("{", "}")):
            start = data.find(open_char)
            end = data.rfind(close_char)
            if start != -1 and end != -1 and end > start:
                candidate = data[start : end + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    continue
        return None


def coerce_transaction_payload(data: Any) -> list[dict[str, Any]] | None:
    parsed = parse_json_maybe(data)
    if isinstance(parsed, dict):
        parsed = parsed.get("transactions") or parsed.get("data") or parsed
    if isinstance(parsed, list) and parsed and all(isinstance(row, dict) for row in parsed):
        return parsed
    return None


def is_structured_transaction_data(data: Any, required_fields: list[str] | None = None) -> bool:
    parsed = coerce_transaction_payload(data)
    if not parsed:
        return False
    first_row = parsed[0]
    if not required_fields:
        return True
    return any(field in first_row for field in required_fields)


def has_balance_errors(validation_result: dict[str, Any] | None) -> bool:
    if not validation_result:
        return False
    for error in validation_result.get("errors", []):
        text = str(error.get("error", "")).lower()
        if "not balanced" in text or "difference" in text:
            return True
    return False


def normal_validation_errors(validation_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not validation_result:
        return []
    errors: list[dict[str, Any]] = []
    for error in validation_result.get("errors", []):
        text = str(error.get("error", "")).lower()
        if "not balanced" not in text and "difference" not in text:
            errors.append(error)
    return errors


def metric_duration_ms(started_at: float | None) -> float:
    if not started_at:
        return 0.0
    return round((time.time() - started_at) * 1000, 1)


def append_tool(state: dict[str, Any], name: str, result: Any) -> dict[str, Any]:
    # Issue 12: Deduplicate tools_used — same tool should never appear twice
    existing_tools: list[str] = list(state.get("tools_used") or [])
    if name not in existing_tools:
        existing_tools.append(name)

    # Accumulate tool call results as a list so multiple calls to the same tool
    # are all preserved (e.g. re_extract_field called many times per repair cycle)
    tool_results: dict[str, Any] = dict(state.get("tool_results") or {})
    existing_results = tool_results.get(name)
    if existing_results is None:
        tool_results[name] = result
    elif isinstance(existing_results, list):
        tool_results[name] = existing_results + [result]
    else:
        tool_results[name] = [existing_results, result]

    return {
        "tools_used": existing_tools,
        "tool_results": tool_results,
    }
