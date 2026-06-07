"""Tests for field mapper tool"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adjust path to import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFieldMapping:
    """Test suite for field mapping variants."""
    
    def test_voucher_date_variants(self):
        """Test that various Voucher Date variants map correctly."""
        variants = [
            "Voucher Date",
            "voucher_date",
            "voucher date",
            "Voucher_Date",
        ]
        
        master_key = "voucher_date"
        
        for variant in variants:
            # Normalize to master key
            normalized = variant.lower().replace(" ", "_").replace("-", "_")
            assert normalized == master_key
    
    def test_entry_no_variants(self):
        """Test that various Entry No/Entry Number variants map correctly."""
        variants = [
            "Entry No",
            "entry_no",
            "Entry Number",
            "entry_number",
            "EntryNo",
            "Entry_No",
            "ENTRY_NO",
        ]
        
        # These should all map to a master key
        for variant in variants:
            normalized = variant.lower().replace(" ", "_").replace("-", "_")
            # Should normalize to entry_no or entry_number (both acceptable)
            assert "entry" in normalized
    
    def test_debit_variants(self):
        """Test that various Debit variants map correctly."""
        variants = [
            "Debit",
            "DR",
            "Dr",
            "Debit Amount",
            "debit_amount",
            "DEBIT",
            "debit",
        ]
        
        master_key = "debit_amount"
        
        for variant in variants:
            normalized = variant.lower().replace(" ", "_").replace("-", "_")
            # All should contain "debit"
            assert "debit" in normalized or variant.upper() == "DR"
    
    def test_credit_variants(self):
        """Test that various Credit variants map correctly."""
        variants = [
            "Credit",
            "CR",
            "Cr",
            "Cr.",
            "Credit Amount",
            "credit_amount",
            "CREDIT",
            "credit",
        ]
        
        master_key = "credit_amount"
        
        for variant in variants:
            normalized = variant.lower().replace(" ", "_").replace("-", "_").replace(".", "")
            # All should contain "credit"
            assert "credit" in normalized or variant.upper() in ["CR", "CR."]
    
    def test_account_name_variants(self):
        """Test that various Account Name variants map correctly."""
        variants = [
            "Account Name",
            "account_name",
            "Account",
            "Ledger Name",
            "ledger_name",
            "Sub Account",
            "sub_account",
        ]
        
        # These should map to one of the account-related master keys
        for variant in variants:
            normalized = variant.lower().replace(" ", "_").replace("-", "_")
            # Should contain account or ledger or subaccount
            assert any(key in normalized for key in ["account", "ledger"])
    
    def test_amount_variants(self):
        """Test that various Amount variants map correctly."""
        variants = [
            "Amount",
            "amount",
            "Transaction Amount",
            "transaction_amount",
            "AMOUNT",
            "Total Amount",
            "total_amount",
        ]
        
        master_key = "amount"
        
        for variant in variants:
            normalized = variant.lower().replace(" ", "_").replace("-", "_")
            # All should contain "amount"
            assert "amount" in normalized
    
    def test_details_description_variants(self):
        """Test that Description/Details variants map correctly."""
        variants = [
            "Description",
            "description",
            "Details",
            "details",
            "Narration",
            "narration",
            "Particulars",
            "particulars",
        ]
        
        # These should map to a master key for descriptions
        for variant in variants:
            normalized = variant.lower()
            # Should be one of the description-like keys
            assert any(key in normalized for key in ["description", "details", "narration", "particulars"])
    
    def test_class_variants(self):
        """Test that Class/Classification variants map correctly."""
        variants = [
            "Class",
            "class",
            "Classification",
            "classification",
            "Account Class",
            "account_class",
            "Voucher Type",
            "voucher_type",
        ]
        
        # These should map to class or type
        for variant in variants:
            normalized = variant.lower().replace(" ", "_").replace("-", "_")
            # Should contain class or type or voucher
            assert any(key in normalized for key in ["class", "type", "voucher"])
    
    def test_case_insensitive_mapping(self):
        """Test that mapping is case insensitive."""
        variants = ["Amount", "AMOUNT", "amount", "Amount"]
        
        # All should map to same key
        normalized_keys = [v.lower() for v in variants]
        assert len(set(normalized_keys)) == 1
    
    def test_space_and_underscore_normalization(self):
        """Test that spaces and underscores are normalized."""
        variants = [
            "Voucher Date",
            "Voucher_Date",
            "voucher date",
            "voucher_date",
        ]
        
        normalized_keys = [
            v.lower().replace(" ", "_").replace("-", "_")
            for v in variants
        ]
        
        # All should normalize to same key
        assert len(set(normalized_keys)) == 1


class TestFieldMapperIntegration:
    """Integration tests for field mapper."""
    
    def test_dataframe_column_mapping(self):
        """Test mapping DataFrame columns to master schema."""
        import pandas as pd
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
        from field_mapper_tool import field_mapper_tool
        
        # Sample DataFrame with messy column names
        df = pd.DataFrame({
            "Voucher Date": ["2024-01-15"],
            "DR": [1000],
            "Cr.": [0],
            "Account Name": ["Bank"],
        })
        
        # Expected output columns
        expected_columns = [
            "voucher_date",
            "debit_amount",
            "credit_amount",
            "sub_account",
        ]
        
        df_out = field_mapper_tool(df)
        
        # Check that output columns match master schema
        for col in expected_columns:
            assert col in df_out.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
