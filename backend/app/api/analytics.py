from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_roles
from app.db.session import get_db
from app.models import ApprovedTransaction, KpiSnapshot, PendingUploadRow, Upload, UploadStatus, User, UserRole
from app.services.excel_parser import infer_amount

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/kpis")
async def get_kpis(
    status: UploadStatus | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> dict:
    upload_filters = []
    if status:
        upload_filters.append(Upload.status == status)
    if date_from:
        upload_filters.append(Upload.created_at >= date_from)
    if date_to:
        upload_filters.append(Upload.created_at <= date_to)

    upload_scope = select(Upload.id).where(*upload_filters)
    total_uploads = await db.scalar(select(func.count()).select_from(Upload).where(*upload_filters))
    approved_uploads = await db.scalar(
        select(func.count()).select_from(Upload).where(*upload_filters, Upload.status == UploadStatus.approved)
    )
    pending_uploads = await db.scalar(
        select(func.count()).select_from(Upload).where(*upload_filters, Upload.status == UploadStatus.pending)
    )
    total_rows = await db.scalar(select(func.coalesce(func.sum(Upload.total_rows), 0)).where(*upload_filters))
    total_revenue = await db.scalar(
        select(func.coalesce(func.sum(ApprovedTransaction.amount), 0)).where(ApprovedTransaction.upload_id.in_(upload_scope))
    )

    recent_uploads = (
        await db.execute(select(Upload).where(*upload_filters).order_by(desc(Upload.created_at)).limit(5))
    ).scalars().all()
    approved_transactions = (
        await db.execute(select(ApprovedTransaction).where(ApprovedTransaction.upload_id.in_(upload_scope)))
    ).scalars().all()
    latest_upload = await db.scalar(select(Upload).where(*upload_filters).order_by(desc(Upload.created_at)).limit(1))
    latest_rows: list[PendingUploadRow] = []
    if latest_upload:
        latest_rows = (
            await db.execute(
                select(PendingUploadRow)
                .where(PendingUploadRow.upload_id == latest_upload.id)
                .order_by(desc(PendingUploadRow.row_index))
                .limit(10)
            )
        ).scalars().all()
    trend_rows = (
        await db.execute(
            select(func.date_trunc("day", Upload.created_at).label("day"), func.count(Upload.id))
            .where(*upload_filters)
            .group_by("day")
            .order_by("day")
            .limit(30)
        )
    ).all()
    staged_rows = (
        await db.execute(
            select(PendingUploadRow, Upload.status)
            .join(Upload, PendingUploadRow.upload_id == Upload.id)
            .where(*upload_filters)
        )
    ).all()
    snapshots = (
        await db.execute(select(KpiSnapshot).order_by(desc(KpiSnapshot.captured_at)).limit(12))
    ).scalars().all()

    workflow_amounts = {
        "initiated": 0.0,
        "pending": 0.0,
        "approved": 0.0,
        "declined": 0.0,
    }
    for row, upload_status in staged_rows:
        amount = infer_amount(row.payload) or 0
        workflow_amounts["initiated"] += amount
        if upload_status == UploadStatus.pending:
            workflow_amounts["pending"] += amount
        elif upload_status == UploadStatus.approved:
            workflow_amounts["approved"] += amount
        elif upload_status == UploadStatus.rejected:
            workflow_amounts["declined"] += amount

    approved_cash = 0.0
    for txn in approved_transactions:
        transaction_status = str(txn.payload.get("status", "")).strip().lower()
        if transaction_status == "successful":
            approved_cash += float(txn.amount or 0)

    latest_chart_by_date: dict[str, float] = {}
    if latest_upload:
        chart_rows = (
            await db.execute(
                select(PendingUploadRow).where(PendingUploadRow.upload_id == latest_upload.id)
            )
        ).scalars().all()
        for row in chart_rows:
            raw_date = row.payload.get("transaction_date")
            if not raw_date:
                continue
            date_key = str(raw_date)[:10]
            latest_chart_by_date[date_key] = latest_chart_by_date.get(date_key, 0) + (infer_amount(row.payload) or 0)

    return {
        "totals": {
            "uploads": total_uploads or 0,
            "approved": approved_uploads or 0,
            "pending": pending_uploads or 0,
            "rows": int(total_rows or 0),
            "revenue": float(total_revenue or 0),
            "cash": approved_cash,
            "transaction_initiated_amount": workflow_amounts["initiated"],
            "pending_amount": workflow_amounts["pending"],
            "approved_amount": workflow_amounts["approved"],
            "declined_amount": workflow_amounts["declined"],
        },
        "workflow_amounts": workflow_amounts,
        "recent_uploads": [
            {
                "id": upload.id,
                "filename": upload.filename,
                "status": upload.status.value,
                "rows": upload.total_rows,
                "created_at": upload.created_at,
            }
            for upload in recent_uploads
        ],
        "latest_upload": {
            "id": latest_upload.id,
            "filename": latest_upload.filename,
            "status": latest_upload.status.value,
            "created_at": latest_upload.created_at,
        } if latest_upload else None,
        "last_transactions": [format_transaction_row(row, latest_upload) for row in latest_rows],
        "transaction_amount_trend": [
            {"date": date, "amount": amount}
            for date, amount in sorted(latest_chart_by_date.items())
        ],
        "upload_trends": [{"day": row[0], "uploads": row[1]} for row in trend_rows],
        "kpi_snapshots": [
            {
                "metric_name": snapshot.metric_name,
                "metric_value": float(snapshot.metric_value),
                "metadata": snapshot.metadata_json,
                "captured_at": snapshot.captured_at,
            }
            for snapshot in snapshots
        ],
    }


def format_transaction_row(row: PendingUploadRow, upload: Upload | None) -> dict:
    payload = row.payload
    return {
        "row_index": row.row_index,
        "upload_id": row.upload_id,
        "upload_status": upload.status.value if upload else None,
        "uploaded_at": upload.created_at if upload else None,
        "transaction_id": payload.get("transaction_id"),
        "transaction_date": payload.get("transaction_date"),
        "customer_name": payload.get("customer_name"),
        "merchant_name": payload.get("merchant_name"),
        "transaction_type": payload.get("transaction_type"),
        "payment_method": payload.get("payment_method"),
        "status": payload.get("status"),
        "amount": infer_amount(payload) or 0,
    }
