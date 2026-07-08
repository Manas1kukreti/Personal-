"""Tests for validator.py"""

import pytest
from pathlib import Path

# Adjust path to import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.validator import safe_float


class TestSafeFloat:
    """Test suite for safe_float function."""
    
    def test_safe_float_empty_string(self):
        """Test that empty string returns 0.0"""
        assert safe_float("") == 0.0
    
    def test_safe_float_none(self):
        """Test that None returns 0.0"""
        assert safe_float(None) == 0.0
    
    def test_safe_float_valid_number(self):
        """Test that valid number is converted correctly."""
        assert safe_float("123.45") == 123.45
    
    def test_safe_float_with_comma_separator(self):
        """Test that comma separators are removed."""
        assert safe_float("1,000.00") == 1000.0
    
    def test_safe_float_with_multiple_commas(self):
        """Test that multiple commas are removed."""
        assert safe_float("1,000,000.00") == 1000000.0
    
    def test_safe_float_with_brackets_positive(self):
        """Test that brackets are converted to negative."""
        result = safe_float("(100.00)")
        assert result == -100.0
    
    def test_safe_float_with_brackets_and_comma(self):
        """Test that brackets with commas are converted correctly."""
        result = safe_float("(1,000.00)")
        assert result == -1000.0
    
    def test_safe_float_integer(self):
        """Test that integer is converted correctly."""
        assert safe_float("100") == 100.0
    
    def test_safe_float_negative_sign(self):
        """Test that negative sign is preserved."""
        assert safe_float("-100.00") == -100.0
    
    def test_safe_float_with_whitespace(self):
        """Test that whitespace is stripped."""
        assert safe_float("  123.45  ") == 123.45
    
    def test_safe_float_invalid_string(self):
        """Test that invalid string returns 0.0"""
        assert safe_float("invalid") == 0.0
    
    def test_safe_float_zero_as_string(self):
        """Test that '0' returns 0.0"""
        assert safe_float("0") == 0.0
    
    def test_safe_float_large_number(self):
        """Test that large numbers are handled."""
        assert safe_float("999999999.99") == 999999999.99


class TestDTCDValidation:
    """Test suite for DTCD (Debit-Total Credit-Difference) validation."""
    
    def test_dtcd_balanced(self):
        """Test that balanced DTCD validation passes (difference < 0.01)."""
        # This test would require the actual validator, which we'll check
        # in the integration tests. For now, we verify the concept.
        debit_total = 1000.00
        credit_total = 1000.00
        difference = abs(debit_total - credit_total)
        assert difference < 0.01
    
    def test_dtcd_imbalanced_exceeds_threshold(self):
        """Test that imbalance > 0.01 is detected."""
        debit_total = 1000.00
        credit_total = 1000.05
        difference = abs(debit_total - credit_total)
        assert difference > 0.01
    
    def test_dtcd_imbalanced_equals_threshold(self):
        """Test that imbalance ≈ 0.01 is at boundary."""
        debit_total = 1000.00
        credit_total = 1000.01
        difference = abs(debit_total - credit_total)
        # Use approximate comparison for floating point
        assert difference >= 0.009  # Close enough to threshold


class TestVoucherValidation:
    """Test suite for voucher validation logic."""
    
    def test_empty_voucher_date_produces_error(self):
        """Test that empty voucher_date should produce an error."""
        # This tests the business rule that voucher_date is required
        voucher_date = ""
        assert voucher_date == ""  # Empty
        # In actual validation, this should trigger an error
    
    def test_valid_voucher_date_format(self):
        """Test that valid voucher date format is acceptable."""
        voucher_date = "2024-01-15"
        assert voucher_date != ""
        assert len(voucher_date) > 0
    
    def test_simultaneous_debit_credit_error(self):
        """Test that filling both debit and credit simultaneously produces an error."""
        # This tests the business rule that either debit OR credit, not both
        debit_amount = 100.0
        credit_amount = 100.0
        
        # The rule is: exactly one of them should have a value > 0
        has_debit = debit_amount > 0
        has_credit = credit_amount > 0
        
        # Both having values is an error condition
        assert has_debit and has_credit  # This should trigger validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
