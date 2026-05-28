from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_EXTENSIONS = {".xlsx", ".csv"}
REQUIRED_FINANCIAL_COLUMNS = {
    "voucher_date": "date",
    "entry_no": "string",      # parsed into entry_group + entry_line
    "sub_account": "string",
    "details": "string",
    "account_code": "string",
    "class": "string",         # mapped to account_class in DB
    "sub_class": "string",
    "country": "string",
    "region": "string",
}
OPTIONAL_FINANCIAL_COLUMNS: dict[str, str] = {}

# debit_amount and credit_amount are not in REQUIRED because one side
# is always null — they get their own column-presence + row-level checks
AMOUNT_COLUMNS = ["debit_amount", "credit_amount"]


def validate_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .xlsx and .csv files are supported")
    return ext


def parse_spreadsheet(path: Path, max_preview_rows: int) -> dict[str, Any]:
    ext = validate_extension(path.name)
    if ext == ".csv":
        frame = pd.read_csv(path)
    else:
        frame = pd.read_excel(path, engine="openpyxl")

    frame = frame.dropna(how="all")
    COLUMN_ALIASES = {
        "date": "voucher_date",
        "entry no": "entry_no",
        "entry_number": "entry_no",
        "sub account": "sub_account",
        "ledger_name": "sub_account",
        "particulars": "details",
        "account class": "class",
        "account_class": "class",
        "account subclass": "sub_class",
        "account_subclass": "sub_class",
        "debit": "debit_amount",
        "credit": "credit_amount",
        "debit amount": "debit_amount",
        "credit amount": "credit_amount",
        "account code": "account_code",
    }
    frame.columns = [
        COLUMN_ALIASES.get(str(col).strip().lower(), str(col).strip().lower())
        for col in frame.columns
    ]
    frame = frame.where(pd.notnull(frame), None)

    detected_types = infer_detected_types(frame)
    validation = validate_financial_schema(frame)
    normalized = frame.copy()
    for column in normalized.columns:
        normalized[column] = normalized[column].map(normalize_cell)

    records = normalized.to_dict(orient="records")
    return {
        "columns": list(frame.columns),
        "total_rows": len(records),
        "total_columns": len(frame.columns),
        "detected_types": detected_types,
        "validation": validation,
        "preview_rows": records[:max_preview_rows],
        "records": records,
    }


def infer_detected_types(frame: pd.DataFrame) -> dict[str, str]:
    detected: dict[str, str] = {}
    for column in frame.columns:
        series = frame[column].dropna()
        if series.empty:
            detected[column] = "empty"
        elif pd.api.types.is_numeric_dtype(series):
            detected[column] = "number"
        elif pd.api.types.is_datetime64_any_dtype(series):
            detected[column] = "date"
        else:
            date_ratio = pd.to_datetime(series, errors="coerce").notna().mean()
            numeric_ratio = pd.to_numeric(series, errors="coerce").notna().mean()
            if date_ratio >= 0.9:
                detected[column] = "date"
            elif numeric_ratio >= 0.9:
                detected[column] = "number"
            else:
                detected[column] = "string"
    return detected


