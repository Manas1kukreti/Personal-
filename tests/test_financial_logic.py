"""Tests for financial logic and business rules"""

import pytest
import pandas as pd
from pathlib import Path

# Adjust path to import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from tools.financial_logic_tool import (
    determine_debit_credit,
    financial_logic_tool,
    clean_amount,
    rule_from_business_logic,
    rule_from_subclass,
    rule_from_keywords
)
from agents.validator import safe_float


class TestBusinessRulePriority:
    """Test suite for business rule priority logic."""
    
    def test_business_rule_beats_subclass_rule(self):
        """
        Test that business rules have higher priority than subclass rules.
        
        Priority: Business Rules > Subclass Rules > Keyword Fallback
        
        Using actual production function: Credit Sales transaction should
        apply business rule and credit sales account (credit) beats subclass.
        """
        # Call actual production function with credit sales business rule
        debit, credit, source = determine_debit_credit(
            amount=1000,
            details="credit sales",
            account="sales",
            subclass="income",
            subaccount="sales"
        )
        
        # Should apply business rule for credit sales -> sales = credit
        assert source == "business_rule"
        assert credit == "1000"
        assert debit == ""
    
    def test_subclass_rule_beats_keyword_fallback(self):
        """
        Test that subclass rules beat keyword fallback.
        
        When no business rule matches, subclass rules should be applied before
        keyword matching.
        """
        # Call with no business rule match, only subclass
        debit, credit, source = determine_debit_credit(
            amount=500,
            subclass="assets",
            details="some generic transaction",
            account="unknown",
            subaccount="unknown"
        )
        
        # Should apply subclass rule (asset -> debit for positive)
        assert source == "subclass"
        assert debit == "500"
        assert credit == ""
    
    def test_priority_chain_with_real_data(self):
        """
        Test the complete priority chain with a DataFrame and financial_logic_tool.
        
        Create a transaction that matches business rule and verify it beats
        the subclass rule.
        """
        df = pd.DataFrame([
            {
                "voucher_number": "V001",
                "particulars": "cost of sales",
                "account": "inventory",
                "account_subclass": "assets",
                "amount": 2000
            }
        ])
        
        result = financial_logic_tool(df)
        
        # Business rule for cost of sales -> inventory = credit
        credit_val = result.iloc[0]["credit_amount"]
        credit_val = float(credit_val) if credit_val else 0.0
        
        debit_val = result.iloc[0]["debit_amount"]
        debit_val = float(debit_val) if debit_val else 0.0
        
        assert credit_val == 2000.0
        assert debit_val == 0.0



class TestBracketAmountConversion:
    """Test suite for bracket amount conversion."""
    
    def test_bracket_conversion_to_negative_with_clean_amount(self):
        """
        Test that (X) is converted to -X using actual clean_amount function.
        """
        # Test actual clean_amount function
        result = clean_amount("(1000.00)")
        assert result == -1000.0
    
    def test_bracket_with_decimal_clean_amount(self):
        """Test bracket conversion with decimal places using clean_amount."""
        result = clean_amount("(123.45)")
        assert result == -123.45
    
    def test_bracket_with_commas_clean_amount(self):
        """
        Test bracket conversion with comma separators using clean_amount.
        """
        result = clean_amount("(1,000,000.00)")
        assert result == -1000000.0
    
    def test_negative_already_negative_clean_amount(self):
        """Test that -X stays -X (no double negation) with clean_amount."""
        result = clean_amount("-1000.00")
        assert result == -1000.0
    
    def test_positive_amount_clean_amount(self):
        """Test that positive amounts remain positive."""
        result = clean_amount("5000.50")
        assert result == 5000.50
    
    def test_bracket_conversion_in_debit_credit(self):
        """
        Test that bracket amounts work correctly end-to-end with
        determine_debit_credit function.
        """
        # Negative amount (from brackets) should go to credit for assets
        debit, credit, source = determine_debit_credit(
            amount=-5000,
            subclass="assets"
        )
        
        assert debit == ""
        assert credit == "5000"
    
    def test_safe_float_bracket_conversion(self):
        """Test safe_float function handles bracket conversion."""
        result = safe_float("(2500.00)")
        assert result == -2500.0
    
    def test_safe_float_with_commas(self):
        """Test safe_float handles commas correctly."""
        result = safe_float("1,500.50")
        assert result == 1500.50
    
    def test_safe_float_empty_string(self):
        """Test safe_float returns 0.0 for empty string."""
        result = safe_float("")
        assert result == 0.0
    
    def test_safe_float_none(self):
        """Test safe_float returns 0.0 for None."""
        result = safe_float(None)
        assert result == 0.0
    
    def test_safe_float_invalid_string(self):
        """Test safe_float returns 0.0 for invalid input."""
        result = safe_float("not_a_number")
        assert result == 0.0



