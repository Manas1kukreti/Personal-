print("notification_agent imported")

import smtplib
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from email.mime.text import MIMEText

from ledgerflow_agent.env import require_env_alias
from ledgerflow_agent.guardrails import GuardrailViolation, require_env, safe_error_message
from ledgerflow_agent.llm import get_groq_client
from ledgerflow_agent.prompts import get_agent_prompt

load_dotenv(
    dotenv_path=Path(__file__).resolve().parent.parent / ".env"
)

# =========================================================
# IMPORT UI ALERT TOOL
# =========================================================

from agents.ui_agent import login_tool
from tools.pushing_validation_alert_tool import push_validation_alert_tool


# =========================================================
# MANAGER EMAIL
# =========================================================

MANAGER_EMAIL_ENV = "LEDGERFLOW_MANAGER_EMAIL"
SENDER_EMAIL_ENV = "LEDGERFLOW_SENDER_EMAIL"
SENDER_PASSWORD_ENV = "LEDGERFLOW_SENDER_EMAIL_APP_PASSWORD"
SMTP_HOST_ENV = "LEDGERFLOW_SMTP_HOST"
SMTP_PORT_ENV = "LEDGERFLOW_SMTP_PORT"


# =========================================================
# SEND FAILURE NOTIFICATION
# =========================================================

