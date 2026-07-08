import json
import re

from collections import defaultdict

from pydantic import BaseModel
from pydantic import ValidationError

from jsonschema import validate

from rapidfuzz import fuzz


# =========================================================
# PYDANTIC MODEL
# =========================================================

class GLTransaction(BaseModel):

    voucher_date: str = ""

    entry_no: str = ""

    sub_account: str = ""

    details: str = ""

    debit_amount: str = ""

    credit_amount: str = ""

    account_code: str = ""

    country: str = ""

    region: str = ""

    class_name: str = ""

    account_subclass: str = ""


def _invalid_result(message: str, *, transaction_index: int | None = None) -> dict:
    error: dict[str, object] = {"error": message}
    if transaction_index is not None:
        error["transaction_index"] = transaction_index
    return {
        "status": "invalid",
        "errors": [error],
        "warnings": [],
    }


# =========================================================
# JSON SCHEMA
# =========================================================

transaction_schema = {

    "type": "array",

    "items": {

        "type": "object",

        "required": [

            "voucher_date"
        ]
    }
}


# =========================================================
# SAFE FLOAT CONVERTER
# =========================================================

def safe_float(value):

    if value in ["", None]:

        return 0.0

    try:

        value = str(value).strip()

        value = value.replace(",", "")

        if value.startswith("(") and value.endswith(")"):

            value = "-" + value[1:-1]

        return float(value)

    except:

        return 0.0


# =========================================================
# VALIDATOR FUNCTION
# =========================================================

