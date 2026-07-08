try:
    from langchain.tools import Tool
except ImportError:
    from langchain_core.tools import Tool

try:
    from langchain.tools import tool
except ImportError:
    from langchain_core.tools import tool

try:
    from langchain.tools import StructuredTool
except ImportError:
    from langchain_core.tools import StructuredTool

from typing import Any
from pydantic import BaseModel

# =========================================================
# IMPORT CORE AGENTS
# =========================================================

from agents.data_input import get_email_text
from agents.llm_extractor import extract_data
from agents.validator import validate_data
from agents.ui_agent import push_to_ui

# =========================================================
# IMPORT PREPROCESSING TOOLS
# =========================================================

from tools.excel_reader_tool import read_excel_tool
from tools.limit_tool import limit_rows_tool
from tools.field_mapper_tool import field_mapper_tool
from tools.text_cleaner_tool import clean_dataframe_tool
from tools.relation_mapper_tool import relation_mapper_tool
from tools.financial_logic_tool import financial_logic_tool
from tools.pushing_validation_alert_tool import push_validation_alert_tool


# =========================================================
# TOOL 1 → EMAIL TOOL
# =========================================================

@tool
def email_extraction_tool(query: str = "") -> str:
    """Fetches latest financial email and extracts raw body text and attachments."""
    return get_email_text()

# Keep legacy alias for ALL_TOOLS list
email_tool = email_extraction_tool


# =========================================================
# TOOL 2 → LLM EXTRACTION TOOL
# =========================================================

@tool
def financial_data_extractor(text: str) -> str:
    """Extracts structured financial transactions from raw email or Excel text using LLM."""
    return extract_data(text)

llm_tool = financial_data_extractor


# =========================================================
# TOOL 3 → VALIDATOR TOOL
# =========================================================

class _ValidatorInput(BaseModel):
    """Input schema for validator_tool — accepts string or object from Groq."""
    json_data: Any


def _validator_fn(json_data: Any) -> str:
    """
    Validates extracted financial JSON.

    Accepts:
      (a) A JSON string  — bare array or envelope {"email_text": ..., "extracted_data": ...}
      (b) A pre-parsed dict/list (Groq sends the object directly after the schema fix).
    """
    import json as _json

    email_text = ""

    # Normalise: if it's already a Python object, use it; otherwise parse the string.
    if isinstance(json_data, (dict, list)):
        payload = json_data
    else:
        try:
            payload = _json.loads(json_data)
        except (_json.JSONDecodeError, TypeError):
            return validate_data("", str(json_data))

    if isinstance(payload, dict):
        email_text = payload.get("email_text", "")
        extracted_data = payload.get("extracted_data", payload)
        if not isinstance(extracted_data, str):
            extracted_data = _json.dumps(extracted_data)
    else:
        extracted_data = _json.dumps(payload) if not isinstance(payload, str) else payload

    return validate_data(email_text, extracted_data)


validator_tool = StructuredTool.from_function(
    func=_validator_fn,
    name="validator_tool",
    description=(
        "Validates extracted financial JSON using schema validation and financial business rules. "
        "Pass the extracted_data as a JSON array or an envelope object with email_text and extracted_data keys."
    ),
    args_schema=_ValidatorInput,
)


# =========================================================
# TOOL 4 → UI PUSH TOOL
# =========================================================

ui_tool = Tool(

    name="ui_push_tool",

    func=push_to_ui,

    description=(
        "Pushes validated structured "
        "financial data to frontend dashboard."
    )
)


# =========================================================
# TOOL 5 → EXCEL READER TOOL
# =========================================================

excel_reader_tool = Tool(

    name="excel_reader_tool",

    func=read_excel_tool,

    description=(
        "Reads Excel files and identifies "
        "the correct financial transaction sheet."
    )
)


# =========================================================
# TOOL 6 → LIMIT TOOL
# =========================================================

limit_tool = Tool(

    name="limit_rows_tool",

    func=limit_rows_tool,

    description=(
        "Limits dataframe rows for testing "
        "or preprocessing."
    )
)


# =========================================================
# TOOL 7 → FIELD MAPPER TOOL
# =========================================================

field_mapping_tool = Tool(

    name="field_mapper_tool",

    func=field_mapper_tool,

    description=(
        "Maps company-specific columns "
        "to standardized master GL schema."
    )
)


# =========================================================
# TOOL 8 → TEXT CLEANER TOOL
# =========================================================

text_cleaner_tool = Tool(

    name="text_cleaner_tool",

    func=clean_dataframe_tool,

    description=(
        "Cleans dataframe values, removes "
        "nulls, trims spaces, and normalizes text."
    )
)


# =========================================================
# TOOL 9 → RELATIONAL MAPPER TOOL
# =========================================================

relation_mapping_tool = Tool(

    name="relation_mapper_tool",

    func=relation_mapper_tool,

    description=(
        "Maps account hierarchy relationships "
        "like account, subclass, class, "
        "country, and region."
    )
)


# =========================================================
# TOOL 10 → FINANCIAL LOGIC TOOL
# =========================================================

financial_rules_tool = Tool(

    name="financial_logic_tool",

    func=financial_logic_tool,

    description=(
        "Applies accounting business rules "
        "for debit-credit classification, "
        "negative-positive amount handling, "
        "and voucher balancing."
    )
)

# =========================================================
# TOOL 11 → VALIDATION ALERT TOOL
# =========================================================

validation_alert_tool = Tool(

    name="validation_alert_tool",

    func=push_validation_alert_tool,

    description=(
        "Pushes DTCD validation alerts "
        "to frontend UI dashboard."
    )
)


# =========================================================
# TOOL 12 → GENERIC FILE READER TOOL
# =========================================================

def read_file_wrapper(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

read_file_tool = Tool(
    name="read_file_tool",
    func=read_file_wrapper,
    description="Reads the content of any generic text file given its path."
)

# =========================================================
# ALL TOOLS LIST
# =========================================================

ALL_TOOLS = [

    email_tool,

    excel_reader_tool,

    limit_tool,

    field_mapping_tool,

    relation_mapping_tool,

    text_cleaner_tool,

    financial_rules_tool,

    llm_tool,

    validator_tool,

    ui_tool,
    
    validation_alert_tool,

    read_file_tool
]
