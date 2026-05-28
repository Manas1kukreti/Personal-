print("GRAPH FILE STARTED")

import json
import time

from typing import TypedDict

print("TypedDict imported")

from langgraph.graph import StateGraph, END

print("LangGraph imported")

from data_input import get_email_text

print("data_input imported")

from llm_extractor import extract_data

print("llm_extractor imported")

from validator import validate_data

print("validator imported")

from ui_agent import (
    push_to_ui,
    login_tool
)

print("ui_agent imported")

from re_extractor import re_extract_field

print("re_extractor imported")

from pushing_validation_alert_tool import (
    push_validation_alert_tool
)

print("pushing_validation_alert_tool imported")


# =========================================================
# STATE
# =========================================================

class AgentState(TypedDict):

    email_text: str

    extracted_data: str

    validation_result: dict

    corrected_data: dict

    ui_result: dict

    retry_count: int

    processing_status: str


# =========================================================
# NODE 1 → FETCH EMAIL
# =========================================================

def fetch_email_node(state):

    print("\n=================================================")
    print("AGENT: EMAIL AGENT")
    print("TOOLS USED:")
    print("- Gmail IMAP")
    print("- Email Parser")
    print("- Attachment Reader")
    print("=================================================\n")

    print("\nFETCHING EMAIL...\n")

    email_text = get_email_text()

    return {

        "email_text": email_text,

        "retry_count": 0,

        "processing_status": "email_fetched"
    }


# =========================================================
# NODE 2 → INPUT AGENT
# =========================================================

def preprocessing_tools_node(state):

    print("\n=================================================")
    print("AGENT: INPUT AGENT")
    print("TOOLS USED:")
    print("- Excel Reader Tool")
    print("- Field Mapper Tool")
    print("- Relational Mapper Tool")
    print("- Financial Logic Tool")
    print("- Data Cleaner Tool")
    print("=================================================\n")

    print("\nRUNNING INPUT PREPROCESSING...\n")

    return {

        "processing_status": "preprocessed"
    }


# =========================================================
# NODE 3 → EXTRACTION AGENT
# =========================================================

def extract_data_node(state):

    print("\n=================================================")
    print("AGENT: EXTRACTION AGENT")
    print("TOOLS USED:")
    print("- Groq API")
    print("- Llama 3.3 70B")
    print("- Prompt Engineering")
    print("- Structured JSON Extraction")
    print("=================================================\n")

    print("\nRUNNING LLM EXTRACTION...\n")

    extracted = extract_data(
        state["email_text"]
    )

    return {

        "extracted_data": extracted,

        "processing_status": "data_extracted"
    }


# =========================================================
# NODE 4 → VALIDATOR AGENT
# =========================================================

def validate_node(state):

    print("\n=================================================")
    print("AGENT: VALIDATOR AGENT")
    print("TOOLS USED:")
    print("- Pydantic")
    print("- JSON Schema Validation")
    print("- Voucher Balancing Logic")
    print("- Financial Validation Engine")
    print("- RapidFuzz Similarity")
    print("=================================================\n")

    print("\nVALIDATING DATA...\n")

    result = validate_data(

        state["email_text"],

        state["extracted_data"]
    )

    print("\nVALIDATION RESULT:\n")

    print(result)

    retry_count = state.get(
        "retry_count",
        0
    )

    # =====================================================
    # CHECK NORMAL ERRORS ONLY
    # =====================================================

    errors = result.get(
        "errors",
        []
    )

    normal_errors = []

    for err in errors:

        error_text = str(
            err.get("error", "")
        ).lower()

        if (
            "not balanced" not in error_text
            and "difference" not in error_text
        ):

            normal_errors.append(err)

    # =====================================================
    # RETRY ONLY FOR NORMAL ERRORS
    # =====================================================

    if normal_errors:

        retry_count += 1

    return {

        "validation_result": result,

        "retry_count": retry_count,

        "processing_status": "validated"
    }


# =========================================================
# NODE 5 → RE-EXTRACTION AGENT
# =========================================================

