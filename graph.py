print("GRAPH FILE STARTED")

import json
import time

from typing import TypedDict

print("TypedDict imported")

from langgraph.graph import StateGraph, END

print("LangGraph imported")

from import_paths import ensure_project_paths

ensure_project_paths()

from agents.data_input import get_email_text

print("data_input imported")

from agents.llm_extractor import extract_data

print("llm_extractor imported")

from agents.validator import validate_data

print("validator imported")

from agents.ui_agent import (
    push_to_ui,
    login_tool
)

print("ui_agent imported")

from agents.re_extractor import re_extract_field

print("re_extractor imported")

from agents.react_agent import choose_validation_route

print("react_agent imported")

from pushing_validation_alert_tool import (
    push_validation_alert_tool
)

print("pushing_validation_alert_tool imported")

from config_loader import get_agent_config
from config_loader import get_workflow_config


# =========================================================
# STATE
# =========================================================

class AgentState(TypedDict, total=False):

    email_text: str

    extracted_data: str

    validation_result: dict

    corrected_data: dict

    ui_result: dict

    retry_count: int

    processing_status: str


# =========================================================
# DYNAMIC WORKFLOW HELPERS
# =========================================================

def get_max_retries():

    workflow_config = get_workflow_config()

    return workflow_config.get(
        "max_retries",
        5
    )


def print_agent_profile(agent_name):

    agent_config = get_agent_config(
        agent_name
    )

    role = agent_config.get(
        "role"
    )

    performs = agent_config.get(
        "performs",
        []
    )

    if role:

        print(f"ROLE: {role}")

    if performs:

        print("HOW IT PERFORMS:")

        for item in performs:

            print(f"- {item}")


def ensure_json_string(data):

    if isinstance(data, str):

        return data

    return json.dumps(
        data,
        indent=2,
        default=str
    )


def is_structured_data(data):

    if not data:

        return False

    try:

        parsed = json.loads(data) if isinstance(
            data,
            str
        ) else data

    except Exception:

        return False

    if isinstance(parsed, dict):

        parsed = parsed.get(
            "transactions",
            []
        )

    if not isinstance(parsed, list) or not parsed:

        return False

    first_row = parsed[0]

    if not isinstance(first_row, dict):

        return False

    workflow_config = get_workflow_config()

    required_fields = workflow_config.get(
        "structured_data_required_fields",
        []
    )

    if not required_fields:

        return True

    return any(
        field in first_row
        for field in required_fields
    )


def has_dtcd_errors(validation_result):

    errors = validation_result.get(
        "errors",
        []
    )

    for err in errors:

        error_text = str(
            err.get("error", "")
        ).lower()

        if (
            "not balanced" in error_text
            or "difference" in error_text
        ):

            return True

    return False


def supervisor_node(state):

    print("\n=================================================")
    print("AGENT: SUPERVISOR AGENT")
    print("TOOLS USED:")
    print("- State Inspection")
    print("- Dynamic Routing")
    print("- Backtracking Rules")
    print("=================================================\n")

    print_agent_profile("supervisor")

    return {}


