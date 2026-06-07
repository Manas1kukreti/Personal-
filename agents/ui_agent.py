print("ui_agent imported")

import json
import pandas as pd
import httpx
import time

from dotenv import load_dotenv

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
    return validate_api_base_url(require_env("LEDGERFLOW_FRONTEND_BASE_URL"))

def _login_url() -> str:
    return f"{_get_base_url()}/api/agent/login"

def _upload_url() -> str:
    return f"{_get_base_url()}/api/agent/upload"

def _status_url() -> str:
    return f"{_get_base_url()}/api/uploads"


EMAIL_ENV = "LEDGERFLOW_AGENT_EMAIL"
PASSWORD_ENV = "LEDGERFLOW_AGENT_PASSWORD"


# =========================================================
# INTERNAL COLUMNS
# =========================================================

INTERNAL_COLUMNS = ["dr_cr_source"]


# =========================================================
# TOOL 1 → SAVE JSON
# =========================================================

def save_json_tool(validated_data):

    print("\nSAVING VERIFIED JSON...\n")

    try:
        cleaned_data = validated_data.copy()
        cleaned_rows = []

        for row in cleaned_data.get("data", []):
            row = row.copy()
            for col in INTERNAL_COLUMNS:
                row.pop(col, None)
            cleaned_rows.append(row)

        cleaned_data["data"] = cleaned_rows

        with open(PROJECT_ROOT / "verified_data.json", "w") as f:
            json.dump(cleaned_data, f, indent=4)

        print("VERIFIED DATA SAVED AS JSON")

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
        excel_data = validated_data.get("data", [])

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
        })

        preferred_columns = [
            "voucher_date", "entry_no", "Voucher Type", "sub_account",
            "details", "Narration", "debit_amount", "credit_amount",
            "Balance", "Reference Number", "Party Name", "GST Number",
            "Cost Center", "Branch", "Currency", "account_code",
            "Invoice Number", "country", "region", "class", "sub_class",
            "Repairs Applied",
        ]

        existing_columns = [col for col in preferred_columns if col in df.columns]
        df = df[existing_columns]
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
        email = require_env(EMAIL_ENV)
        password = require_env(PASSWORD_ENV)

        login_response = httpx.post(
            _login_url(),
            json={"email": email, "password": password},
            timeout=60.0,
        )

        print("LOGIN RESPONSE:", login_response.status_code)
        print(login_response.text)

        if login_response.status_code != 200:
            raise Exception(
                f"LOGIN FAILED → {login_response.status_code} → {login_response.text}"
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
    print(response.text)

    if response.status_code != 200:
        raise Exception(
            f"UPLOAD FAILED → {response.status_code} → {response.text}"
        )

    response_json = response.json()
    print("FULL UPLOAD RESPONSE JSON:", response_json)

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
        print(poll_response.text)

        if poll_response.status_code == 200:
            poll_data = poll_response.json()
            status = poll_data.get("status")
            print(f"\nCURRENT STATUS: {status}\n")

            if status in ["pending", "approved", "rejected", "reupload_requested"]:
                print("\nFILE PROCESSING COMPLETED\n")
                return

            if status == "parse_failed":
                raise Exception(f"PARSE FAILED → {poll_response.text}")

        time.sleep(5)

    raise Exception("Polling timeout → Frontend processing not completed")


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
        token = login_tool()
        upload_tool(token)

        print("\nDATA PUSHED SUCCESSFULLY\n")
        return {"status": "success", "message": "GL data pushed successfully"}

    except Exception as e:
        print("\nUI AGENT ERROR:\n")
        print(e)
        return {"status": "failed", "error": str(e)}