def re_extract_node(state):

    print("\n=================================================")
    print("AGENT: RE-EXTRACTION AGENT")
    print("TOOLS USED:")
    print("- Groq API")
    print("- Llama 3.3 70B")
    print("- JSON Repair")
    print("- Field Correction Logic")
    print("=================================================\n")

    print(
        "\nRE-EXTRACTING INVALID FIELDS...\n"
    )

    validation = state[
        "validation_result"
    ]

    errors = validation.get(
        "errors",
        []
    )

    # =====================================================
    # JSON LOAD
    # =====================================================

    try:

        parsed_data = json.loads(
            state["extracted_data"]
        )

    except Exception as e:

        print("\nJSON LOAD FAILED\n")

        print(e)

        retry_count = state.get(
            "retry_count",
            0
        ) + 1

        return {

            "processing_status":
            "re_extract_failed",

            "retry_count":
            retry_count
        }

    # =====================================================
    # INVALID DATA TYPE
    # =====================================================

    if not isinstance(parsed_data, list):

        print("\nINVALID PARSED DATA\n")

        retry_count = state.get(
            "retry_count",
            0
        ) + 1

        return {

            "processing_status":
            "re_extract_failed",

            "retry_count":
            retry_count
        }

    # =====================================================
    # LOOP THROUGH ERRORS
    # =====================================================

    for error in errors:

        error_text = str(
            error.get("error", "")
        ).lower()

        # =================================================
        # SKIP DTCD ERRORS
        # =================================================

        if (
            "not balanced" in error_text
            or
            "difference" in error_text
        ):

            print(
                "\nSKIPPING DTCD "
                "RE-EXTRACTION\n"
            )

            continue

        if "failed_field" not in error:

            continue

        failed_field = error[
            "failed_field"
        ]

        current_value = error.get(
            "current_value",
            ""
        )

        transaction_index = error.get(
            "transaction_index",
            0
        )

        if transaction_index >= len(parsed_data):

            continue

        failed_transaction = parsed_data[
            transaction_index
        ]

        print(
            f"\nFIXING TRANSACTION "
            f"{transaction_index}"
        )

        print(
            f"FAILED FIELD: "
            f"{failed_field}"
        )

        corrected_value = re_extract_field(

            failed_transaction,

            failed_field,

            current_value
        )

        if corrected_value is None:

            print(
                "\nFAILED TO RECOVER FIELD\n"
            )

            continue

        parsed_data[
            transaction_index
        ][failed_field] = corrected_value

    # =====================================================
    # UPDATED JSON
    # =====================================================

    updated_json = json.dumps(
        parsed_data,
        indent=4
    )

    return {

        "extracted_data":
        updated_json,

        "processing_status":
        "re_extracted"
    }


# =========================================================
# NODE 6 → UI AGENT
# =========================================================

def push_to_ui_node(state):

    print("\n=================================================")
    print("AGENT: UI AGENT")
    print("TOOLS USED:")
    print("- Excel Generator")
    print("- JSON Export")
    print("- REST API")
    print("- Frontend Connector")
    print("=================================================\n")

    print(
        "\nPUSHING DATA TO FRONTEND...\n"
    )

    result = push_to_ui(
        state["validation_result"]
    )

    print("\nUI RESULT:\n")

    print(result)

    validation_result = state[
        "validation_result"
    ]

    errors = validation_result.get(
        "errors",
        []
    )

    # =====================================================
    # DTCD CHECK
    # =====================================================

    dtcd_errors = []

    for err in errors:

        error_text = str(
            err.get("error", "")
        ).lower()

        if (
            "not balanced" in error_text
            or "difference" in error_text
        ):

            dtcd_errors.append(err)

    # =====================================================
    # STATUS
    # =====================================================

    if dtcd_errors:

        status = "ui_pushed_with_alert"

    else:

        status = "completed"

    return {

        "ui_result": result,

        "processing_status": status
    }


# =========================================================
# NODE 7 → NOTIFICATION AGENT
# =========================================================

