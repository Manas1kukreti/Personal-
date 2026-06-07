"""Regression tests for validator and routing consistency."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.validator import validate_data
from ledgerflow_agent.nodes import validation_node


def test_validate_data_returns_errors_list_on_invalid_json():
    result = validate_data("sample email", "{not-json")

    assert result["status"] == "invalid"
    assert "errors" in result
    assert result["errors"]


def test_validate_data_returns_errors_list_on_empty_payload():
    result = validate_data("sample email", "[]")

    assert result["status"] == "invalid"
    assert "errors" in result
    assert result["errors"][0]["error"] == "NO FINANCIAL DATA EXTRACTED"


def test_validation_node_marks_invalid_status_as_failed(monkeypatch):
    monkeypatch.setattr(
        "ledgerflow_agent.nodes.call_tool",
        lambda *args, **kwargs: {"status": "invalid", "error": "boom"},
    )

    state = {
        "email_text": "sample email",
        "extracted_data": [{"voucher_date": "2024-01-01"}],
        "memory_summary": {},
        "retry_count": 0,
    }

    result = validation_node(state)

    assert result["processing_status"] == "validation_failed"
    assert result["retry_count"] == 1
    assert result["validation_result"]["status"] == "invalid"

