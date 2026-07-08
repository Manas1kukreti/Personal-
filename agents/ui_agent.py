print("ui_agent imported")

import json
import pandas as pd
import httpx
import time
import os
import psycopg2

from dotenv import load_dotenv

from ledgerflow_agent.env import get_frontend_base_url, get_frontend_credentials
from ledgerflow_agent.guardrails import require_env, validate_api_base_url
from pathlib import Path

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# =========================================================
# FRONTEND CONFIG — resolved lazily to avoid import-time crashes
# =========================================================
# Evaluating validate_api_base_url() at module level causes the entire
# import to fail with "No module named ..." if the env var is unset or
# the host is not yet whitelisted. Resolve inside helpers instead.

def _get_base_url() -> str:
    return validate_api_base_url(get_frontend_base_url())

def _login_url() -> str:
    return f"{_get_base_url()}/api/agent/login"

def _upload_url() -> str:
    return f"{_get_base_url()}/api/agent/upload"

def _status_url() -> str:
    return f"{_get_base_url()}/api/uploads"


EMAIL_ENV = "LEDGERFLOW_FRONTEND_EMAIL"
PASSWORD_ENV = "LEDGERFLOW_FRONTEND_PASSWORD"


# =========================================================
# INTERNAL COLUMNS
# =========================================================

INTERNAL_COLUMNS = ["dr_cr_source"]


def _voucher_key(value) -> str:
    text = "" if value is None else str(value).strip()
    return text.split(".", 1)[0]


def _annotate_review_data(validated_data):
    """Attach balance-review details to each row so the frontend can display them."""
    payload = validated_data.copy()
    rows = [row.copy() for row in payload.get("data", [])]
    errors = payload.get("errors", []) or []
    warnings = payload.get("warnings", []) or []

    balance_by_voucher: dict[str, dict[str, object]] = {}
    for error in errors:
        difference = error.get("difference")
        if difference is None:
            continue
        voucher = _voucher_key(error.get("Entry no") or error.get("entry_no") or error.get("transaction_index"))
        if voucher not in balance_by_voucher:
            balance_by_voucher[voucher] = {
                "status": "review_required",
                "difference": difference,
                "messages": [],
            }
        balance_by_voucher[voucher]["messages"].append(str(error.get("error", "Validation error")))

    warning_by_voucher: dict[str, list[str]] = {}
    for warning in warnings:
        voucher = _voucher_key(warning.get("Entry no") or warning.get("entry_no") or warning.get("transaction_index"))
        warning_by_voucher.setdefault(voucher, []).append(str(warning.get("warning", "Warning")))

    for row in rows:
        row_voucher = _voucher_key(row.get("entry_no"))
        review = balance_by_voucher.get(row_voucher)
        if review:
            row["review_status"] = review["status"]
            row["dtcd_difference"] = review["difference"]
            row["validation_messages"] = "; ".join(review["messages"])
        if row_voucher in warning_by_voucher:
            row["validation_warnings"] = "; ".join(warning_by_voucher[row_voucher])

    payload["data"] = rows
    return payload


# =========================================================
# TOOL 1 → SAVE JSON
# =========================================================

def save_json_tool(validated_data):

    print("\nSAVING VERIFIED JSON...\n")

    try:
        cleaned_data = _annotate_review_data(validated_data)
        cleaned_rows = []

        for row in cleaned_data.get("data", []):
            row = row.copy()
            for col in INTERNAL_COLUMNS:
                row.pop(col, None)
            cleaned_rows.append(row)

        cleaned_data["data"] = cleaned_rows

        output_json = os.getenv("OUTPUT_JSON_FILE")
        if output_json:
            with open(output_json, "w") as f:
                json.dump(cleaned_data, f, indent=4)
        else:
            with open(PROJECT_ROOT / "verified_data.json", "w") as f:
                json.dump(cleaned_data, f, indent=4)

        print("VERIFIED DATA SAVED AS JSON")
        
        # Save to PostgreSQL
        save_to_postgres(validated_data)

    except Exception as e:
        print("\nJSON SAVE FAILED\n")
        print(e)
        raise


# =========================================================
# TOOL 2 → GENERATE EXCEL
# =========================================================

