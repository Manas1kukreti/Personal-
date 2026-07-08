import imaplib
import email
import os
import json

from dotenv import load_dotenv
from pathlib import Path

import PyPDF2
import pandas as pd

from config_loader import get_workflow_config
from ledgerflow_agent.env import get_imap_settings, get_mail_credentials
from ledgerflow_agent.guardrails import GuardrailViolation, validate_attachment_path
from tools.excel_reader_tool import read_excel_tool
from tools.limit_tool import limit_rows_tool
from tools.field_mapper_tool import field_mapper_tool
from tools.text_cleaner_tool import clean_dataframe_tool
from tools.relation_mapper_tool import relation_mapper_tool
from tools.financial_logic_tool import financial_logic_tool

# LOAD ENV VARIABLES
# =====================================================

env_path = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(dotenv_path=env_path)


# =====================================================
# EMAIL CREDENTIALS
# =====================================================

EMAIL_USER, EMAIL_PASS = get_mail_credentials()
IMAP_HOST, IMAP_PORT = get_imap_settings()

print("MAIL USER CONFIGURED:", bool(EMAIL_USER))
print("MAIL PASS CONFIGURED:", bool(EMAIL_PASS))


# =====================================================
# ATTACHMENT FOLDER
# =====================================================

ATTACHMENT_FOLDER = "attachments"

os.makedirs(
    ATTACHMENT_FOLDER,
    exist_ok=True
)


# =====================================================
# CONNECT TO EMAIL
# =====================================================

def connect_email():

    print("\nCONNECTING TO GMAIL...\n")

    mail = imaplib.IMAP4_SSL(
        IMAP_HOST,
        IMAP_PORT
    )

    mail.login(
        EMAIL_USER,
        EMAIL_PASS
    )

    print("CONNECTED SUCCESSFULLY")

    return mail


# =====================================================
# FETCH LATEST EMAIL
# =====================================================

def fetch_latest_email(mail):

    mail.select("inbox")

    status, messages = mail.search(
        None,
        "ALL"
    )

    print(
        "EMAIL SEARCH STATUS:",
        status
    )

    email_ids = messages[0].split()

    print(
        "TOTAL EMAILS FOUND:",
        len(email_ids)
    )

    if not email_ids:

        print("\nNO EMAILS FOUND\n")

        return ""

    latest_email_id = email_ids[-1]

    print(
        "LATEST EMAIL ID:",
        latest_email_id
    )

    res, msg_data = mail.fetch(
        latest_email_id,
        "(RFC822)"
    )

    for response in msg_data:

        if isinstance(response, tuple):

            msg = email.message_from_bytes(
                response[1]
            )

            return process_email(msg)

    return ""


# =====================================================
# PROCESS EMAIL
# =====================================================

def process_email(msg):

    full_text = ""

    for part in msg.walk():

        content_type = part.get_content_type()

        filename = part.get_filename()

        print(
            "\nFOUND PART:",
            content_type,
            "| FILE:",
            filename
        )

        # =================================================
        # EMAIL BODY
        # =================================================

        if "text" in content_type and filename is None:

            try:

                body = part.get_payload(
                    decode=True
                )

                if body:

                    body = body.decode(
                        errors="ignore"
                    )

                    full_text += (
                        "\n" + clean_text(body)
                    )

            except Exception as e:

                print(
                    "\nERROR READING EMAIL BODY\n"
                )

                print(e)

        # =================================================
        # ATTACHMENTS
        # =================================================

        elif filename:

            filepath = os.path.join(
                ATTACHMENT_FOLDER,
                filename
            )

            try:

                with open(filepath, "wb") as f:

                    f.write(
                        part.get_payload(
                            decode=True
                        )
                    )

                print(
                    f"\nATTACHMENT SAVED: {filepath}\n"
                )

                extracted_text = (
                    extract_attachment_text(
                        filepath
                    )
                )

                full_text += (
                    "\n" + extracted_text
                )

            except Exception as e:

                print(
                    "\nERROR PROCESSING ATTACHMENT\n"
                )

                print(e)

    return full_text.strip()


# =====================================================
# ATTACHMENT ROUTER
# =====================================================

def extract_attachment_text(filepath):
    try:

        safe_path = validate_attachment_path(filepath)

    except GuardrailViolation as exc:

        print("\nATTACHMENT REJECTED BY GUARDRAILS\n")

        print(exc)

        return ""

    # =================================================
    # PDF
    # =================================================

    if safe_path.suffix.lower() == ".pdf":

        return extract_pdf(str(safe_path))

    # =================================================
    # EXCEL
    # =================================================

    elif safe_path.suffix.lower() in (".xlsx", ".xls"):

        return extract_excel(str(safe_path))

    # =================================================
    # UNSUPPORTED
    # =================================================

    else:

        print(
            "\nUNSUPPORTED FILE TYPE\n"
        )

        return ""


# =====================================================
# PDF EXTRACTION
# =====================================================

def extract_pdf(filepath):

    print("\nREADING PDF...\n")

    text = ""

    try:

        with open(filepath, "rb") as f:

            reader = PyPDF2.PdfReader(f)

            for page in reader.pages:

                text += (
                    page.extract_text()
                    or ""
                )

    except Exception as e:

        print("\nPDF READ ERROR\n")

        print(e)

    return clean_text(text)



# =====================================================
# EXCEL EXTRACTION PIPELINE
# =====================================================

def extract_excel(filepath):

    print(
        "\nSTARTING EXCEL PREPROCESSING PIPELINE...\n"
    )

    try:

        # =================================================
        # STEP 1 → READ EXCEL
        # =================================================

        df = read_excel_tool(filepath)

        if df is None:

            return ""

        # =================================================
        # STEP 2 → LIMIT ROWS
        # =================================================

        workflow_config = get_workflow_config()

        df = limit_rows_tool(
            df,
            limit=workflow_config.get(
                "excel_row_limit",
                14
            )
        )

        if df is None:

            return ""

        # =================================================
        # STEP 3 → FIELD MAPPING
        # =================================================

        df = field_mapper_tool(df)

        # =================================================
        # STEP 4 → CLEAN DATA
        # =================================================

        df = clean_dataframe_tool(df)

        # =================================================
        # STEP 5 → RELATIONAL MAPPING
        # =================================================

        df = relation_mapper_tool(
            df,
            filepath
        )

        # =================================================
        # STEP 6 → FINANCIAL LOGIC
        # =================================================

        df = financial_logic_tool(df)

        # =================================================
        # STEP 7 → CONVERT TO JSON
        # =================================================

        # Prevent NaN floats from breaking standard JSON and Pydantic string validation
        df = df.fillna("")

        structured_json = df.to_dict(
            orient="records"
        )

        print(
            "\nEXCEL PREPROCESSING COMPLETED\n"
        )

        print(
            "\nFINAL DATAFRAME COLUMNS:\n"
        )

        print(df.columns.tolist())

        return json.dumps(

            structured_json,

            indent=2,

            default=str
        )

    except Exception as e:

        print(
            "\nEXCEL PROCESSING ERROR\n"
        )

        print(e)

        return ""


def clean_text(text):


    text = text.strip()

    text = " ".join(text.split())

    return text


# =====================================================
# MAIN FUNCTION
# =====================================================

def get_email_text():

    print(
        "\nSTARTING EMAIL EXTRACTION PIPELINE...\n"
    )

    mail = connect_email()

    data = fetch_latest_email(mail)

    print(
        "\nFINAL EXTRACTED DATA PREVIEW:\n"
    )

    print(data[:3000])

    return data