def send_failure_notification(validation_result):

    print(
        "\nSENDING FAILURE NOTIFICATION...\n"
    )

    try:

        # =====================================================
        # FORMAT ERRORS
        # =====================================================

        formatted_errors = ""

        errors = validation_result.get(
            "errors",
            []
        )

        # =====================================================
        # NO ERRORS
        # =====================================================

        if not errors:

            formatted_errors = (
                "Validation failed but "
                "specific error details "
                "were not available."
            )

        else:

            for error in errors:

                # =================================================
                # SKIP PYDANTIC ERRORS
                # =================================================

                if (
                    "Pydantic"
                    in error.get(
                        "error",
                        ""
                    )
                ):

                    continue

                # =================================================
                # COMMON FIELDS
                # =================================================

                row_number = (
                    error.get(
                        "transaction_index",
                        0
                    ) + 1
                )

                failed_field = error.get(
                    "failed_field",
                    "Unknown Field"
                )

                current_value = error.get(
                    "current_value",
                    "EMPTY"
                )

                # =================================================
                # CLEAN EMPTY VALUES
                # =================================================

                if current_value in [
                    "",
                    None
                ]:

                    current_value = "EMPTY"

                # =================================================
                # FRIENDLY ERROR MESSAGES
                # =================================================

                if failed_field == "amount":

                    readable_error = (
                        f"â€¢ Row {row_number}: "
                        f"Amount field is empty."
                    )

                elif failed_field == "customer_name":

                    readable_error = (
                        f"â€¢ Row {row_number}: "
                        f"Customer name is missing "
                        f"or invalid."
                    )

                elif failed_field == "merchant_name":

                    readable_error = (
                        f"â€¢ Row {row_number}: "
                        f"Merchant name is invalid."
                    )

                elif failed_field == "transaction_id":

                    readable_error = (
                        f"â€¢ Row {row_number}: "
                        f"Transaction ID format "
                        f"is invalid."
                    )

                # =================================================
                # DTCD VALIDATION FAILURE
                # =================================================

                elif failed_field == "dtcd_difference":

                    entry_no = error.get(
                        "Entry no",
                        "UNKNOWN"
                    )

                    account_code = error.get(
                        "Account code",
                        "UNKNOWN"
                    )

                    sub_account = error.get(
                        "Sub Account",
                        "UNKNOWN"
                    )

                    difference = error.get(
                        "difference",
                        "UNKNOWN"
                    )

                    
                    # =============================================
                    # LOGIN TO UI
                    # =============================================

                    token = login_tool()

                    # =============================================
                    # CREATE ALERT PAYLOAD
                    # =============================================

                    alert_payload = {
                        "Entry no": entry_no,
                        "Account code": account_code,
                        "Sub Account": sub_account,
                        "difference": difference,
                        "status": "FAILED"
                    }

                    # =============================================
                    # PUSH ALERT TO UI
                    # =============================================

                    push_validation_alert_tool(
                        token,
                        alert_payload
                    )

                    # =============================================
                    # HUMAN READABLE MESSAGE
                    # =============================================

                    readable_error = (
                        f"â€¢ DTCD VALIDATION FAILED\n"
                        f"  Entry No      : {entry_no}\n"
                        f"  Account Code  : {account_code}\n"
                        f"  Sub Account   : {sub_account}\n"
                        f"  Difference    : â‚¹{difference}"
                    )

                # =================================================
                # DEFAULT ERROR
                # =================================================

                else:

                    readable_error = (
                        f"â€¢ Row {row_number}: "
                        f"Issue found in "
                        f"'{failed_field}' field."
                    )

                # =================================================
                # APPEND ERROR
                # =================================================

                formatted_errors += (
                    readable_error + "\n\n"
                )

        # =====================================================
        # LLM PROMPT
        # =====================================================

        prompt = f"""
{get_agent_prompt("notification")}

Generate a professional email for an admin.

Context:
The financial extraction pipeline failed validation
after multiple retry attempts.

Validation Errors:
{formatted_errors}

Instructions:
1. Generate a professional email subject.
2. Generate a professional email body.
3. Keep the tone formal and corporate.
4. Use simple business English.
5. Mention that manual verification is required.
6. Do NOT include JSON.
7. Do NOT include technical logs.
8. Do NOT mention Pydantic.
9. Do NOT mention parsing errors.
10. End professionally.
11. After Regards add EY.

Return ONLY in this format:

SUBJECT:
<subject here>

BODY:
<body here>
"""

        # =====================================================
        # SEND TO GROQ
        # =====================================================

        response = get_groq_client().chat.completions.create(

            model="llama-3.3-70b-versatile",

            messages=[
                {
                    "role": "system",
                    "content": get_agent_prompt("notification")
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0
        )

        # =====================================================
        # GENERATED RESPONSE
        # =====================================================

        generated_text = (
            response
            .choices[0]
            .message.content
        )

        print(
            "\nGENERATED EMAIL:\n"
        )

        print(generated_text)

        # =====================================================
        # EXTRACT SUBJECT
        # =====================================================

        subject = (
            generated_text
            .split("BODY:")[0]
            .replace("SUBJECT:", "")
            .strip()
        )

        # =====================================================
        # EXTRACT BODY
        # =====================================================

        body = (
            generated_text
            .split("BODY:")[1]
            .strip()
        )

        # =====================================================
        # CREATE EMAIL
        # =====================================================

        sender_email = require_env_alias("LEDGERFLOW_SENDER_EMAIL", "LEDGERFLOW_MAIL_USERNAME", "EMAIL_USER")

        manager_email = os.getenv(MANAGER_EMAIL_ENV) or sender_email
        if not manager_email:
            raise GuardrailViolation(f"Missing required environment variable: {MANAGER_EMAIL_ENV}")

        sender_password = require_env_alias("LEDGERFLOW_SENDER_EMAIL_APP_PASSWORD", "LEDGERFLOW_MAIL_PASSWORD", "EMAIL_PASS")

        smtp_host = os.getenv(SMTP_HOST_ENV) or "smtp.gmail.com"
        smtp_port = int(os.getenv(SMTP_PORT_ENV) or "587")

        msg = MIMEText(body)

        msg["Subject"] = subject

        msg["From"] = sender_email

        msg["To"] = manager_email

        # =====================================================
        # EMAIL RETRY
        # =====================================================

        MAX_RETRIES = 3

        email_sent = False

        last_error = None

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                print(
                    f"\nEMAIL SEND ATTEMPT "
                    f"{attempt}/{MAX_RETRIES}\n"
                )

                # =================================================
                # SMTP CONNECTION
                # =================================================

                server = smtplib.SMTP(
                    smtp_host,
                    smtp_port,
                    timeout=30
                )

                server.starttls()

                # =================================================
                # LOGIN
                # =================================================

                server.login(
                    sender_email,
                    sender_password
                )

                # =================================================
                # SEND EMAIL
                # =================================================

                server.send_message(msg)

                # =================================================
                # CLOSE CONNECTION
                # =================================================

                server.quit()

                print(
                    "\nEMAIL SENT SUCCESSFULLY\n"
                )

                email_sent = True

                break

            except Exception as smtp_error:

                last_error = smtp_error

                print(
                    f"\nEMAIL ATTEMPT "
                    f"{attempt} FAILED:\n"
                )

                print(smtp_error)

                # =================================================
                # WAIT BEFORE RETRY
                # =================================================

                time.sleep(
                    attempt * 3
                )

        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        if email_sent:

            print(
                "\nFAILURE EMAIL "
                "SENT SUCCESSFULLY\n"
            )

            return {

                "status": "notification_sent",

                "subject": subject,

                "attempts_used": attempt
            }

        else:

            print(
                "\nALL EMAIL ATTEMPTS FAILED\n"
            )

            return {

                "status": "notification_failed",

                "error": safe_error_message(last_error)
            }

    # =========================================================
    # EXCEPTION HANDLING
    # =========================================================

    except Exception as e:

        print(
            "\nNOTIFICATION ERROR:\n"
        )

        print(e)

        return {

            "status": "notification_failed",

            "error": safe_error_message(e)
        }




