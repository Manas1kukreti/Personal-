"""Regression tests for structured payload detection."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from ledgerflow_agent.utils import coerce_transaction_payload, is_structured_transaction_data


def test_embedded_json_array_is_detected():
    payload = """<div dir="ltr"><br></div>
    [
      {"voucher_number": "1", "voucher_date": "2024-01-01", "particulars": "Sales"}
    ]
    """

    parsed = coerce_transaction_payload(payload)

    assert parsed is not None
    assert parsed[0]["voucher_number"] == "1"
    assert is_structured_transaction_data(payload, ["voucher_number"])

