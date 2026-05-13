from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import require_roles
from app.db.session import get_db
from app.models import PendingUploadRow, Upload, User, UserRole
from app.schemas import UploadPreview, UploadSummary
from app.services.excel_parser import parse_spreadsheet, validate_extension
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadPreview)
async def create_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> UploadPreview:
    settings = get_settings()
    try:
        ext = validate_extension(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    await ws_manager.broadcast("uploads", "upload_progress", {"filename": file.filename, "progress": 10})
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File size limit is {settings.max_upload_size_mb} MB")

    upload = Upload(filename=file.filename or "upload", file_type=ext.replace(".", ""), uploaded_by_id=user.id)
    db.add(upload)
    await db.flush()

    path = upload_dir / f"{upload.id}{ext}"
    path.write_bytes(contents)
    await ws_manager.broadcast("uploads", "upload_progress", {"upload_id": upload.id, "progress": 40})

    try:
        parsed = parse_spreadsheet(path, settings.max_preview_rows)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Unable to parse spreadsheet: {exc}") from exc

    upload.source_path = str(path)
    upload.total_rows = parsed["total_rows"]
    upload.total_columns = parsed["total_columns"]
    upload.columns = parsed["columns"]
    upload.detected_types = parsed["detected_types"]
    upload.validation_summary = parsed["validation"]
    upload.preview_rows = parsed["preview_rows"]

    db.add_all(
        PendingUploadRow(upload_id=upload.id, row_index=index, payload=row)
        for index, row in enumerate(parsed["records"], start=1)
    )
    await db.commit()
    await db.refresh(upload)

    payload = {
        "upload_id": upload.id,
        "filename": upload.filename,
        "status": upload.status.value,
        "total_rows": upload.total_rows,
    }
    await ws_manager.broadcast("uploads", "upload_progress", {**payload, "progress": 100})
    await ws_manager.broadcast("uploads", "upload.complete", payload)
    await ws_manager.broadcast("manager", "new_upload", payload)
    await ws_manager.broadcast("manager", "upload.new", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)

    return UploadPreview(
        upload_id=upload.id,
        filename=upload.filename,
        status=upload.status.value,
        total_rows=upload.total_rows,
        total_columns=upload.total_columns,
        columns=upload.columns,
        detected_types=upload.detected_types,
        validation=upload.validation_summary,
        preview_rows=upload.preview_rows,
    )


@router.get("", response_model=list[UploadSummary])
async def list_uploads(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> list[UploadSummary]:
    stmt = select(Upload).options(selectinload(Upload.uploaded_by)).order_by(desc(Upload.created_at)).limit(100)
    if status:
        stmt = stmt.where(Upload.status == status)
    uploads = (await db.execute(stmt)).scalars().all()
    return [
        UploadSummary(
            id=upload.id,
            filename=upload.filename,
            status=upload.status.value,
            total_rows=upload.total_rows,
            total_columns=upload.total_columns,
            uploader_name=upload.uploaded_by.name if upload.uploaded_by else None,
            validation_passed=bool(upload.validation_summary.get("valid", True)),
            created_at=upload.created_at,
        )
        for upload in uploads
    ]


@router.get("/{upload_id}", response_model=UploadPreview)
async def get_upload(
    upload_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> UploadPreview:
    upload = await db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return UploadPreview(
        upload_id=upload.id,
        filename=upload.filename,
        status=upload.status.value,
        total_rows=upload.total_rows,
        total_columns=upload.total_columns,
        columns=upload.columns,
        detected_types=upload.detected_types,
        validation=upload.validation_summary,
        preview_rows=upload.preview_rows,
    )