class TestVoucherPairing:
    """Test suite for voucher pairing logic."""
    
    def test_voucher_pairing_same_date_debit_credit_match(self):
        """
        Test voucher pairing with matching debit and credit amounts.
        
        Two transactions: one with debit, one with credit on same date
        should be paired correctly.
        """
        df = pd.DataFrame([
            {
                "voucher_number": "V001",
                "voucher_date": "2024-01-15",
                "particulars": "cash sales",
                "account": "sales",
                "amount": 1000,
                "account_subclass": "income"
            },
            {
                "voucher_number": "V001",
                "voucher_date": "2024-01-15",
                "particulars": "cash sales",
                "account": "cash at bank",
                "amount": 1000,
                "account_subclass": "assets"
            }
        ])
        
        result = financial_logic_tool(df)
        
        # First transaction (sales) should credit 1000
        credit_val_1 = result.iloc[0]["credit_amount"]
        credit_val_1 = float(credit_val_1) if credit_val_1 else 0.0
        debit_val_1 = result.iloc[0]["debit_amount"]
        debit_val_1 = float(debit_val_1) if debit_val_1 else 0.0
        
        assert credit_val_1 == 1000.0
        assert debit_val_1 == 0.0
        
        # Second transaction (cash) should debit 1000
        debit_val_2 = result.iloc[1]["debit_amount"]
        debit_val_2 = float(debit_val_2) if debit_val_2 else 0.0
        credit_val_2 = result.iloc[1]["credit_amount"]
        credit_val_2 = float(credit_val_2) if credit_val_2 else 0.0
        
        assert debit_val_2 == 1000.0
        assert credit_val_2 == 0.0
    
    def test_voucher_pairing_different_dates_not_paired(self):
        """
        Test that vouchers with different dates are handled separately
        and not automatically paired.
        """
        df = pd.DataFrame([
            {
                "voucher_number": "V001",
                "voucher_date": "2024-01-15",
                "particulars": "Sales transaction",
                "account": "sales",
                "amount": 1000,
                "account_subclass": "income"
            },
            {
                "voucher_number": "V002",
                "voucher_date": "2024-01-16",
                "particulars": "Cash receipt",
                "account": "cash at bank",
                "amount": 1000,
                "account_subclass": "assets"
            }
        ])
        
        result = financial_logic_tool(df)
        
        # Both transactions should be processed independently
        assert len(result) == 2
        assert result.iloc[0]["voucher_number"] == "V001"
        assert result.iloc[1]["voucher_number"] == "V002"
    
    def test_voucher_pairing_requires_matching_amounts(self):
        """
        Test that voucher pairing only works with matching amounts
        on debit and credit sides.
        """
        df = pd.DataFrame([
            {
                "voucher_number": "V001",
                "voucher_date": "2024-01-15",
                "particulars": "Sales transaction",
                "account": "sales",
                "amount": 1000,
                "account_subclass": "income"
            },
            {
                "voucher_number": "V001",
                "voucher_date": "2024-01-15",
                "particulars": "Cash receipt",
                "account": "cash at bank",
                "amount": 500,  # Different amount
                "account_subclass": "assets"
            }
        ])
        
        result = financial_logic_tool(df)
        
        # Amounts don't match, so no pairing
        # First transaction: 1000 credit
        # Second transaction: 500 debit
        assert float(result.iloc[0]["credit_amount"]) == 1000.0
        assert float(result.iloc[1]["debit_amount"]) == 500.0
    
    def test_debit_credit_pairing_balancing(self):
        """
        Test that debit and credit sides of a paired transaction balance.
        
        Same voucher number and date with matching amounts on opposite sides.
        """
        df = pd.DataFrame([
            {
                "voucher_number": "V001",
                "voucher_date": "2024-01-15",
                "particulars": "cash sales",
                "account": "sales",
                "amount": 2000,
                "account_subclass": "income"
            },
            {
                "voucher_number": "V001",
                "voucher_date": "2024-01-15",
                "particulars": "cash sales",
                "account": "cash at bank",
                "amount": 2000,
                "account_subclass": "assets"
            }
        ])
        
        result = financial_logic_tool(df)
        
        # Cash sales business rule should apply
        # Sales should be credited (credit = 2000, debit = 0)
        # Cash should be debited (debit = 2000, credit = 0)
        debit_1 = float(result.iloc[0]["debit_amount"]) if result.iloc[0]["debit_amount"] else 0.0
        credit_1 = float(result.iloc[0]["credit_amount"]) if result.iloc[0]["credit_amount"] else 0.0
        debit_2 = float(result.iloc[1]["debit_amount"]) if result.iloc[1]["debit_amount"] else 0.0
        credit_2 = float(result.iloc[1]["credit_amount"]) if result.iloc[1]["credit_amount"] else 0.0
        
        total_debit = debit_1 + debit_2
        total_credit = credit_1 + credit_2
        
        # Should balance: total debit == total credit
        assert abs(total_debit - total_credit) < 0.01


