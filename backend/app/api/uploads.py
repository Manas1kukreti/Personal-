import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import require_roles
from app.db.session import AsyncSessionLocal, get_db
from app.models import AuditAction, PaymentMethod, Review, ReviewStatus, Submission, TransactionRow, TransactionStatus, TransactionType, User, UserRole
from app.schemas import UploadPreview, UploadSummary, UploadVersionRead
from app.services.audit import log_action
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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee)),
) -> UploadPreview:
    return await save_upload(file=file, db=db, user=user, background_tasks=background_tasks)


@router.post("/{submission_id}/reupload", response_model=UploadPreview)
async def reupload_submission(
    submission_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee)),
) -> UploadPreview:
    original = (
        await db.execute(select(Submission).where(Submission.id == submission_id))
    ).scalar_one_or_none()
    if not original or original.user_id != user.id:
        raise HTTPException(status_code=404, detail="Submission not found")
    if original.review_status != ReviewStatus.reupload_requested:
        raise HTTPException(status_code=409, detail="Re-upload is only available when requested by a manager")
    root_submission_id = original.parent_submission_id or original.id
    latest_version = (
        await db.scalar(
            select(func.max(Submission.version_number)).where(
                (Submission.id == root_submission_id) | (Submission.parent_submission_id == root_submission_id)
            )
        )
        or original.version_number
    )
    if original.version_number < latest_version:
        raise HTTPException(status_code=409, detail="A newer version has already been submitted")
    return await save_upload(file=file, db=db, user=user, background_tasks=background_tasks, parent_submission=original)


async def save_upload(
    *,
    file: UploadFile,
    db: AsyncSession,
    user: User,
    background_tasks: BackgroundTasks,
    parent_submission: Submission | None = None,
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

    root_submission_id = None
    version_number = 1
    if parent_submission:
        root_submission_id = parent_submission.parent_submission_id or parent_submission.id
        version_number = (
            await db.scalar(
                select(func.max(Submission.version_number)).where(
                    (Submission.id == root_submission_id) | (Submission.parent_submission_id == root_submission_id)
                )
            )
            or parent_submission.version_number
            or 1
        ) + 1

    submission = Submission(
        user_id=user.id,
        file_name=file.filename or "upload",
        file_path="pending",
        file_size_bytes=len(contents),
        original_filename=file.filename or "upload",
        version_number=version_number,
        parent_submission_id=root_submission_id,
        review_status=ReviewStatus.processing,
    )
    db.add(submission)
    await db.flush()

    path = upload_dir / f"{submission.id}{ext}"
    path.write_bytes(contents)
    submission.file_path = str(path)
    await db.commit()
    await db.refresh(submission)

    payload = {
        "upload_id": submission.id,
        "filename": submission.file_name,
        "status": submission.review_status.value,
        "total_rows": 0,
    }
    await ws_manager.broadcast("uploads", "upload_progress", {**payload, "progress": 40})
    await ws_manager.broadcast("uploads", "upload.processing", payload)
    await ws_manager.broadcast("uploads", "upload_status", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)
    background_tasks.add_task(
        process_upload_file,
        submission.id,
        user.id,
        path,
        settings.max_preview_rows,
        AuditAction.reupload_submitted if parent_submission else AuditAction.upload_created,
    )

    return UploadPreview(
        upload_id=submission.id,
        filename=submission.file_name,
        status=submission.review_status.value,
        version_number=submission.version_number,
        parent_submission_id=submission.parent_submission_id,
        total_rows=0,
        total_columns=len(TRANSACTION_COLUMNS),
        created_at=submission.uploaded_at,
        columns=TRANSACTION_COLUMNS,
        detected_types={},
        validation={"valid": None, "status": "processing"},
        preview_rows=[],
        version_history=await get_version_history(db, submission),
    )


async def process_upload_file(
    submission_id: UUID,
    user_id: UUID,
    path: Path,
    max_preview_rows: int,
    audit_action: AuditAction,
) -> None:
    async with AsyncSessionLocal() as db:
        submission = (
            await db.execute(
                select(Submission)
                .options(selectinload(Submission.user))
                .where(Submission.id == submission_id)
            )
        ).scalar_one_or_none()
        user = await db.get(User, user_id)
        if not submission or not user:
            return

        try:
            parsed, row_values = await asyncio.to_thread(parse_transaction_records, path, max_preview_rows)
        except Exception as exc:
            await db.rollback()
            detail = exc.detail if isinstance(exc, HTTPException) else f"Unable to parse spreadsheet: {exc}"
            await mark_upload_parse_failed(db, submission, detail)
            return

        if not parsed["validation"].get("valid", False):
            await mark_upload_parse_failed(db, submission, parsed["validation"])
            return

        try:
            db.add_all(TransactionRow(submission_id=submission.id, **values) for values in row_values)
            submission.review_status = ReviewStatus.pending
            await db.commit()
            await db.refresh(submission)
        except Exception as exc:
            await db.rollback()
            detail = exc.detail if isinstance(exc, HTTPException) else f"Unable to save parsed spreadsheet: {exc}"
            await mark_upload_parse_failed(db, submission, detail)
            return

        try:
            await log_action(
                db,
                user,
                audit_action,
                target_id=submission.id,
                target_label=submission.file_name,
                detail=f"v{submission.version_number}",
            )
        except Exception:
            await db.rollback()

        await broadcast_upload_complete(db, submission, user, len(row_values))


def parse_transaction_records(path: Path, max_preview_rows: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    parsed = parse_spreadsheet(path, max_preview_rows)
    if not parsed["validation"].get("valid", False):
        return parsed, []
    return parsed, [transaction_values_from_record(record) for record in parsed["records"]]


async def mark_upload_parse_failed(db: AsyncSession, submission: Submission, detail: Any) -> None:
    await db.refresh(submission)
    submission.review_status = ReviewStatus.parse_failed
    await db.commit()
    payload = {
        "upload_id": submission.id,
        "filename": submission.file_name,
        "status": submission.review_status.value,
        "error": detail,
    }
    await ws_manager.broadcast("uploads", "upload_progress", {**payload, "progress": 100})
    await ws_manager.broadcast("uploads", "upload.failed", payload)
    await ws_manager.broadcast("uploads", "upload_status", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)


async def broadcast_upload_complete(db: AsyncSession, submission: Submission, user: User, total_rows: int) -> None:
    manager = await db.get(User, user.manager_id) if user.manager_id else None
    payload = {
        "upload_id": submission.id,
        "filename": submission.file_name,
        "status": submission.review_status.value,
        "total_rows": total_rows,
    }
    await ws_manager.broadcast("uploads", "upload_progress", {**payload, "progress": 100})
    await ws_manager.broadcast("uploads", "upload.complete", payload)
    await ws_manager.broadcast("uploads", "upload_status", payload)
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
                f"Open it here: {manager_submission_link(submission.id, manager.id)}"
            ),
        )


