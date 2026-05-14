from datetime import date
from pathlib import Path
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import require_roles
from app.db.session import get_db
from app.models import PaymentMethod, Review, ReviewStatus, Submission, TransactionRow, TransactionStatus, TransactionType, User, UserRole
from app.schemas import UploadPreview, UploadSummary
from app.services.email import manager_submission_link, send_email
from app.services.excel_parser import parse_spreadsheet, validate_extension
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/uploads", tags=["uploads"])

TRANSACTION_COLUMNS = [
    "customer_name",
    "account_number",
    "transaction_id",
    "transaction_date",
    "amount",
    "transaction_type",
    "merchant_name",
    "invoice_id",
    "payment_method",
    "status",
]


@router.post("", response_model=UploadPreview)
async def create_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee)),
) -> UploadPreview:
    settings = get_settings()
    try:
        ext = validate_extension(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await ws_manager.broadcast("uploads", "upload_progress", {"filename": file.filename, "progress": 10})
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File size limit is {settings.max_upload_size_mb} MB")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    submission = Submission(
        user_id=user.id,
        file_name=file.filename or "upload",
        file_path="pending",
        file_size_bytes=len(contents),
        original_filename=file.filename or "upload",
    )
    db.add(submission)
    await db.flush()

    path = upload_dir / f"{submission.id}{ext}"
    path.write_bytes(contents)
    submission.file_path = str(path)

    await ws_manager.broadcast("uploads", "upload_progress", {"upload_id": submission.id, "progress": 40})

    try:
        parsed = parse_spreadsheet(path, settings.max_preview_rows)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Unable to parse spreadsheet: {exc}") from exc

    if not parsed["validation"].get("valid", False):
        await db.rollback()
        raise HTTPException(status_code=422, detail=parsed["validation"])

    rows = [transaction_row_from_record(submission.id, record) for record in parsed["records"]]
    db.add_all(rows)
    await db.commit()
    await db.refresh(submission)
    manager = await db.get(User, user.manager_id) if user.manager_id else None

    payload = {
        "upload_id": submission.id,
        "filename": submission.file_name,
        "status": submission.review_status.value,
        "total_rows": len(rows),
    }
    await ws_manager.broadcast("uploads", "upload_progress", {**payload, "progress": 100})
    await ws_manager.broadcast("uploads", "upload.complete", payload)
    await ws_manager.broadcast("manager", "new_upload", payload)
    await ws_manager.broadcast("manager", "upload.new", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)
    if manager:
        await send_email(
            manager.email,
            "New upload pending review",
            (
                f"Hello {manager.full_name},\n\n"
                f"{user.full_name} submitted {submission.file_name} for review.\n\n"
                f"Open it here: {manager_submission_link(submission.id)}"
            ),
        )

    return UploadPreview(
        upload_id=submission.id,
        filename=submission.file_name,
        status=submission.review_status.value,
        total_rows=len(rows),
        total_columns=len(TRANSACTION_COLUMNS),
        created_at=submission.uploaded_at,
        columns=TRANSACTION_COLUMNS,
        detected_types=parsed["detected_types"],
        validation=parsed["validation"],
        preview_rows=[transaction_row_to_dict(row) for row in rows[: settings.max_preview_rows]],
    )