def notification_node(state):

    print("\n=================================================")
    print("AGENT: NOTIFICATION AGENT")
    print("TOOLS USED:")
    print("- Validation Alert Tool")
    print("- REST API")
    print("- Frontend Alert System")
    print("=================================================\n")

    validation_result = state[
        "validation_result"
    ]

    errors = validation_result.get(
        "errors",
        []
    )

    # =====================================================
    # FILTER DTCD ERRORS
    # =====================================================

    dtcd_errors = []

    for err in errors:

        error_text = str(
            err.get("error", "")
        ).lower()

        if (
            "not balanced" in error_text
            or "difference" in error_text
        ):

            dtcd_errors.append(err)

    # =====================================================
    # LOGIN WITH RETRY
    # =====================================================

    token = None

    for attempt in range(3):

        try:

            print(
                f"\nLOGIN ATTEMPT "
                f"{attempt + 1}/3\n"
            )

            token = login_tool()

            print(
                "\nLOGIN SUCCESSFUL\n"
            )

            break

        except Exception as e:

            print(
                "\nLOGIN FAILED:\n"
            )

            print(e)

            time.sleep(5)

    # =====================================================
    # LOGIN FAILED
    # =====================================================

    if token is None:

        print(
            "\nFRONTEND LOGIN FAILED "
            "AFTER 3 ATTEMPTS\n"
        )

        return {

            "processing_status":
            "notification_failed"
        }

    # =====================================================
    # PUSH ALERTS
    # =====================================================

    for error in dtcd_errors:

        print(
            "\nPUSHING DTCD ALERT...\n"
        )

        alert_payload = {

            "Entry no":
            error.get(
                "Entry no",
                "UNKNOWN"
            ),

            "Account code":
            error.get(
                "Account code",
                "UNKNOWN"
            ),

            "Sub Account":
            error.get(
                "Sub Account",
                "UNKNOWN"
            ),

            "difference":
            error.get(
                "difference",
                0
            ),

            "status":
            "FAILED"
        }

        result = push_validation_alert_tool(

            token=token,

            alert_payload=alert_payload
        )

        print(
            "\nALERT RESULT:\n"
        )

        print(result)

    return {

        "processing_status":
        "manual_review_required"
    }


# =========================================================
# VALIDATION ROUTER
# =========================================================

def validation_router(state):

    validation_result = state.get(
        "validation_result",
        {}
    )

    status = validation_result.get(
        "status"
    )

    errors = validation_result.get(
        "errors",
        []
    )

    retry_count = state.get(
        "retry_count",
        0
    )

    # =====================================================
    # VALID DATA
    # =====================================================

    if status == "valid":

        print(
            "\nVALID DATA DETECTED\n"
        )

        return "valid"

    # =====================================================
    # JSON / EXTRACTION ERRORS
    # =====================================================

    validation_error = str(
        validation_result.get(
            "error",
            ""
        )
    ).lower()

    if (

        "expecting value" in validation_error
        or
        "json" in validation_error
        or
        "decode" in validation_error

    ):

        print(
            "\nJSON / EXTRACTION ERROR DETECTED\n"
        )

        retry_count += 1

        state["retry_count"] = retry_count

        print(
            f"\nRETRY COUNT: "
            f"{retry_count}/5\n"
        )

        # =================================================
        # MAX RETRIES REACHED
        # =================================================

        if retry_count >= 5:

            print(
                "\nMAX JSON RETRIES REACHED\n"
            )

            return "notify"

        return "re_extract"

    # =====================================================
    # DTCD ERRORS
    # =====================================================

    dtcd_errors = []

    for err in errors:

        error_text = str(
            err.get("error", "")
        ).lower()

        if (
            "not balanced" in error_text
            or
            "difference" in error_text
        ):

            dtcd_errors.append(err)

    # =====================================================
    # DTCD FLOW
    # =====================================================

    if dtcd_errors:

        print(
            "\nDTCD DIFFERENCE DETECTED\n"
        )

        print(
            "\nSENDING TO UI + ALERT FLOW\n"
        )

        return "push_with_alert"

    # =====================================================
    # NORMAL VALIDATION ERRORS
    # =====================================================

    retry_count += 1

    state["retry_count"] = retry_count

    print(
        f"\nNORMAL RETRY COUNT: "
        f"{retry_count}/5\n"
    )

    if retry_count >= 5:

        print(
            "\nMAX RETRIES COMPLETED\n"
        )

        return "notify"

    return "re_extract"

    # =====================================================
    # DTCD ERRORS
    # =====================================================

    dtcd_errors = []

    for err in errors:

        error_text = str(
            err.get("error", "")
        ).lower()

        if (
            "not balanced" in error_text
            or
            "difference" in error_text
        ):

            dtcd_errors.append(err)

    # =====================================================
    # DTCD FLOW
    # =====================================================

    if dtcd_errors:

        print(
            "\nDTCD DIFFERENCE DETECTED\n"
        )

        return "push_with_alert"

    # =====================================================
    # NORMAL VALIDATION ERRORS
    # =====================================================

    retry_count += 1

    print(
        f"\nNORMAL RETRY COUNT: "
        f"{retry_count}/5\n"
    )

    if retry_count >= 5:

        print(
            "\nMAX RETRIES COMPLETED\n"
        )

        return "notify"

    state["retry_count"] = retry_count

    return "re_extract"

    # =====================================================
    # DTCD CHECK
    # =====================================================

    dtcd_errors = []

    for err in errors:

        error_text = str(
            err.get("error", "")
        ).lower()

        # =================================================
        # DTCD ERRORS SHOULD NOT GO TO RE-EXTRACT
        # =================================================

        if (
            "not balanced" in error_text
            or "difference" in error_text
        ):

            dtcd_errors.append(err)

    # =====================================================
    # PUSH WITH ALERT
    # =====================================================

    if dtcd_errors:

        print(
            "\nDTCD DIFFERENCE DETECTED\n"
        )

        print(
            "\nSENDING TO UI + ALERT FLOW\n"
        )

        return "push_with_alert"

    # =====================================================
    # NORMAL RETRY FLOW
    # =====================================================

    current_retry = state.get(
        "retry_count",
        0
    )

    print(
        f"\nINVALID DATA "
        f"→ RETRY {current_retry}/5\n"
    )

    # =====================================================
    # MAX RETRIES
    # =====================================================

    if current_retry >= 5:

        print(
            "\nMAX RETRIES COMPLETED\n"
        )

        return "notify"

    # =====================================================
    # NORMAL RE-EXTRACTION
    # =====================================================

    return "re_extract"
 


