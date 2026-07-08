# =========================================================
# PUSH VALIDATION ALERT TOOL
# =========================================================

import httpx

from ledgerflow_agent.env import get_frontend_base_url
from ledgerflow_agent.guardrails import safe_error_message, validate_api_base_url


# =========================================================
# LAZY URL RESOLUTION
# =========================================================
# BASE_URL must NOT be evaluated at import time — doing so causes the
# entire module import to fail with a misleading "No module named ..."
# error if the env var is missing or the host isn't whitelisted yet.
# Resolve it once, lazily, inside the function instead.

def _get_alert_url() -> str:
    base = validate_api_base_url(get_frontend_base_url())
    return f"{base}/api/alerts"


# =========================================================
# PUSH VALIDATION ALERT TOOL
# =========================================================

def push_validation_alert_tool(token, alert_payload):

    print("\nPUSHING VALIDATION ALERT TO UI...\n")

    try:

        alert_api_url = _get_alert_url()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = httpx.post(
            alert_api_url,
            headers=headers,
            json=alert_payload,
            timeout=30.0,
        )

        print("ALERT RESPONSE:", response.status_code)

        if response.status_code not in [200, 201]:
            raise Exception(
                f"ALERT PUSH FAILED → "
                f"{response.status_code} → response body omitted"
            )

        print("\nVALIDATION ALERT PUSHED SUCCESSFULLY\n")
        return {"status": "success"}

    except Exception as e:
        print("\nVALIDATION ALERT PUSH FAILED\n")
        print(safe_error_message(e))
        return {"status": "failed", "error": safe_error_message(e)}
