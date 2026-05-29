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
from app.models import AuditAction, Review, ReviewStatus, Submission, TransactionRow, User, UserRole
from app.schemas import TransactionRowRead, UploadPreview, UploadSummary, UploadVersionRead
from app.services.audit import log_action
from app.services.email import manager_submission_link, send_email
from app.services.excel_parser import infer_amount, infer_date, infer_text, parse_entry_no, parse_spreadsheet, validate_extension
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/uploads", tags=["uploads"])

GL_COLUMNS = [
    "date",
    "entry_group",
    "entry_line",
    "sub_account",
    "details",
    "account_code",
    "debit_amount",
    "credit_amount",
    "account_class",
    "sub_class",
    "country",
    "region",
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
    count = await db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(Submission.review_status != ReviewStatus.parse_failed)
    )
    submission.sub_id = count

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
        sub_id=submission.sub_id,
        filename=submission.file_name,
        status=submission.review_status.value,
        version_number=submission.version_number,
        parent_submission_id=submission.parent_submission_id,
        total_rows=0,
        total_columns=len(GL_COLUMNS),
        created_at=submission.uploaded_at,
        columns=GL_COLUMNS,
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
    return parsed, [gl_values_from_record(record) for record in parsed["records"]]


async def mark_upload_parse_failed(db: AsyncSession, submission: Submission, detail: Any) -> None:
    await db.refresh(submission)
    submission.review_status = ReviewStatus.parse_failed
    submission.sub_id = None
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
    else:
        stmt = stmt.where(Submission.review_status != ReviewStatus.parse_failed)
    if date_from:
        stmt = stmt.where(Submission.uploaded_at >= date_from)
    if date_to:
        stmt = stmt.where(Submission.uploaded_at <= date_to)
    if user.role == UserRole.employee:
        stmt = stmt.where(Submission.user_id == user.id)
    elif user.role == UserRole.manager:
        stmt = stmt.where(User.manager_id == user.id)

    submissions = (await db.execute(stmt)).all()
    return [
        UploadSummary(
            id=submission.id,
            sub_id=submission.sub_id,
            filename=submission.file_name,
            status=submission.review_status.value,
            version_number=submission.version_number,
            parent_submission_id=submission.parent_submission_id,
            total_rows=row_count,
            total_columns=len(GL_COLUMNS),
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
        await db.execute(
            select(Submission)
            .options(selectinload(Submission.user), selectinload(Submission.review))
            .where(Submission.id == upload_id)
        )
    ).scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    verify_upload_access(submission, user)

    rows = (
        await db.execute(
            select(TransactionRow)
            .where(TransactionRow.submission_id == upload_id)
            .order_by(TransactionRow.date, TransactionRow.entry_group, TransactionRow.entry_line)
            .limit(get_settings().max_preview_rows)
        )
    ).scalars().all()
    row_count = await db.scalar(
        select(func.count()).select_from(TransactionRow).where(TransactionRow.submission_id == upload_id)
    )

    validation = {"valid": True, "schema": "general_ledger", "currency": "INR"}
    if submission.review_status == ReviewStatus.processing:
        validation = {"valid": None, "status": "processing"}
    elif submission.review_status == ReviewStatus.parse_failed:
        validation = {"valid": False, "status": "parse_failed"}

    return UploadPreview(
        upload_id=submission.id,
        sub_id=submission.sub_id,
        filename=submission.file_name,
        status=submission.review_status.value,
        version_number=submission.version_number,
        parent_submission_id=submission.parent_submission_id,
        total_rows=row_count or 0,
        total_columns=len(GL_COLUMNS),
        created_at=submission.uploaded_at,
        reviewed_at=submission.review.reviewed_at if submission.review else None,
        columns=GL_COLUMNS,
        detected_types={},
        validation=validation,
        preview_rows=[gl_row_to_dict(row) for row in rows],
        version_history=await get_version_history(db, submission),
    )


@router.get("/{upload_id}/transactions", response_model=list[TransactionRowRead])
async def get_upload_transactions(
    upload_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> list[TransactionRowRead]:
    submission = (
        await db.execute(
            select(Submission)
            .options(selectinload(Submission.user))
            .where(Submission.id == upload_id)
        )
    ).scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    verify_upload_access(submission, user)

    rows = (
        await db.execute(
            select(TransactionRow)
            .where(TransactionRow.submission_id == upload_id)
            .order_by(TransactionRow.date, TransactionRow.entry_group, TransactionRow.entry_line)
        )
    ).scalars().all()
    return [TransactionRowRead(**gl_row_to_dict(row)) for row in rows]


async def get_version_history(db: AsyncSession, submission: Submission) -> list[UploadVersionRead]:
    root_submission_id = submission.parent_submission_id or submission.id
    versions = (
        await db.execute(
            select(Submission)
            .options(selectinload(Submission.review))
            .where(
                (Submission.id == root_submission_id) | (Submission.parent_submission_id == root_submission_id)
            )
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


def gl_values_from_record(record: dict) -> dict[str, Any]:
    """
    Build a dict of TransactionRow kwargs from a parsed GL record.
    Keys in `record` match the spreadsheet column names (lowercased by excel_parser).
    'class' column maps to account_class (reserved keyword workaround).
    """
    lowered = {str(k).strip().lower(): v for k, v in record.items()}

    raw_entry_no = lowered.get("entry_no")
    if raw_entry_no is None:
        raise HTTPException(status_code=422, detail="Missing required field: entry_no")
    entry_group, entry_line = parse_entry_no(raw_entry_no)

    debit_amount, credit_amount = infer_amount(lowered)

    raw_date = infer_date(lowered, "voucher_date")
    if raw_date is None:
        raise HTTPException(status_code=422, detail="Missing or invalid field: voucher_date")

    return {
        "date": raw_date.date() if hasattr(raw_date, "date") else raw_date,
        "entry_group": entry_group,
        "entry_line": entry_line,
        "sub_account": infer_text(lowered, "sub_account"),
        "details": infer_text(lowered, "details"),
        "account_code": infer_text(lowered, "account_code"),
        "debit_amount": debit_amount,
        "credit_amount": credit_amount,
        # spreadsheet column is 'class'; DB column is 'account_class'
        "account_class": infer_text(lowered, "class"),
        "sub_class": infer_text(lowered, "sub_class"),
        "country": infer_text(lowered, "country"),
        "region": infer_text(lowered, "region"),
    }


def gl_row_to_dict(row: TransactionRow) -> dict:
    """Serialize a TransactionRow ORM object to a JSON-safe dict."""
    return {
        "id": str(row.id),
        "submission_id": str(row.submission_id),
        "date": row.date.isoformat() if row.date else None,
        "entry_group": row.entry_group,
        "entry_line": row.entry_line,
        "sub_account": row.sub_account,
        "details": row.details,
        "account_code": row.account_code,
        "debit_amount": float(row.debit_amount) if row.debit_amount is not None else None,
        "credit_amount": float(row.credit_amount) if row.credit_amount is not None else None,
        "account_class": row.account_class,
        "sub_class": row.sub_class,
        "country": row.country,
        "region": row.region,
    }
