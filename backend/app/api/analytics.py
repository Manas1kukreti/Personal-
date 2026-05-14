from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_roles
from app.db.session import get_db
from app.models import ReviewStatus, Submission, TransactionRow, TransactionStatus, User, UserRole

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/kpis")
async def get_kpis(
    status: ReviewStatus | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> dict:
    submission_filters = []
    if status:
        submission_filters.append(Submission.review_status == status)
    if date_from:
        submission_filters.append(Submission.uploaded_at >= date_from)
    if date_to:
        submission_filters.append(Submission.uploaded_at <= date_to)
    if user.role == UserRole.employee:
        submission_filters.append(Submission.user_id == user.id)
    elif user.role == UserRole.manager:
        submission_filters.append(Submission.user_id.in_(select(User.id).where(User.manager_id == user.id)))

    submission_scope = select(Submission.id).where(*submission_filters)
    total_submissions = await db.scalar(select(func.count()).select_from(Submission).where(*submission_filters))
    approved_submissions = await db.scalar(
        select(func.count()).select_from(Submission).where(*submission_filters, Submission.review_status == ReviewStatus.approved)
    )
    pending_submissions = await db.scalar(
        select(func.count()).select_from(Submission).where(*submission_filters, Submission.review_status == ReviewStatus.pending)
    )
    total_rows = await db.scalar(select(func.count()).select_from(TransactionRow).where(TransactionRow.submission_id.in_(submission_scope)))
    total_revenue = await db.scalar(
        select(func.coalesce(func.sum(TransactionRow.amount), 0))
        .where(TransactionRow.submission_id.in_(submission_scope))
        .where(Submission.review_status == ReviewStatus.approved)
        .join(Submission, TransactionRow.submission_id == Submission.id)
    )

    recent_submissions = (
        await db.execute(select(Submission).where(*submission_filters).order_by(desc(Submission.uploaded_at)).limit(5))
    ).scalars().all()
    latest_submission = await db.scalar(select(Submission).where(*submission_filters).order_by(desc(Submission.uploaded_at)).limit(1))
    latest_rows: list[TransactionRow] = []
    if latest_submission:
        latest_rows = (
            await db.execute(
                select(TransactionRow)
                .where(TransactionRow.submission_id == latest_submission.id)
                .order_by(desc(TransactionRow.transaction_date))
                .limit(10)
            )
        ).scalars().all()

    trend_rows = (
        await db.execute(
            select(func.date_trunc("day", Submission.uploaded_at).label("day"), func.count(Submission.id))
            .where(*submission_filters)
            .group_by("day")
            .order_by("day")
            .limit(30)
        )
    ).all()

    workflow_amounts = {
        "initiated": float(await db.scalar(select(func.coalesce(func.sum(TransactionRow.amount), 0)).where(TransactionRow.submission_id.in_(submission_scope))) or 0),
        "pending": float(await amount_for_status(db, ReviewStatus.pending, submission_filters)),
        "approved": float(await amount_for_status(db, ReviewStatus.approved, submission_filters)),
        "declined": float(await amount_for_status(db, ReviewStatus.declined, submission_filters)),
    }
    approved_cash = float(
        await db.scalar(
            select(func.coalesce(func.sum(TransactionRow.amount), 0))
            .join(Submission, TransactionRow.submission_id == Submission.id)
            .where(*submission_filters, Submission.review_status == ReviewStatus.approved, TransactionRow.status == TransactionStatus.Successful)
        )
        or 0
    )

    latest_chart_by_date: dict[str, float] = {}
    if latest_submission:
        chart_rows = (
            await db.execute(select(TransactionRow).where(TransactionRow.submission_id == latest_submission.id))
        ).scalars().all()
        for row in chart_rows:
            date_key = row.transaction_date.isoformat()
            latest_chart_by_date[date_key] = latest_chart_by_date.get(date_key, 0) + float(row.amount or 0)

    return {
        "totals": {
            "uploads": total_submissions or 0,
            "approved": approved_submissions or 0,
            "pending": pending_submissions or 0,
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
                "id": submission.id,
                "filename": submission.file_name,
                "status": submission.review_status.value,
                "rows": await row_count_for_submission(db, submission.id),
                "created_at": submission.uploaded_at,
            }
            for submission in recent_submissions
        ],
        "latest_upload": {
            "id": latest_submission.id,
            "filename": latest_submission.file_name,
            "status": latest_submission.review_status.value,
            "created_at": latest_submission.uploaded_at,
        } if latest_submission else None,
        "last_transactions": [format_transaction_row(row, latest_submission) for row in latest_rows],
        "transaction_amount_trend": [
            {"date": date, "amount": amount}
            for date, amount in sorted(latest_chart_by_date.items())
        ],
        "upload_trends": [{"day": row[0], "uploads": row[1]} for row in trend_rows],
        "kpi_snapshots": [],
    }


async def amount_for_status(db: AsyncSession, status: ReviewStatus, filters: list) -> float:
    return await db.scalar(
        select(func.coalesce(func.sum(TransactionRow.amount), 0))
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*filters, Submission.review_status == status)
    ) or 0


async def row_count_for_submission(db: AsyncSession, submission_id) -> int:
    return await db.scalar(select(func.count()).select_from(TransactionRow).where(TransactionRow.submission_id == submission_id)) or 0


def format_transaction_row(row: TransactionRow, submission: Submission | None) -> dict:
    return {
        "row_index": row.transaction_id,
        "upload_id": row.submission_id,
        "upload_status": submission.review_status.value if submission else None,
        "uploaded_at": submission.uploaded_at if submission else None,
        "transaction_id": row.transaction_id,
        "transaction_date": row.transaction_date,
        "customer_name": row.customer_name,
        "merchant_name": row.merchant_name,
        "transaction_type": row.transaction_type.value,
        "payment_method": row.payment_method.value,
        "status": row.status.value,
        "amount": float(row.amount or 0),
    }