def validate_financial_schema(frame: pd.DataFrame) -> dict[str, Any]:
    normalized_columns = {str(column).strip().lower(): column for column in frame.columns}
    missing = [column for column in REQUIRED_FINANCIAL_COLUMNS if column not in normalized_columns]

    # Also check that both amount columns exist as columns in the file
    for amount_col in AMOUNT_COLUMNS:
        if amount_col not in normalized_columns:
            missing.append(amount_col)

    row_errors: list[dict[str, Any]] = []

    if frame.empty:
        row_errors.append({"row": 0, "field": "file", "message": "File contains no data rows"})

    # Required non-null text/date fields
    for expected, expected_type in REQUIRED_FINANCIAL_COLUMNS.items():
        source_column = normalized_columns.get(expected)
        if source_column is None:
            continue

        series = frame[source_column]
        invalid = series.isna() | (series.astype(str).str.strip() == "")
        row_errors.extend(
            {"row": int(index) + 2, "field": expected, "message": "Required value is missing"}
            for index in series[invalid].index[:25]
        )

        if expected_type == "date":
            invalid_date = series.notna() & pd.to_datetime(series, errors="coerce").isna()
            row_errors.extend(
                {"row": int(index) + 2, "field": expected, "message": "Must be a valid date"}
                for index in series[invalid_date].index[:25]
            )

    # entry_no must be parseable as two integers separated by a dot e.g. "1.1"
    if "entry_no" in normalized_columns:
        series = frame[normalized_columns["entry_no"]]
        for index, value in series.items():
            if value is None or pd.isna(value):
                continue
            parts = str(value).strip().split(".")
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                row_errors.append({
                    "row": int(index) + 2,
                    "field": "entry_no",
                    "message": f"Must be in format 'N.N' (e.g. 1.1, 3.2), got '{value}'"
                })
                if len(row_errors) >= 100:
                    break

    # Amount columns — numeric check and at least one must be filled per row
    debit_col = normalized_columns.get("debit_amount")
    credit_col = normalized_columns.get("credit_amount")

    if debit_col and credit_col:
        debit_series = pd.to_numeric(frame[debit_col], errors="coerce")
        credit_series = pd.to_numeric(frame[credit_col], errors="coerce")

        # Both null on the same row is invalid
        both_null = frame[debit_col].isna() & frame[credit_col].isna()
        row_errors.extend(
            {
                "row": int(index) + 2,
                "field": "debit_amount/credit_amount",
                "message": "Each row must have at least one of debit_amount or credit_amount",
            }
            for index in frame[both_null].index[:25]
        )

        # Both filled on the same row is invalid (standard double-entry: one side per leg)
        both_filled = frame[debit_col].notna() & frame[credit_col].notna()
        row_errors.extend(
            {
                "row": int(index) + 2,
                "field": "debit_amount/credit_amount",
                "message": "Each row must have only one of debit_amount or credit_amount, not both",
            }
            for index in frame[both_filled].index[:25]
        )

        # Whichever is filled must be numeric and > 0
        for col_name, numeric in [
            ("debit_amount", debit_series),
            ("credit_amount", credit_series),
        ]:
            source = normalized_columns.get(col_name)
            if source is None:
                continue
            non_numeric = frame[source].notna() & numeric.isna()
            row_errors.extend(
                {"row": int(index) + 2, "field": col_name, "message": "Must be numeric"}
                for index in frame[non_numeric].index[:25]
            )
            non_positive = numeric.notna() & (numeric <= 0)
            row_errors.extend(
                {"row": int(index) + 2, "field": col_name, "message": "Must be greater than zero"}
                for index in frame[non_positive].index[:25]
            )

        
            

    return {
        "schema": "general_ledger",
        "required_columns": REQUIRED_FINANCIAL_COLUMNS,
        "optional_columns": OPTIONAL_FINANCIAL_COLUMNS,
        "missing_columns": missing,
        "row_errors": row_errors[:100],
        "valid": not missing and not row_errors,
    }


def normalize_cell(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def normalize_enum_text(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def infer_amount(payload: dict) -> tuple[float | None, float | None]:
    """Returns (debit_amount, credit_amount) from a parsed row dict."""
    lowered = {str(key).lower(): value for key, value in payload.items()}

    def to_float(val) -> float | None:
        if val is None:
            return None
        try:
            result = float(val)
            return result if result > 0 else None
        except (TypeError, ValueError):
            return None

    return to_float(lowered.get("debit_amount")), to_float(lowered.get("credit_amount"))


def parse_entry_no(entry_no: Any) -> tuple[int, int]:
    """Splits '3.2' into (3, 2). Assumes entry_no already passed validation."""
    parts = str(entry_no).strip().split(".")
    return int(parts[0]), int(parts[1])


def infer_number(payload: dict, key: str) -> float | None:
    value = {str(name).lower(): item for name, item in payload.items()}.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_text(payload: dict, key: str) -> str | None:
    value = {str(name).lower(): item for name, item in payload.items()}.get(key)
    if value is None:
        return None
    return str(value)


def infer_date(payload: dict, key: str):
    value = {str(name).lower(): item for name, item in payload.items()}.get(key)
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()