class TestAccountClassification:
    """Test suite for account classification logic."""
    
    def test_asset_classification_using_real_function(self):
        """
        Test that assets are classified correctly by applying business rules.
        
        Bank accounts (assets) should debit for positive amounts.
        """
        debit, credit, source = determine_debit_credit(
            amount=5000,
            subclass="assets"
        )
        
        # Assets should debit for positive amounts
        assert debit == "5000"
        assert credit == ""
    
    def test_liability_classification_using_real_function(self):
        """
        Test that liabilities are classified correctly.
        
        Creditors (liabilities) should credit for positive amounts.
        """
        debit, credit, source = determine_debit_credit(
            amount=3000,
            subclass="liabilities"
        )
        
        # Liabilities should credit for positive amounts
        assert debit == ""
        assert credit == "3000"
    
    def test_income_classification_using_real_function(self):
        """
        Test that income is classified correctly.
        
        Sales revenue should credit for positive amounts when using
        proper account and subclass context.
        """
        # Use full context with business rule matching
        debit, credit, source = determine_debit_credit(
            amount=7500,
            details="cash sales",  # Use business rule context
            account="sales",
            subclass="income"
        )
        
        # Should match business rule: cash sales -> sales = credit
        assert source == "business_rule"
        assert debit == ""
        assert credit == "7500"
    
    def test_expense_classification_using_real_function(self):
        """
        Test that expenses are classified correctly.
        
        Expenses should debit for positive amounts.
        """
        debit, credit, source = determine_debit_credit(
            amount=1200,
            subclass="expense"
        )
        
        # Expenses should debit for positive amounts
        assert debit == "1200"
        assert credit == ""
    
    def test_asset_negative_amount(self):
        """
        Test asset with negative amount (credit reduction).
        """
        debit, credit, source = determine_debit_credit(
            amount=-1000,
            subclass="assets"
        )
        
        # Negative asset should go to credit (reduction)
        assert debit == ""
        assert credit == "1000"


class TestDTCDBalancing:
    """Test suite for DTCD (Debit Total vs Credit Total) balancing."""
    
    def test_balanced_transaction_no_imbalance(self):
        """
        Test that balanced transactions (debit total = credit total)
        have zero imbalance.
        """
        df = pd.DataFrame([
            {
                "voucher_number": "V001",
                "particulars": "cash sales",
                "account": "sales",
                "amount": 5000,
                "account_subclass": "income"
            },
            {
                "voucher_number": "V001",
                "particulars": "cash sales",
                "account": "cash at bank",
                "amount": 5000,
                "account_subclass": "assets"
            }
        ])
        
        result = financial_logic_tool(df)
        
        total_debit = sum(float(x) for x in result["debit_amount"] if x)
        total_credit = sum(float(x) for x in result["credit_amount"] if x)
        
        imbalance = abs(total_debit - total_credit)
        
        # Should be balanced (or very close due to floating point)
        assert imbalance < 0.01
    
    def test_imbalanced_transaction_detects_imbalance(self):
        """
        Test that imbalanced transactions (debit != credit) are detected
        when imbalance exceeds 0.01.
        """
        df = pd.DataFrame([
            {
                "voucher_number": "V001",
                "particulars": "cash sales",
                "account": "sales",
                "amount": 5000,
                "account_subclass": "income"
            },
            {
                "voucher_number": "V001",
                "particulars": "cash sales",
                "account": "cash at bank",
                "amount": 5001,  # Mismatched amount
                "account_subclass": "assets"
            }
        ])
        
        result = financial_logic_tool(df)
        
        total_debit = sum(float(x) for x in result["debit_amount"] if x)
        total_credit = sum(float(x) for x in result["credit_amount"] if x)
        
        imbalance = abs(total_debit - total_credit)
        
        # Should detect imbalance > 0.01
        assert imbalance > 0.01
    
    def test_multiple_transactions_balancing(self):
        """
        Test DTCD balancing with multiple transactions across different accounts.
        """
        df = pd.DataFrame([
            {
                "voucher_number": "V001",
                "particulars": "cash sales",
                "account": "sales",
                "amount": 3000,
                "account_subclass": "income"
            },
            {
                "voucher_number": "V001",
                "particulars": "cash sales",
                "account": "cash at bank",
                "amount": 2000,
                "account_subclass": "assets"
            },
            {
                "voucher_number": "V001",
                "particulars": "credit sales",
                "account": "trade receivables",
                "amount": 1000,
                "account_subclass": "assets"
            }
        ])
        
        result = financial_logic_tool(df)
        
        total_debit = sum(float(x) for x in result["debit_amount"] if x)
        total_credit = sum(float(x) for x in result["credit_amount"] if x)
        
        imbalance = abs(total_debit - total_credit)
        
        # Should balance when accounting rules are correctly applied
        assert imbalance < 0.01


