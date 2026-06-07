import pandas as pd

from config_loader import get_field_mapping_config


# =====================================================
# MASTER GL SCHEMA
# =====================================================

MASTER_SCHEMA = {

    # =================================================
    # DATE
    # =================================================

    "date": "voucher_date",
    "voucher date": "voucher_date",
    "transaction date": "voucher_date",

    # =================================================
    # VOUCHER
    # =================================================

    "entryno": "voucher_number",
    "entry no": "voucher_number",
    "voucher no": "voucher_number",
    "voucher number": "voucher_number",

    "voucher type": "voucher_type",

    # =================================================
    # DESCRIPTION
    # =================================================

    "details": "particulars",
    "description": "particulars",
    "narration": "narration",

    # =================================================
    # AMOUNT
    # =================================================

    "amount": "amount",
    "debit": "debit_amount",
    "dr": "debit_amount",
    "credit": "credit_amount",
    "cr.": "credit_amount",

    # =================================================
    # ACCOUNT KEYS
    # =================================================

    "account_key": "account_key",
    "territory_key": "territory_key",

    # =================================================
    # ACCOUNT HIERARCHY
    # =================================================

    "account": "account",
    "subaccount": "subaccount",
    "account name": "sub_account",

    "class": "account_class",
    "subclass": "account_subclass",

    # =================================================
    # REGION
    # =================================================

    "country": "country",
    "region": "region",

    # =================================================
    # OPTIONAL
    # =================================================

    "balance": "balance",
    "currency": "currency",
    "branch": "branch",
    "invoice_number": "invoice_number",
    "invoice no": "invoice_number",
    "reference": "reference_number",
    "party_name": "party_name",
    "gst_number": "gst_number",
    "cost_center": "cost_center"
}


# =====================================================
# FIELD MAPPER TOOL
# =====================================================

def field_mapper_tool(df):

    print("\nSTARTING FIELD MAPPING...\n")

    master_schema = get_field_mapping_config() or MASTER_SCHEMA

    new_columns = {}

    for col in df.columns:

        clean_col = (
            str(col)
            .strip()
            .lower()
        )

        if clean_col in master_schema:

            new_columns[col] = master_schema[clean_col]

        else:

            new_columns[col] = (
                clean_col
                .replace(" ", "_")
            )

    df = df.rename(columns=new_columns)

    print("\nFINAL MAPPED COLUMNS:\n")

    print(df.columns.tolist())

    return df