def generate_excel_tool(validated_data):

    print("\nGENERATING GL EXCEL FILE...\n")

    try:
        review_ready = _annotate_review_data(validated_data)
        excel_data = review_ready.get("data", [])

        if not excel_data:
            raise Exception("NO VALIDATED DATA FOUND")

        df = pd.DataFrame(excel_data)
        df = df.drop(columns=INTERNAL_COLUMNS, errors="ignore")
        df = df.dropna(axis=1, how="all")
        df = df.loc[:, (df.astype(str).apply(lambda col: col.str.strip().ne("").any()))]

        df = df.rename(columns={
            "voucher_date": "voucher_date",
            "entry_no": "entry_no",
            "voucher_type": "Voucher Type",
            "sub_account": "sub_account",
            "details": "details",
            "narration": "Narration",
            "debit_amount": "debit_amount",
            "credit_amount": "credit_amount",
            "balance": "Balance",
            "reference_number": "Reference Number",
            "party_name": "Party Name",
            "gst_number": "GST Number",
            "cost_center": "Cost Center",
            "branch": "Branch",
            "currency": "Currency",
            "account_code": "account_code",
            "invoice_number": "Invoice Number",
            "country": "country",
            "region": "region",
            "class_name": "class",
            "account_subclass": "sub_class",
            "review_status": "Review Status",
            "dtcd_difference": "DTCD Difference",
            "validation_messages": "Validation Messages",
            "validation_warnings": "Validation Warnings",
        })

        preferred_columns = [
            "voucher_date", "entry_no", "Voucher Type", "sub_account",
            "details", "Narration", "debit_amount", "credit_amount",
            "Balance", "Reference Number", "Party Name", "GST Number",
            "Cost Center", "Branch", "Currency", "account_code",
            "Invoice Number", "country", "region", "class", "sub_class",
            "Review Status", "DTCD Difference", "Validation Messages",
            "Validation Warnings", "Repairs Applied",
        ]

        existing_columns = [col for col in preferred_columns if col in df.columns]
        df = df[existing_columns]
        output_excel = os.getenv("OUTPUT_EXCEL_FILE")
        if output_excel:
            df.to_excel(output_excel, index=False)
        else:
            df.to_excel(PROJECT_ROOT / "verified_data.xlsx", index=False)

        print("GL EXCEL FILE GENERATED SUCCESSFULLY")

    except Exception as e:
        print("\nEXCEL GENERATION FAILED\n")
        print(e)
        raise


# =========================================================
# TOOL 3 → LOGIN TOOL
# =========================================================

def login_tool():

    print("\nLOGGING INTO FRONTEND...\n")

    try:
        email, password = get_frontend_credentials()

        login_response = httpx.post(
            _login_url(),
            json={"email": email, "password": password},
            timeout=60.0,
        )

        print("LOGIN RESPONSE:", login_response.status_code)

        if login_response.status_code != 200:
            raise Exception(
                f"LOGIN FAILED → {login_response.status_code} → response body omitted"
            )

        token = login_response.json()["access_token"]
        print("\nLOGIN SUCCESSFUL\n")
        return token

    except httpx.ReadTimeout:
        raise Exception("LOGIN API TIMEOUT → Frontend server took too long to respond")
    except Exception as e:
        raise Exception(f"LOGIN TOOL ERROR → {str(e)}")


# =========================================================
# TOOL 4 → UPLOAD TOOL
# =========================================================