class TestAccountRuleApplication:
    """Test suite for various account rule applications with real data."""
    
    def test_cost_of_sales_business_rule(self):
        """
        Test that cost of sales business rule correctly applies.
        
        Business rule: ("cost of sales", "cost of sales") -> debit
                       ("cost of sales", "inventory") -> credit
        """
        df = pd.DataFrame([{"amount": 1500, "particulars": "cost of sales", "account": "cost of sales"}])
        result = financial_logic_tool(df)
        assert float(result.iloc[0]["debit_amount"] or 0) == 1500.0
        assert float(result.iloc[0]["credit_amount"] or 0) == 0.0
    
    def test_credit_sales_business_rule(self):
        """
        Test that credit sales business rule correctly applies.
        
        Business rule: ("credit sales", "sales") -> credit
                       ("credit sales", "receivables") -> debit
        """
        df = pd.DataFrame([{"amount": 2500, "particulars": "credit sales", "account": "sales"}])
        result = financial_logic_tool(df)
        assert float(result.iloc[0]["credit_amount"] or 0) == 2500.0
        assert float(result.iloc[0]["debit_amount"] or 0) == 0.0
    
    def test_cash_sales_business_rule(self):
        """
        Test that cash sales business rule correctly applies.
        
        Business rule: ("cash sales", "sales") -> credit
                       ("cash sales", "cash at bank") -> debit
        """
        df = pd.DataFrame([{"amount": 1000, "particulars": "cash sales", "account": "cash at bank"}])
        result = financial_logic_tool(df)
        assert float(result.iloc[0]["debit_amount"] or 0) == 1000.0
        assert float(result.iloc[0]["credit_amount"] or 0) == 0.0
    
    def test_credit_expenses_business_rule(self):
        """
        Test that credit expenses business rule correctly applies.
        """
        df = pd.DataFrame([{"amount": 500, "particulars": "credit expenses", "account": "advertisements"}])
        result = financial_logic_tool(df)
        assert float(result.iloc[0]["debit_amount"] or 0) == 500.0
        assert float(result.iloc[0]["credit_amount"] or 0) == 0.0
    
    def test_keyword_fallback_when_no_business_or_subclass_rule(self):
        """
        Test keyword fallback when no business rule or subclass rule matches.
        
        A transaction with "bank" in details should be classified as asset (debit).
        """
        debit, credit, source = determine_debit_credit(
            amount=800,
            details="Transfer to bank account",
            account="unknown",
            subclass=None
        )
        
        # Should fall back to keyword matching for "bank" -> asset
        assert source == "keyword"
        assert debit == "800"
        assert credit == ""
    
    def test_sign_fallback_positive(self):
        """
        Test sign fallback for positive amount with no matching rules.
        
        Positive amounts should go to debit as default.
        """
        debit, credit, source = determine_debit_credit(
            amount=600,
            details="unmatched",
            account="unknown",
            subclass=None
        )
        
        # Should fall back to sign (positive -> debit)
        assert debit == "600"
        assert credit == ""
    
    def test_sign_fallback_negative(self):
        """
        Test sign fallback for negative amount with no matching rules.
        
        Negative amounts should go to credit as default.
        """
        debit, credit, source = determine_debit_credit(
            amount=-300,
            details="unmatched",
            account="unknown",
            subclass=None
        )
        
        # Should fall back to sign (negative -> credit)
        assert debit == ""
        assert credit == "300"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
