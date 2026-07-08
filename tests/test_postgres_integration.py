"""Unit tests for PostgreSQL database integration in ui_agent."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.ui_agent import save_to_postgres


def test_save_to_postgres_no_env(monkeypatch, capsys):
    """Test that database save is skipped gracefully if DATABASE_URL is not set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    
    validated_data = {
        "status": "valid",
        "data": [{"voucher_date": "2024-01-01", "entry_no": "1", "debit_amount": "100.0"}]
    }
    
    # Should not crash
    save_to_postgres(validated_data)
    
    captured = capsys.readouterr()
    assert "DATABASE_URL is not set in environment" in captured.out


def test_save_to_postgres_connection_failure(monkeypatch, capsys):
    """Test that connection failures are caught and logged as warnings instead of crashing."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid_user:invalid_pass@localhost:54321/invalid_db")
    
    validated_data = {
        "status": "valid",
        "data": [{"voucher_date": "2024-01-01", "entry_no": "1", "debit_amount": "100.0"}]
    }
    
    # Should not crash and should print warning
    save_to_postgres(validated_data)
    
    captured = capsys.readouterr()
    assert "Failed to save to PostgreSQL database" in captured.out or "Skipping database save" in captured.out


@patch("psycopg2.connect")
def test_save_to_postgres_success(mock_connect, monkeypatch, capsys):
    """Test successful database table creation and insertion path."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://mock_user:mock_pass@mock_host:5432/mock_db")
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    
    validated_data = {
        "status": "valid",
        "data": [
            {
                "voucher_date": "2024-01-01",
                "entry_no": "1",
                "sub_account": "Sales",
                "details": "Invoice 123",
                "debit_amount": "100.0",
                "credit_amount": "0.0",
                "account_code": "400",
                "country": "US",
                "region": "West",
                "class_name": "Revenue",
                "account_subclass": "ProductSales"
            }
        ]
    }
    
    save_to_postgres(validated_data)
    
    # Verify connect was called
    mock_connect.assert_called_once_with("postgresql://mock_user:mock_pass@mock_host:5432/mock_db")
    
    # Verify cursor execute was called for CREATE TABLE and INSERT
    assert mock_cur.execute.call_count >= 2
    
    # Verify connection was closed
    mock_cur.close.assert_called_once()
    mock_conn.close.assert_called_once()
    
    captured = capsys.readouterr()
    assert "Successfully saved 1 transactions" in captured.out