@router.get("", response_model=list[UploadSummary])
async def list_uploads(
    status: str | None = None,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
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
    if date_from or date_to:
        transaction_date_scope = select(TransactionRow.submission_id)
        if date_from:
            transaction_date_scope = transaction_date_scope.where(TransactionRow.transaction_date >= date_from.date())
        if date_to:
            transaction_date_scope = transaction_date_scope.where(TransactionRow.transaction_date <= date_to.date())
        stmt = stmt.where(Submission.id.in_(transaction_date_scope.distinct()))
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
            version_number=submission.version_number,
            parent_submission_id=submission.parent_submission_id,
            total_rows=row_count,
            total_columns=len(TRANSACTION_COLUMNS),
            uploader_name=submission.user.full_name if submission.user else None,
            validation_passed=submission.review_status != ReviewStatus.parse_failed,
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

    validation = {"valid": True, "schema": "financial_transactions", "currency": "INR"}
    if submission.review_status == ReviewStatus.processing:
        validation = {"valid": None, "status": "processing"}
    elif submission.review_status == ReviewStatus.parse_failed:
        validation = {"valid": False, "status": "parse_failed"}

    return UploadPreview(
        upload_id=submission.id,
        filename=submission.file_name,
        status=submission.review_status.value,
        version_number=submission.version_number,
        parent_submission_id=submission.parent_submission_id,
        total_rows=row_count or 0,
        total_columns=len(TRANSACTION_COLUMNS),
        created_at=submission.uploaded_at,
        reviewed_at=submission.review.reviewed_at if submission.review else None,
        columns=TRANSACTION_COLUMNS,
        detected_types={},
        validation=validation,
        preview_rows=[transaction_row_to_dict(row) for row in rows],
        version_history=await get_version_history(db, submission),
    )


async def get_version_history(db: AsyncSession, submission: Submission) -> list[UploadVersionRead]:
    root_submission_id = submission.parent_submission_id or submission.id
    versions = (
        await db.execute(
            select(Submission)
            .options(selectinload(Submission.review))
            .where((Submission.id == root_submission_id) | (Submission.parent_submission_id == root_submission_id))
            .order_by(Submission.version_number)
        )
    ).scalars().all()
    return [
        UploadVersionRead(
            id=version.id,
            filename=version.file_name,
            status=version.review_status.value,
            version_number=version.version_number,
            created_at=version.uploaded_at,
            reviewed_at=version.review.reviewed_at if version.review else None,
        )
        for version in versions
    ]


def verify_upload_access(submission: Submission, user: User) -> None:
    if user.role == UserRole.admin:
        return
    if user.role == UserRole.employee and submission.user_id == user.id:
        return
    if user.role == UserRole.manager and submission.user and submission.user.manager_id == user.id:
        return
    raise HTTPException(status_code=404, detail="Submission not found")


def transaction_row_from_record(submission_id: UUID, record: dict) -> TransactionRow:
    return TransactionRow(submission_id=submission_id, **transaction_values_from_record(record))


def transaction_values_from_record(record: dict) -> dict[str, Any]:
    lowered = {str(key).strip().lower(): value for key, value in record.items()}
    return {
        "customer_name": required_text(lowered, "customer_name"),
        "account_number": required_text(lowered, "account_number"),
        "transaction_id": required_text(lowered, "transaction_id"),
        "transaction_date": required_date(lowered, "transaction_date"),
        "amount": float(lowered["amount"]),
        "transaction_type": TransactionType(canonical_value(lowered, "transaction_type", TransactionType)),
        "merchant_name": required_text(lowered, "merchant_name"),
        "invoice_id": required_text(lowered, "invoice_id"),
        "payment_method": PaymentMethod(canonical_value(lowered, "payment_method", PaymentMethod)),
        "status": TransactionStatus(canonical_value(lowered, "status", TransactionStatus)),
    }


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