def supervisor_router(state):

    processing_status = state.get(
        "processing_status",
        ""
    )

    retry_count = state.get(
        "retry_count",
        0
    )

    if processing_status in [

        "re_extracted",
        "data_extracted",
        "extraction_skipped"
    ]:

        return "validate"

    if processing_status == "re_extract_failed":

        if retry_count >= get_max_retries():

            return "notification"

        return "extract_data"

    if processing_status == "preprocessed":

        return "extract_data"

    validation_result = state.get(
        "validation_result"
    )

    if validation_result:

        status = validation_result.get(
            "status"
        )

        if status == "valid" or has_dtcd_errors(
            validation_result
        ):

            return "push_to_ui"

        if retry_count >= get_max_retries():

            return "notification"

        return "re_extract"

    extracted_data = state.get(
        "extracted_data"
    )

    if is_structured_data(extracted_data):

        print(
            "\nSTRUCTURED DATA ALREADY AVAILABLE. "
            "SKIPPING EXTRACTION.\n"
        )

        return "validate"

    email_text = state.get(
        "email_text"
    )

    if is_structured_data(email_text):

        print(
            "\nEMAIL/ATTACHMENT OUTPUT IS ALREADY "
            "STRUCTURED JSON. SKIPPING EXTRACTION.\n"
        )

        return "validate"

    if not email_text:

        return "fetch_email"

    if processing_status != "preprocessed":

        return "preprocessing_tools"

    return "extract_data"


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

    print_agent_profile("email")

    print("\nFETCHING EMAIL...\n")

    email_text = get_email_text()

    result = {

        "email_text": email_text,

        "retry_count": 0,

        "processing_status": "email_fetched"
    }

    if is_structured_data(email_text):

        result["extracted_data"] = ensure_json_string(
            email_text
        )

    return result


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

    print_agent_profile("input")

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

    print_agent_profile("extraction")

    existing_data = state.get(
        "extracted_data"
    )

    if is_structured_data(existing_data):

        print(
            "\nSTRUCTURED DATA FOUND. "
            "EXTRACTION STEP SKIPPED.\n"
        )

        return {

            "extracted_data":
            ensure_json_string(existing_data),

            "processing_status":
            "extraction_skipped"
        }

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

    print_agent_profile("validation")

    print("\nVALIDATING DATA...\n")

    extracted_data = state.get(
        "extracted_data"
    )

    if not extracted_data and is_structured_data(
        state.get("email_text")
    ):

        extracted_data = state.get(
            "email_text"
        )

    result = validate_data(

        state["email_text"],

        ensure_json_string(extracted_data)
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

    print_agent_profile("re_extraction")

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

    print_agent_profile("ui")

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

    print_agent_profile("notification")

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

def react_route_or_default(state, default_route):

    print("\n=================================================")
    print("AGENT: REACT SUPERVISOR")
    print("TOOLS USED:")
    print("- Groq API")
    print("- Llama 3.3 70B")
    print("- Validation Route Reasoning")
    print("=================================================\n")

    try:

        react_route = choose_validation_route(
            state
        )

        print(
            "\nREACT SUPERVISOR ROUTE:\n"
        )

        print(react_route)

    except Exception as e:

        print(
            "\nREACT SUPERVISOR FAILED:\n"
        )

        print(e)

        return default_route

    if react_route == default_route:

        return react_route

    print(
        "\nREACT ROUTE DID NOT MATCH "
        "VALIDATION SAFETY CHECK\n"
    )

    print(
        "USING SAFE GRAPH ROUTE:\n"
    )

    print(default_route)

    return default_route


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

        return react_route_or_default(
            state,
            "valid"
        )

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
            f"{retry_count}/"
            f"{get_max_retries()}\n"
        )

        # =================================================
        # MAX RETRIES REACHED
        # =================================================

        if retry_count >= get_max_retries():

            print(
                "\nMAX JSON RETRIES REACHED\n"
            )

            return react_route_or_default(
                state,
                "notify"
            )

        return react_route_or_default(
            state,
            "re_extract"
        )

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

        return react_route_or_default(
            state,
            "push_with_alert"
        )

    # =====================================================
    # NORMAL VALIDATION ERRORS
    # =====================================================

    retry_count += 1

    state["retry_count"] = retry_count

    print(
        f"\nNORMAL RETRY COUNT: "
        f"{retry_count}/"
        f"{get_max_retries()}\n"
    )

    if retry_count >= get_max_retries():

        print(
            "\nMAX RETRIES COMPLETED\n"
        )

        return react_route_or_default(
            state,
            "notify"
        )

    return react_route_or_default(
        state,
        "re_extract"
    )


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
    "supervisor",
    supervisor_node
)

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
    "supervisor"
)


# =========================================================
# MAIN FLOW
# =========================================================

workflow.add_conditional_edges(

    "supervisor",

    supervisor_router,

    {

        "fetch_email": "fetch_email",

        "preprocessing_tools": "preprocessing_tools",

        "extract_data": "extract_data",

        "validate": "validate",

        "re_extract": "re_extract",

        "push_to_ui": "push_to_ui",

        "notification": "notification"
    }
)

workflow.add_edge(
    "fetch_email",
    "supervisor"
)

workflow.add_edge(
    "preprocessing_tools",
    "supervisor"
)

workflow.add_edge(
    "extract_data",
    "supervisor"
)

workflow.add_edge(
    "re_extract",
    "supervisor"
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

    graph_definition = (
        app.get_graph()
        .draw_mermaid()
    )

    with open(
        "graph.mmd",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(graph_definition)

    print(
        "\nGRAPH DEFINITION SAVED "
        "AS graph.mmd\n"
    )

except Exception as e:

    print(
        "\nERROR GENERATING GRAPH:\n"
    )

    print(e)