# =========================================================
# BUILD GRAPH
# =========================================================

workflow = StateGraph(
    AgentState
)


# =========================================================
# ADD NODES
# =========================================================

workflow.add_node(
    "fetch_email",
    fetch_email_node
)

workflow.add_node(
    "preprocessing_tools",
    preprocessing_tools_node
)

workflow.add_node(
    "extract_data",
    extract_data_node
)

workflow.add_node(
    "validate",
    validate_node
)

workflow.add_node(
    "re_extract",
    re_extract_node
)

workflow.add_node(
    "push_to_ui",
    push_to_ui_node
)

workflow.add_node(
    "notification",
    notification_node
)


# =========================================================
# ENTRY POINT
# =========================================================

workflow.set_entry_point(
    "fetch_email"
)


# =========================================================
# MAIN FLOW
# =========================================================

workflow.add_edge(
    "fetch_email",
    "preprocessing_tools"
)

workflow.add_edge(
    "preprocessing_tools",
    "extract_data"
)

workflow.add_edge(
    "extract_data",
    "validate"
)

workflow.add_edge(
    "re_extract",
    "validate"
)


# =========================================================
# CONDITIONAL ROUTING
# =========================================================

workflow.add_conditional_edges(

    "validate",

    validation_router,

    {

        "valid": "push_to_ui",

        "push_with_alert": "push_to_ui",

        "re_extract": "re_extract",

        "notify": "notification"
    }
)


# =========================================================
# UI CONDITIONAL FLOW
# =========================================================

workflow.add_conditional_edges(

    "push_to_ui",

    lambda state:
    state["processing_status"],

    {

        "completed": END,

        "ui_pushed_with_alert":
        "notification"
    }
)


# =========================================================
# FINAL EDGE
# =========================================================

workflow.add_edge(
    "notification",
    END
)


# =========================================================
# COMPILE GRAPH
# =========================================================

app = workflow.compile()


# =========================================================
# GENERATE GRAPH IMAGE
# =========================================================

try:

    graph_image = (
        app.get_graph()
        .draw_mermaid_png()
    )

    with open(
        "graph.png",
        "wb"
    ) as f:

        f.write(graph_image)

    print(
        "\nGRAPH IMAGE SAVED "
        "AS graph.png\n"
    )

except Exception as e:

    print(
        "\nERROR GENERATING GRAPH:\n"
    )

    print(e)