def validate_data(

    email_text,

    data

):

    print("\nVALIDATING GL DATA...\n")

    try:

        # =================================================
        # CLEAN RAW LLM OUTPUT
        # =================================================

        cleaned_data = (

            data.replace(
                "```json",
                ""
            )

            .replace(
                "```",
                ""
            )

            .strip()
        )

        # =================================================
        # STRING TO JSON
        # =================================================

        parsed = json.loads(
            cleaned_data
        )

        # =================================================
        # ENSURE LIST
        # =================================================

        # If a single JSON object is returned, wrap it in a list for downstream processing
        if isinstance(parsed, dict):
            parsed = [parsed]
        elif not isinstance(parsed, list):
            return _invalid_result("Expected JSON array")

        # =================================================
        # EMPTY CHECK
        # =================================================

        if len(parsed) == 0:

            return _invalid_result("NO FINANCIAL DATA EXTRACTED")

        # =================================================
        # STORAGE
        # =================================================

        validated_transactions = []

        validation_errors = []

        validation_warnings = []

        voucher_groups = defaultdict(list)

        # =================================================
        # VALIDATE EACH TRANSACTION
        # =================================================

        for idx, transaction in enumerate(parsed):

            # =================================================
            # RENAME FIELDS
            # =================================================

            transformed_transaction = {

    "voucher_date":
    transaction.get(
        "voucher_date",
        ""
    ),

    "entry_no":
    transaction.get(
        "voucher_number",
        ""
    ),

    "sub_account":
    transaction.get(
        "subaccount",
        ""
    ),

    "details":
    transaction.get(
        "particulars",
        ""
    ),

    "debit_amount":
    transaction.get(
        "debit_amount",
        ""
    ),

    "credit_amount":
    transaction.get(
        "credit_amount",
        ""
    ),

    "account_code":
    transaction.get(
        "account_key",
        ""
    ),

    "country":
    transaction.get(
        "country",
        ""
    ),

    "region":
    transaction.get(
        "region",
        ""
    ),

    "class_name":
    transaction.get(
        "account_class",
        ""
    ),

    "account_subclass":
    transaction.get(
        "account_subclass",
        ""
    )
}

            # =================================================
            # COERCE TO STRING
            # =================================================

            for key in transformed_transaction:
                val = transformed_transaction[key]
                if val not in [None, ""]:
                    # Convert float integers (e.g. 214.0) to "214", but preserve 2001.1
                    if isinstance(val, float) and val.is_integer():
                        transformed_transaction[key] = str(int(val))
                    else:
                        transformed_transaction[key] = str(val)

            # =================================================
            # PYDANTIC VALIDATION
            # =================================================

            try:

                validated = GLTransaction(
                    **transformed_transaction
                )

                cleaned_transaction = (
                    validated.dict()
                )

            except ValidationError as ve:

                validation_errors.append({

                    "error":
                    "Pydantic validation failed",

                    "validation_error":
                    ve.errors(),

                    "transaction_index":
                    idx
                })

                continue

            # =================================================
            # CLEAN STRINGS
            # =================================================

            for key, value in cleaned_transaction.items():

                if isinstance(value, str):

                    cleaned_transaction[key] = (
                        value.strip()
                    )

            # =================================================
            # REQUIRED FIELD CHECK
            # =================================================

            voucher_date = cleaned_transaction.get(
                "voucher_date",
                ""
            )

            if voucher_date == "":

                validation_errors.append({

                    "error":
                    "voucher_date is empty",

                    "failed_field":
                    "voucher_date",

                    "transaction_index":
                    idx
                })

            # =================================================
            # DEBIT/CREDIT CHECK
            # =================================================

            debit = cleaned_transaction.get(
                "debit_amount",
                ""
            )

            credit = cleaned_transaction.get(
                "credit_amount",
                ""
            )

            if debit in ["", None] and credit in ["", None]:

                validation_errors.append({

                    "error":
                    "Both debit and credit empty",

                    "failed_field":
                    "debit_credit",

                    "transaction_index":
                    idx
                })

            if debit not in ["", None] and credit not in ["", None]:

                validation_errors.append({

                    "error":
                    "Both debit and credit filled",

                    "failed_field":
                    "debit_credit",

                    "transaction_index":
                    idx
                })

            # =================================================
            # FUZZY VALIDATION
            # =================================================

            details = cleaned_transaction.get(
                "details",
                ""
            )

            if details:

                score = fuzz.partial_ratio(

                    details.lower(),

                    email_text.lower()
                )

                if score < 50:

                    validation_warnings.append({

                        "warning":
                        "Details mismatch",

                        "details":
                        details,

                        "score":
                        score
                    })

            # =================================================
            # GROUP VOUCHERS
            # =================================================

            entry_no = cleaned_transaction.get(
                "entry_no",
                ""
            )

            base_voucher = str(
                entry_no
            ).split(".")[0]

            voucher_groups[
                base_voucher
            ].append(
                cleaned_transaction
            )

            validated_transactions.append(
                cleaned_transaction
            )

        # =================================================
        # DTCD VALIDATION
        # =================================================

        print(
            "\nCHECKING VOUCHER BALANCING...\n"
        )

        for voucher_id, transactions in voucher_groups.items():

            total_debit = 0.0

            total_credit = 0.0

            for tx in transactions:

                total_debit += safe_float(

                    tx.get(
                        "debit_amount",
                        ""
                    )
                )

                total_credit += safe_float(

                    tx.get(
                        "credit_amount",
                        ""
                    )
                )

            total_debit = round(
                total_debit,
                2
            )

            total_credit = round(
                total_credit,
                2
            )

            difference = round(

                abs(
                    total_debit -
                    total_credit
                ),

                2
            )

            print(

                f"Voucher {voucher_id} "

                f"-> Debit: {total_debit} "

                f"| Credit: {total_credit} "

                f"| Difference: {difference}"
            )

            if difference > 0.01:

                validation_warnings.append({

                    "warning":
                    f"Voucher {voucher_id} not balanced",

                    "difference":
                    difference
                })

                sample_tx = transactions[0]

                validation_errors.append({

                    "error":
                    f"Voucher {voucher_id} not balanced",

                    "failed_field":
                    "dtcd_difference",

                    "Entry no":
                    voucher_id,

                    "Account code":
                    sample_tx.get(
                        "account_code",
                        ""
                    ),

                    "Sub Account":
                    sample_tx.get(
                        "sub_account",
                        ""
                    ),

                    "difference":
                    difference
                })

        # =================================================
        # FINAL RESULT
        # =================================================

        if validation_errors:

            print("\nVALIDATION FAILED\n")

            return {

                "status": "invalid",

                "errors": validation_errors,

                "warnings": validation_warnings,

                "validated_count": len(
                    validated_transactions
                ),

                "data": validated_transactions
            }

        print("\nVALIDATION SUCCESSFUL\n")

        return {

            "status": "valid",

            "warnings": validation_warnings,

            "validated_count": len(
                validated_transactions
            ),

            "data": validated_transactions
        }

    except Exception as e:

        return _invalid_result(str(e))