def upload_tool(token):

    print("\nUPLOADING FILE...\n")

    headers = {"Authorization": f"Bearer {token}"}

    with open(PROJECT_ROOT / "verified_data.xlsx", "rb") as f:
        response = httpx.post(
            _upload_url(),
            headers=headers,
            files={
                "file": (
                    "verified_data.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            timeout=120.0,
        )

    print("UPLOAD RESPONSE:", response.status_code)

    if response.status_code != 200:
        raise Exception(
            f"UPLOAD FAILED → {response.status_code} → response body omitted"
        )

    response_json = response.json()
    print("UPLOAD RESPONSE JSON KEYS:", sorted(response_json.keys()))

    upload_id = response_json.get("upload_id")
    print(f"\nUPLOAD ID: {upload_id}\n")

    print("\nSTARTING POLLING...\n")

    max_attempts = 1
    for attempt in range(max_attempts):
        print(f"Polling Attempt {attempt + 1}/{max_attempts}")

        poll_response = httpx.get(
            f"{_status_url()}/{upload_id}",
            headers=headers,
            timeout=30.0,
        )

        print("POLL STATUS:", poll_response.status_code)

        if poll_response.status_code == 200:
            poll_data = poll_response.json()
            status = poll_data.get("status")
            print(f"\nCURRENT STATUS: {status}\n")

            if status in ["pending", "approved", "rejected", "reupload_requested"]:
                print("\nFILE PROCESSING COMPLETED\n")
                return

            if status == "parse_failed":
                raise Exception("PARSE FAILED → response body omitted")

        time.sleep(5)

    raise Exception("Polling timeout → Frontend processing not completed")


# =========================================================
# POSTGRESQL INTEGRATION
# =========================================================

def save_to_postgres(validated_data):
    """
    Saves validated general ledger data to PostgreSQL.
    If the connection fails or DATABASE_URL is not set, prints a warning instead of crashing.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("\n[WARNING] DATABASE_URL is not set in environment. Skipping database save.\n")
        return

    print(f"\n[INFO] Saving data to PostgreSQL database...")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS ledger_transactions (
            id SERIAL PRIMARY KEY,
            voucher_date VARCHAR(100),
            entry_no VARCHAR(100),
            sub_account VARCHAR(255),
            details TEXT,
            debit_amount NUMERIC(15, 2),
            credit_amount NUMERIC(15, 2),
            account_code VARCHAR(100),
            country VARCHAR(100),
            region VARCHAR(100),
            class_name VARCHAR(100),
            account_subclass VARCHAR(100),
            review_status VARCHAR(100),
            dtcd_difference NUMERIC(15, 2),
            validation_messages TEXT,
            validation_warnings TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_table_query)
        
        # Annotate the data
        annotated_payload = _annotate_review_data(validated_data)
        rows = annotated_payload.get("data", [])
        
        if not rows:
            print("[INFO] No transactions found to save in database.")
            cur.close()
            conn.close()
            return
            
        # Helper to convert to float safely
        from agents.validator import safe_float
        
        insert_query = """
        INSERT INTO ledger_transactions (
            voucher_date, entry_no, sub_account, details, debit_amount, credit_amount,
            account_code, country, region, class_name, account_subclass,
            review_status, dtcd_difference, validation_messages, validation_warnings
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        
        # Insert rows
        for row in rows:
            debit = safe_float(row.get("debit_amount"))
            credit = safe_float(row.get("credit_amount"))
            diff = row.get("dtcd_difference")
            if diff is not None:
                diff = safe_float(diff)
                
            cur.execute(insert_query, (
                row.get("voucher_date", ""),
                row.get("entry_no", ""),
                row.get("sub_account", ""),
                row.get("details", ""),
                debit,
                credit,
                row.get("account_code", ""),
                row.get("country", ""),
                row.get("region", ""),
                row.get("class_name", ""),
                row.get("account_subclass", ""),
                row.get("review_status", ""),
                diff,
                row.get("validation_messages", ""),
                row.get("validation_warnings", "")
            ))
            
        print(f"[INFO] Successfully saved {len(rows)} transactions to PostgreSQL.")
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n[WARNING] Failed to save to PostgreSQL database: {e}\n")


# =========================================================
# MAIN UI AGENT
# =========================================================

def push_to_ui(validated_data):

    print("\nPUSHING VERIFIED GL DATA TO UI...\n")

    try:
        validation_status = validated_data.get("status")
        print(f"\nVALIDATION STATUS: {validation_status}\n")

        if validation_status not in ["valid", "invalid"]:
            raise Exception("UNKNOWN VALIDATION STATUS")

        print("\nCONTINUING DATA PUSH TO FRONTEND...\n")

        save_json_tool(validated_data)
        generate_excel_tool(validated_data)
        
        # Save to PostgreSQL
        save_to_postgres(validated_data)
        
        if os.getenv("SKIP_HTTP_UPLOAD") != "true":
            token = login_tool()
            upload_tool(token)
            print("\nDATA PUSHED SUCCESSFULLY\n")
            return {"status": "success", "message": "GL data pushed successfully"}
        else:
            print("\nDATA GENERATED SUCCESSFULLY (SKIPPED HTTP UPLOAD)\n")
            return {"status": "success", "message": "GL data processed successfully"}

    except Exception as e:
        print("\nUI AGENT ERROR:\n")
        print(e)
        return {"status": "failed", "error": str(e)}
