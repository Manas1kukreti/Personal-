from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_EXTENSIONS = {".xlsx", ".csv"}
REQUIRED_FINANCIAL_COLUMNS = {
    "customer_name": "string",
    "account_number": "string",
    "transaction_id": "string",
    "transaction_date": "date",
    "amount": "number",
    "currency": "string",
    "transaction_type": "string",
    "merchant_name": "string",
    "invoice_id": "string",
    "payment_method": "string",
    "status": "string",
}
OPTIONAL_FINANCIAL_COLUMNS: dict[str, str] = {}

VALID_TRANSACTION_TYPES = {"payment", "debit", "credit", "refund", "transfer"}
VALID_PAYMENT_STATUSES = {"initiated", "pending", "failed", "successful"}


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
    frame.columns = [str(column).strip() for column in frame.columns]
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
    row_errors: list[dict[str, Any]] = []

    if frame.empty:
        row_errors.append({"row": 0, "field": "file", "message": "File contains no data rows"})

    for expected, expected_type in {**REQUIRED_FINANCIAL_COLUMNS, **OPTIONAL_FINANCIAL_COLUMNS}.items():
        source_column = normalized_columns.get(expected)
        if source_column is None:
            continue

        series = frame[source_column]
        if expected in REQUIRED_FINANCIAL_COLUMNS:
            invalid = series.isna() | (series.astype(str).str.strip() == "")
            row_errors.extend(
                {"row": int(index) + 2, "field": expected, "message": "Required value is missing"}
                for index in series[invalid].index[:25]
            )

        if expected_type == "number":
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = series.notna() & numeric.isna()
            row_errors.extend(
                {"row": int(index) + 2, "field": expected, "message": "Must be numeric"}
                for index in series[invalid].index[:25]
            )
            if expected == "amount":
                non_positive = numeric.notna() & (numeric <= 0)
                row_errors.extend(
                    {"row": int(index) + 2, "field": expected, "message": "Must be greater than zero"}
                    for index in series[non_positive].index[:25]
                )
        elif expected_type == "date":
            invalid = series.notna() & pd.to_datetime(series, errors="coerce").isna()
            row_errors.extend(
                {"row": int(index) + 2, "field": expected, "message": "Must be a valid date"}
                for index in series[invalid].index[:25]
            )

    if "transaction_type" in normalized_columns:
        series = frame[normalized_columns["transaction_type"]]
        invalid_type = series.notna() & ~series.astype(str).str.strip().str.lower().isin(VALID_TRANSACTION_TYPES)
        row_errors.extend(
            {"row": int(index) + 2, "field": "transaction_type", "message": "Must be Payment, Debit, Credit, Refund, or Transfer"}
            for index in series[invalid_type].index[:25]
        )

    if "status" in normalized_columns:
        series = frame[normalized_columns["status"]]
        invalid_status = series.notna() & ~series.astype(str).str.strip().str.lower().isin(VALID_PAYMENT_STATUSES)
        row_errors.extend(
            {"row": int(index) + 2, "field": "status", "message": "Must be Initiated, Pending, Failed, or Successful"}
            for index in series[invalid_status].index[:25]
        )

    return {
        "schema": "financial_transactions",
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


def infer_amount(payload: dict) -> float | None:
    candidates = ("amount", "revenue", "total", "price", "value", "sales")
    lowered = {str(key).lower(): value for key, value in payload.items()}
    for key in candidates:
        value = lowered.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


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
