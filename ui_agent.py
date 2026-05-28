print("ui_agent imported")

import json
import pandas as pd
import httpx
import time


# =========================================================
# FRONTEND CONFIG
# =========================================================

BASE_URL = (
    "https://remarkable-harmony-production-2112.up.railway.app"
)

LOGIN_API_URL = (
    f"{BASE_URL}/api/agent/login"
)

UPLOAD_API_URL = (
    f"{BASE_URL}/api/agent/upload"
)

# =========================================================
# FIXED POLLING URL
# =========================================================

STATUS_API_URL = (
    f"{BASE_URL}/api/uploads"
)

EMAIL = "agentmailak44@gmail.com"

PASSWORD = "AgentPassword4382"


# =========================================================
# INTERNAL COLUMNS
# =========================================================

INTERNAL_COLUMNS = [

    "dr_cr_source"
]


# =========================================================
# TOOL 1 → SAVE JSON
# =========================================================

def save_json_tool(validated_data):

    print("\nSAVING VERIFIED JSON...\n")

    try:

        cleaned_data = validated_data.copy()

        cleaned_rows = []

        for row in cleaned_data.get(
            "data",
            []
        ):

            row = row.copy()

            # =============================================
            # REMOVE INTERNAL FIELDS
            # =============================================

            for col in INTERNAL_COLUMNS:

                row.pop(col, None)

            cleaned_rows.append(row)

        cleaned_data["data"] = cleaned_rows

        formatted_data = json.dumps(
            cleaned_data,
            indent=4
        )

        with open(
            "verified_data.json",
            "w"
        ) as f:

            f.write(formatted_data)

        print(
            "VERIFIED DATA SAVED AS JSON"
        )

    except Exception as e:

        print("\nJSON SAVE FAILED\n")

        print(e)

        raise


# =========================================================
# TOOL 2 → GENERATE EXCEL
# =========================================================

def generate_excel_tool(validated_data):

    print(
        "\nGENERATING GL EXCEL FILE...\n"
    )

    try:

        excel_data = validated_data.get(
            "data",
            []
        )

        # =================================================
        # EMPTY CHECK
        # =================================================

        if not excel_data:

            raise Exception(
                "NO VALIDATED DATA FOUND"
            )

        # =================================================
        # CREATE DATAFRAME
        # =================================================

        df = pd.DataFrame(excel_data)

        # =================================================
        # REMOVE INTERNAL COLUMNS
        # =================================================

        df = df.drop(
            columns=INTERNAL_COLUMNS,
            errors="ignore"
        )

        # =================================================
        # REMOVE COMPLETELY EMPTY COLUMNS
        # =================================================

        df = df.dropna(
            axis=1,
            how="all"
        )

        # =================================================
        # REMOVE BLANK STRING COLUMNS
        # =================================================

        df = df.loc[
            :,
            (
                df.astype(str)
                .apply(
                    lambda col:
                    col.str.strip().ne("").any()
                )
            )
        ]

        # =================================================
        # RENAME COLUMNS FOR UI
        # =================================================

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

            "account_subclass": "sub_class"
        })

        # =================================================
        # STANDARD COLUMN ORDER
        # =================================================

        preferred_columns = [

            "voucher_date",

            "entry_no",

            "Voucher Type",

            "sub_account",

            "details",

            "Narration",

            "debit_amount",

            "credit_amount",

            "Balance",

            "Reference Number",

            "Party Name",

            "GST Number",

            "Cost Center",

            "Branch",

            "Currency",

            "account_code",

            "Invoice Number",

            "country",

            "region",

            "class",

            "sub_class"
        ]

        existing_columns = [

            col

            for col in preferred_columns

            if col in df.columns
        ]

        df = df[existing_columns]

        # =================================================
        # SAVE EXCEL
        # =================================================

        df.to_excel(
            "verified_data.xlsx",
            index=False
        )

        print(
            "GL EXCEL FILE GENERATED SUCCESSFULLY"
        )

    except Exception as e:

        print(
            "\nEXCEL GENERATION FAILED\n"
        )

        print(e)

        raise


# =========================================================
# TOOL 3 → LOGIN TOOL
# =========================================================

def login_tool():

    print("\nLOGGING INTO FRONTEND...\n")

    try:

        login_response = httpx.post(

            LOGIN_API_URL,

            json={

                "email": EMAIL,

                "password": PASSWORD
            },

            timeout=60.0
        )

        print(
            "LOGIN RESPONSE:",
            login_response.status_code
        )

        print(login_response.text)

        # =================================================
        # LOGIN FAILED
        # =================================================

        if login_response.status_code != 200:

            raise Exception(

                f"LOGIN FAILED → "

                f"{login_response.status_code} "

                f"→ {login_response.text}"
            )

        # =================================================
        # GET TOKEN
        # =================================================

        token = login_response.json()[
            "access_token"
        ]

        print("\nLOGIN SUCCESSFUL\n")

        return token

    except httpx.ReadTimeout:

        raise Exception(
            "LOGIN API TIMEOUT → "
            "Frontend server took too long to respond"
        )

    except Exception as e:

        raise Exception(
            f"LOGIN TOOL ERROR → {str(e)}"
        )


