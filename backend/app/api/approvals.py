from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_roles
from app.db.session import get_db
from app.models import ApprovedTransaction, KpiSnapshot, ManagerComment, PendingUploadRow, Upload, UploadStatus, User, UserRole
from app.schemas import ApprovalRequest, RejectRequest, ReuploadRequest
from app.services.excel_parser import infer_amount, infer_date, infer_number, infer_text
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/{upload_id}/approve")
async def approve_upload(
    upload_id: UUID,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager, UserRole.admin)),
) -> dict:
    upload = await db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if upload.status != UploadStatus.pending:
        raise HTTPException(status_code=409, detail=f"Upload is already {upload.status.value}")

    rows = (await db.execute(select(PendingUploadRow).where(PendingUploadRow.upload_id == upload_id))).scalars().all()
    transactions = []
    approved_amount = 0.0
    cash_collected = 0.0
    for row in rows:
        target_value = infer_number(row.payload, "target_value")
        actual_value = infer_number(row.payload, "actual_value")
        attainment_pct = (actual_value / target_value * 100) if target_value else None
        amount = infer_amount(row.payload)
        approved_amount += float(amount or 0)
        if str(row.payload.get("status", "")).strip().lower() == "successful":
            cash_collected += float(amount or 0)
        transactions.append(
            ApprovedTransaction(
                upload_id=upload.id,
                row_index=row.row_index,
                payload=row.payload,
                amount=amount,
                department=infer_text(row.payload, "department"),
                employee_name=infer_text(row.payload, "employee_name"),
                kpi_name=infer_text(row.payload, "kpi_name"),
                target_value=target_value,
                actual_value=actual_value,
                attainment_pct=attainment_pct,
                transaction_date=infer_date(row.payload, "transaction_date"),
            )
        )
    db.add_all(transactions)
    upload.status = UploadStatus.approved
    upload.approved_by_id = manager.id
    upload.reviewed_at = datetime.now(UTC)
    db.add(ManagerComment(upload_id=upload.id, manager_id=manager.id, decision="approved", comment=request.comment))
    db.add_all(
        [
            KpiSnapshot(
                metric_name="approved_upload_rows",
                metric_value=len(rows),
                metadata_json={"upload_id": str(upload.id), "filename": upload.filename, "manager_id": str(manager.id)},
            ),
            KpiSnapshot(
                metric_name="approved_amount",
                metric_value=approved_amount,
                metadata_json={"upload_id": str(upload.id), "filename": upload.filename, "manager_id": str(manager.id)},
            ),
            KpiSnapshot(
                metric_name="cash_collected",
                metric_value=cash_collected,
                metadata_json={"upload_id": str(upload.id), "filename": upload.filename, "manager_id": str(manager.id)},
            ),
        ]
    )
    await db.commit()

    payload = {"upload_id": upload.id, "status": upload.status.value, "filename": upload.filename}
    await ws_manager.broadcast("uploads", "upload_status", payload)
    await ws_manager.broadcast("uploads", "approval.decision", payload)
    await ws_manager.broadcast("manager", "upload_reviewed", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)
    await ws_manager.broadcast("dashboard", "kpi.update", payload)
    return {"message": "Upload approved", **payload}


@router.post("/{upload_id}/reject")
async def reject_upload(
    upload_id: UUID,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager, UserRole.admin)),
) -> dict:
    upload = await db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if upload.status != UploadStatus.pending:
        raise HTTPException(status_code=409, detail=f"Upload is already {upload.status.value}")

    upload.status = UploadStatus.rejected
    upload.approved_by_id = manager.id
    upload.reviewed_at = datetime.now(UTC)
    db.add(ManagerComment(upload_id=upload.id, manager_id=manager.id, decision="rejected", comment=request.comment))
    await db.commit()

    payload = {"upload_id": upload.id, "status": upload.status.value, "filename": upload.filename}
    await ws_manager.broadcast("uploads", "upload_status", payload)
    await ws_manager.broadcast("uploads", "approval.decision", payload)
    await ws_manager.broadcast("manager", "upload_reviewed", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)
    return {"message": "Upload rejected", **payload}


@router.post("/{upload_id}/request-reupload")
async def request_reupload(
    upload_id: UUID,
    request: ReuploadRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager, UserRole.admin)),
) -> dict:
    upload = await db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if upload.status != UploadStatus.pending:
        raise HTTPException(status_code=409, detail=f"Upload is already {upload.status.value}")

    upload.status = UploadStatus.reupload_requested
    upload.approved_by_id = manager.id
    upload.reviewed_at = datetime.now(UTC)
    db.add(ManagerComment(upload_id=upload.id, manager_id=manager.id, decision="reupload_requested", comment=request.comment))
    await db.commit()

    payload = {"upload_id": upload.id, "status": upload.status.value, "filename": upload.filename, "comment": request.comment}
    await ws_manager.broadcast("uploads", "upload_status", payload)
    await ws_manager.broadcast("uploads", "approval.decision", payload)
    await ws_manager.broadcast("manager", "upload_reviewed", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)
    return {"message": "Re-upload requested", **payload}