@router.get("", response_model=list[UploadSummary])
async def list_uploads(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> list[UploadSummary]:
    stmt = (
        select(Submission, func.count(TransactionRow.id).label("row_count"))
        .join(User, User.id == Submission.user_id)
        .join(Review, Review.submission_id == Submission.id, isouter=True)
        .join(TransactionRow, TransactionRow.submission_id == Submission.id, isouter=True)
        .options(selectinload(Submission.user), selectinload(Submission.review))
        .group_by(Submission.id, Review.reviewed_at)
        .order_by(desc(Submission.uploaded_at))
        .limit(100)
    )
    if status:
        stmt = stmt.where(Submission.review_status == ReviewStatus(status))
    if user.role == UserRole.employee:
        stmt = stmt.where(Submission.user_id == user.id)
    elif user.role == UserRole.manager:
        stmt = stmt.where(User.manager_id == user.id)

    submissions = (await db.execute(stmt)).all()
    return [
        UploadSummary(
            id=submission.id,
            filename=submission.file_name,
            status=submission.review_status.value,
            total_rows=row_count,
            total_columns=len(TRANSACTION_COLUMNS),
            uploader_name=submission.user.full_name if submission.user else None,
            validation_passed=True,
            created_at=submission.uploaded_at,
            reviewed_at=submission.review.reviewed_at if submission.review else None,
        )
        for submission, row_count in submissions
    ]


@router.get("/{upload_id}", response_model=UploadPreview)
async def get_upload(
    upload_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> UploadPreview:
    submission = (
        await db.execute(select(Submission).options(selectinload(Submission.user), selectinload(Submission.review)).where(Submission.id == upload_id))
    ).scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    verify_upload_access(submission, user)

    rows = (
        await db.execute(
            select(TransactionRow)
            .where(TransactionRow.submission_id == upload_id)
            .order_by(TransactionRow.transaction_date, TransactionRow.transaction_id)
            .limit(get_settings().max_preview_rows)
        )
    ).scalars().all()
    row_count = await db.scalar(select(func.count()).select_from(TransactionRow).where(TransactionRow.submission_id == upload_id))

    return UploadPreview(
        upload_id=submission.id,
        filename=submission.file_name,
        status=submission.review_status.value,
        total_rows=row_count or 0,
        total_columns=len(TRANSACTION_COLUMNS),
        created_at=submission.uploaded_at,
        reviewed_at=submission.review.reviewed_at if submission.review else None,
        columns=TRANSACTION_COLUMNS,
        detected_types={},
        validation={"valid": True, "schema": "financial_transactions", "currency": "INR"},
        preview_rows=[transaction_row_to_dict(row) for row in rows],
    )


def verify_upload_access(submission: Submission, user: User) -> None:
    if user.role == UserRole.admin:
        return
    if user.role == UserRole.employee and submission.user_id == user.id:
        return
    if user.role == UserRole.manager and submission.user and submission.user.manager_id == user.id:
        return
    raise HTTPException(status_code=404, detail="Submission not found")


def transaction_row_from_record(submission_id: UUID, record: dict) -> TransactionRow:
    lowered = {str(key).strip().lower(): value for key, value in record.items()}
    return TransactionRow(
        submission_id=submission_id,
        customer_name=required_text(lowered, "customer_name"),
        account_number=required_text(lowered, "account_number"),
        transaction_id=required_text(lowered, "transaction_id"),
        transaction_date=required_date(lowered, "transaction_date"),
        amount=float(lowered["amount"]),
        transaction_type=TransactionType(canonical_value(lowered, "transaction_type", TransactionType)),
        merchant_name=required_text(lowered, "merchant_name"),
        invoice_id=required_text(lowered, "invoice_id"),
        payment_method=PaymentMethod(canonical_value(lowered, "payment_method", PaymentMethod)),
        status=TransactionStatus(canonical_value(lowered, "status", TransactionStatus)),
    )


def transaction_row_to_dict(row: TransactionRow) -> dict:
    return {
        "id": row.id,
        "submission_id": row.submission_id,
        "customer_name": row.customer_name,
        "account_number": row.account_number,
        "transaction_id": row.transaction_id,
        "transaction_date": row.transaction_date.isoformat(),
        "amount": float(row.amount),
        "transaction_type": row.transaction_type.value,
        "merchant_name": row.merchant_name,
        "invoice_id": row.invoice_id,
        "payment_method": row.payment_method.value,
        "status": row.status.value,
        "currency": "INR",
    }


def required_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if value is None or str(value).strip() == "":
        raise HTTPException(status_code=422, detail=f"Missing required field: {key}")
    return str(value).strip()


def required_date(payload: dict, key: str) -> date:
    parsed = pd.to_datetime(payload.get(key), errors="coerce")
    if pd.isna(parsed):
        raise HTTPException(status_code=422, detail=f"Invalid date field: {key}")
    return parsed.date()


def canonical_value(payload: dict, key: str, enum_type: type) -> str:
    value = required_text(payload, key)
    normalized_value = normalize_enum_text(value)
    for option in enum_type:
        if normalize_enum_text(option.value) == normalized_value or normalize_enum_text(option.name) == normalized_value:
            return option.value
    raise HTTPException(status_code=422, detail=f"Invalid value for {key}")


def normalize_enum_text(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())