# =========================================================
# TOOL 4 → UPLOAD TOOL
# =========================================================

def upload_tool(token):

    print("\nUPLOADING FILE...\n")

    headers = {

        "Authorization": (
            f"Bearer {token}"
        )
    }

    with open(
        "verified_data.xlsx",
        "rb"
    ) as f:

        response = httpx.post(

            UPLOAD_API_URL,

            headers=headers,

            files={

                "file": (
                    "verified_data.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            },

            timeout=120.0
        )

    print(
        "UPLOAD RESPONSE:",
        response.status_code
    )

    print(response.text)

    # =====================================================
    # UPLOAD FAILED
    # =====================================================

    if response.status_code != 200:

        raise Exception(

            f"UPLOAD FAILED → "

            f"{response.status_code} "

            f"→ {response.text}"
        )

    # =====================================================
    # GET RESPONSE JSON
    # =====================================================

    response_json = response.json()
    
    print("FULL UPLOAD RESPONSE JSON:", response_json) 

    # =====================================================
    # FIXED ID FIELD
    # =====================================================

    upload_id = response_json.get(
        "upload_id"
    )

    print(
        f"\nUPLOAD ID: {upload_id}\n"
    )

    # =====================================================
    # POLLING START
    # =====================================================

    print(
        "\nSTARTING POLLING...\n"
    )

    max_attempts = 1

    for attempt in range(max_attempts):

        print(
            f"Polling Attempt "
            f"{attempt + 1}/{max_attempts}"
        )

        poll_response = httpx.get(

            f"{STATUS_API_URL}/{upload_id}",

            headers=headers,

            timeout=30.0
        )

        print(
            "POLL STATUS:",
            poll_response.status_code
        )

        print(
            poll_response.text
        )

        if poll_response.status_code == 200:

            poll_data = poll_response.json()

            status = poll_data.get(
                "status"
            )

            print(
                f"\nCURRENT STATUS: "
                f"{status}\n"
            )

            # =================================================
            # FIXED STATUS CHECK
            # =================================================

            if status in [

                "pending",

                "approved",

                "rejected",

                "reupload_requested"
            ]:

                print(
                    "\nFILE PROCESSING COMPLETED\n"
                )

                return

            # =================================================
            # PARSE FAILED
            # =================================================

            if status == "parse_failed":

                raise Exception(
                    f"PARSE FAILED → "
                    f"{poll_response.text}"
                )

        # =================================================
        # WAIT BEFORE NEXT POLL
        # =================================================

        time.sleep(5)

    # =====================================================
    # POLLING FAILED
    # =====================================================

    raise Exception(

        "Polling timeout → "
        "Frontend processing "
        "not completed"
    )


# =========================================================
# MAIN UI AGENT
# =========================================================

def push_to_ui(validated_data):

    print(
        "\nPUSHING VERIFIED GL DATA TO UI...\n"
    )

    try:

        # =================================================
        # VALIDATION STATUS CHECK
        # =================================================

        validation_status = validated_data.get(
            "status"
        )

        print(
            f"\nVALIDATION STATUS: "
            f"{validation_status}\n"
        )

        # =================================================
        # ALLOW PUSH EVEN IF WARNINGS EXIST
        # =================================================

        if validation_status not in [
            "valid",
            "invalid"
        ]:

            raise Exception(
                "UNKNOWN VALIDATION STATUS"
            )

        print(
            "\nCONTINUING DATA PUSH "
            "TO FRONTEND...\n"
        )

        # =================================================
        # STEP 1 → SAVE JSON
        # =================================================

        save_json_tool(validated_data)

        # =================================================
        # STEP 2 → GENERATE EXCEL
        # =================================================

        generate_excel_tool(validated_data)

        # =================================================
        # STEP 3 → LOGIN
        # =================================================

        token = login_tool()

        # =================================================
        # STEP 4 → UPLOAD FILE
        # =================================================

        upload_tool(token)

        print(
            "\nDATA PUSHED SUCCESSFULLY\n"
        )

        return {

            "status": "success",

            "message": (
                "GL data pushed successfully"
            )
        }

    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as e:

        print("\nUI AGENT ERROR:\n")

        print(e)

        return {

            "status": "failed",

            "error": str(e)
        }