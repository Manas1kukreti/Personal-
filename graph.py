print("GRAPH FILE STARTED")

import json
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

from ui_agent import push_to_ui

print("ui_agent imported")

from notification_agent import (
    send_failure_notification
)

print("notification_agent imported")

from re_extractor import re_extract_field

print("re_extractor imported")


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


# =========================================================
# NODE 1 → FETCH EMAIL
# =========================================================

def fetch_email_node(state):

    print("\nFETCHING EMAIL...\n")

    email_text = get_email_text()

    return {

        "email_text": email_text,

        "retry_count": 0
    }


# =========================================================
# NODE 2 → EXTRACT DATA
# =========================================================

def extract_data_node(state):

    print("\nEXTRACTING DATA...\n")

    extracted = extract_data(
        state["email_text"]
    )

    return {

        "extracted_data": extracted
    }


# =========================================================
# NODE 3 → VALIDATE DATA
# =========================================================

def validate_node(state):

    print("\nVALIDATING DATA...\n")

    result = validate_data(

        state["email_text"],

        state["extracted_data"]
    )

    print("\nVALIDATION RESULT:\n")
    print(result)

    # =====================================================
    # CURRENT RETRY COUNT
    # =====================================================

    retry_count = state.get(
        "retry_count",
        0
    )

    # =====================================================
    # INCREMENT ONLY IF INVALID
    # =====================================================

    if result["status"] == "invalid":

        retry_count += 1

    return {

        "validation_result": result,

        "retry_count": retry_count
    }


# =========================================================
# NODE 4 → RE-EXTRACT FAILED FIELD
# =========================================================

def re_extract_node(state):

    print(
        "\nRE-EXTRACTING FAILED FIELD...\n"
    )

    validation = state[
        "validation_result"
    ]

    failed_field = validation[
        "failed_field"
    ]

    current_value = validation[
        "current_value"
    ]

    transaction_index = validation[
        "transaction_index"
    ]

    # =====================================================
    # LOAD EXISTING JSON
    # =====================================================

    parsed_data = json.loads(
        state["extracted_data"]
    )

    # =====================================================
    # FAILED TRANSACTION ONLY
    # =====================================================

    failed_transaction = parsed_data[
        transaction_index
    ]

    # =====================================================
    # RE-EXTRACT FIELD
    # =====================================================

    corrected_value = re_extract_field(

        failed_transaction,

        failed_field,

        current_value
    )

    # =====================================================
    # RE-EXTRACTION FAILED
    # =====================================================

    if corrected_value is None:

        print(
            "\nRE-EXTRACTION COULD "
            "NOT RECOVER VALUE\n"
        )

        return {

            "extracted_data": state[
                "extracted_data"
            ]
        }

    # =====================================================
    # UPDATE FAILED FIELD
    # =====================================================

    parsed_data[
        transaction_index
    ][failed_field] = corrected_value

    updated_json = json.dumps(
        parsed_data,
        indent=4
    )

    print(
        "\nUPDATED TRANSACTION FIELD:\n"
    )

    print(
        parsed_data[transaction_index]
    )

    return {

        "extracted_data": updated_json
    }


# =========================================================
# NODE 5 → PUSH TO UI
# =========================================================

def push_to_ui_node(state):

    print("\nPUSHING DATA TO FRONTEND...\n")

    result = push_to_ui(
        state["validation_result"]
    )

    print("\nUI RESULT:\n")
    print(result)

    return {

        "ui_result": result
    }


# =========================================================
# NODE 6 → NOTIFICATION AGENT
# =========================================================

def notification_node(state):

    print(
        "\nMANUAL VERIFICATION REQUIRED\n"
    )

    result = send_failure_notification(
        state["validation_result"]
    )

    print("\nNOTIFICATION RESULT:\n")
    print(result)

    return {}


# =========================================================
# VALIDATION ROUTER
# =========================================================

def validation_router(state):

    # =====================================================
    # VALID DATA
    # =====================================================

    if (

        state["validation_result"][
            "status"
        ] == "valid"

    ):

        print(
            "\nVALIDATION SUCCESSFUL\n"
        )

        return "valid"

    # =====================================================
    # INVALID DATA
    # =====================================================

    current_retry = state.get(
        "retry_count",
        0
    )

    print(
        f"\nVALIDATION FAILED "
        f"→ RETRY {current_retry}/5\n"
    )

    # =====================================================
    # MAX RETRIES REACHED
    # =====================================================

    if current_retry >= 5:

        print(
            "\nMAX RETRIES REACHED\n"
        )

        return "notify"

    # =====================================================
    # RE-EXTRACT
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
# CONDITIONAL VALIDATION FLOW
# =========================================================

workflow.add_conditional_edges(

    "validate",

    validation_router,

    {

        "valid": "push_to_ui",

        "re_extract": "re_extract",

        "notify": "notification"
    }
)


# =========================================================
# FINAL FLOWS
# =========================================================

workflow.add_edge(
    "push_to_ui",
    END
)

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