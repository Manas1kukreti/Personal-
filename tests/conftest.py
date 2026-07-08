"""Test fixtures and configuration for LedgerFlow tests."""

import pytest
from pathlib import Path
import sys

# Add parent directory to path for imports
test_dir = Path(__file__).parent
project_dir = test_dir.parent
sys.path.insert(0, str(project_dir))

# Configure pytest
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", 
        "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture
def mock_state():
    """Fixture for mock agent state."""
    return {
        "email_text": "",
        "extracted_data": "",
        "validation_result": {},
        "corrected_data": {},
        "ui_result": {},
        "retry_count": 0,
        "processing_status": "",
    }


@pytest.fixture
def mock_validation_result_valid():
    """Fixture for valid validation result."""
    return {
        "status": "valid",
        "errors": [],
        "warnings": [],
    }


@pytest.fixture
def mock_validation_result_invalid():
    """Fixture for invalid validation result."""
    return {
        "status": "invalid",
        "errors": [
            {
                "error": "Field validation failed",
                "field": "amount",
                "transaction_index": 0,
            }
        ],
        "warnings": [],
    }


@pytest.fixture
def mock_validation_result_dtcd_error():
    """Fixture for DTCD balance error."""
    return {
        "status": "invalid",
        "errors": [
            {
                "error": "Total Debit and Credit not balanced",
                "difference": 10.50,
            }
        ],
        "warnings": [],
    }
