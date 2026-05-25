from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_roles
from app.db.session import get_db
from app.models import Review, ReviewStatus, Submission, SubmissionComment, TransactionRow, TransactionStatus, User, UserRole

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/kpis")
async def get_kpis(
    status: TransactionStatus | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> dict:
    role_filters = []
    if user.role == UserRole.employee:
        role_filters.append(Submission.user_id == user.id)
    elif user.role == UserRole.manager:
        role_filters.append(Submission.user_id.in_(select(User.id).where(User.manager_id == user.id)))

    transaction_filters = transaction_date_filters(date_from, date_to)
    if status:
        transaction_filters.append(TransactionRow.status == status)

    transaction_scope = (
        select(TransactionRow)
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*role_filters, *transaction_filters)
    )
    transaction_scope_subquery = transaction_scope.subquery()
    scoped_submission_ids = select(transaction_scope_subquery.c.submission_id).distinct()

    total_transactions = await db.scalar(select(func.count()).select_from(transaction_scope_subquery))
    initiated_transactions = total_transactions or 0
    pending_transactions = await transaction_count_for_status(db, TransactionStatus.Pending, role_filters, transaction_filters)
    successful_transactions = await transaction_count_for_status(db, TransactionStatus.Successful, role_filters, transaction_filters)
    failed_transactions = await transaction_count_for_status(db, TransactionStatus.Failed, role_filters, transaction_filters)
    reviewed_transactions = successful_transactions + failed_transactions
    approval_rate = successful_transactions / reviewed_transactions if reviewed_transactions else 0
    average_review_seconds = await db.scalar(
        select(func.avg(func.extract("epoch", Review.reviewed_at - Submission.uploaded_at)))
        .select_from(Submission)
        .join(Review, Review.submission_id == Submission.id)
        .where(*role_filters, Submission.id.in_(scoped_submission_ids))
    )
    total_rows = total_transactions or 0
    total_amount = await db.scalar(
        select(func.coalesce(func.sum(TransactionRow.amount), 0))
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*role_filters, *transaction_filters)
    )
    successful_amount = await db.scalar(
        select(func.coalesce(func.sum(TransactionRow.amount), 0))
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*role_filters, *transaction_filters, TransactionRow.status == TransactionStatus.Successful)
    )

    recent_submissions = (
        await db.execute(select(Submission).where(*role_filters, Submission.id.in_(scoped_submission_ids)).order_by(desc(Submission.uploaded_at)).limit(5))
    ).scalars().all()
    latest_submission = await db.scalar(select(Submission).where(*role_filters).order_by(desc(Submission.uploaded_at)).limit(1))
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
            select(
                TransactionRow.transaction_date.label("day"),
                func.count(TransactionRow.id).label("transactions"),
                func.count(TransactionRow.id).filter(TransactionRow.status == TransactionStatus.Successful).label("approved"),
                func.count(TransactionRow.id).filter(TransactionRow.status == TransactionStatus.Failed).label("declined"),
            )
            .join(Submission, TransactionRow.submission_id == Submission.id)
            .where(*role_filters, *transaction_filters)
            .group_by("day")
            .order_by("day")
            .limit(30)
        )
    ).all()

    workflow_amounts = {
        "initiated": float(total_amount or 0),
        "pending": float(await amount_for_status(db, TransactionStatus.Pending, role_filters, transaction_filters)),
        "approved": float(await amount_for_status(db, TransactionStatus.Successful, role_filters, transaction_filters)),
        "declined": float(await amount_for_status(db, TransactionStatus.Failed, role_filters, transaction_filters)),
    }
    approved_cash = float(successful_amount or 0)

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
            "uploads": total_transactions or 0,
            "initiated": initiated_transactions,
            "approved": successful_transactions,
            "pending": pending_transactions,
            "declined": failed_transactions,
            "reupload_requested": 0,
            "processing": 0,
            "parse_failed": 0,
            "reviewed": reviewed_transactions,
            "approval_rate": round(approval_rate * 100, 1),
            "average_review_seconds": float(average_review_seconds or 0),
            "rows": int(total_rows or 0),
            "revenue": float(total_amount or 0),
            "total_amount": float(total_amount or 0),
            "cash": approved_cash,
            "transaction_initiated_amount": workflow_amounts["initiated"],
            "pending_amount": workflow_amounts["pending"],
            "approved_amount": workflow_amounts["approved"],
            "declined_amount": workflow_amounts["declined"],
        },
        "date_mode": "transaction",
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
        "upload_trends": [{"day": row[0], "uploads": row[1], "approved": row[2], "declined": row[3]} for row in trend_rows],
        "personal": {
            "scope": user.role.value,
            "average_review_seconds": float(average_review_seconds or 0),
            "approval_rate": round(approval_rate * 100, 1),
            "rejection_reasons": await rejection_reasons(db, role_filters, scoped_submission_ids),
        },
        "kpi_snapshots": [],
    }


def transaction_date_filters(date_from: datetime | None, date_to: datetime | None) -> list:
    filters = []
    if date_from:
        filters.append(TransactionRow.transaction_date >= date_from.date())
    if date_to:
        filters.append(TransactionRow.transaction_date <= date_to.date())
    return filters


async def transaction_count_for_status(db: AsyncSession, status: TransactionStatus, role_filters: list, transaction_filters: list) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(TransactionRow)
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*role_filters, *transaction_filters, TransactionRow.status == status)
    ) or 0


async def amount_for_status(db: AsyncSession, status: TransactionStatus, role_filters: list, transaction_filters: list) -> float:
    return await db.scalar(
        select(func.coalesce(func.sum(TransactionRow.amount), 0))
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*role_filters, *transaction_filters, TransactionRow.status == status)
    ) or 0


async def row_count_for_submission(db: AsyncSession, submission_id) -> int:
    return await db.scalar(select(func.count()).select_from(TransactionRow).where(TransactionRow.submission_id == submission_id)) or 0


async def rejection_reasons(db: AsyncSession, role_filters: list, scoped_submission_ids) -> list[dict]:
    rows = (
        await db.execute(
            select(Submission, SubmissionComment)
            .select_from(Submission)
            .join(SubmissionComment, SubmissionComment.submission_id == Submission.id)
            .join(User, User.id == SubmissionComment.user_id)
            .where(*role_filters, Submission.id.in_(scoped_submission_ids))
            .where(Submission.review_status.in_([ReviewStatus.declined, ReviewStatus.reupload_requested]))
            .where(User.role == UserRole.manager)
            .order_by(desc(Submission.uploaded_at), desc(SubmissionComment.created_at))
            .limit(25)
        )
    ).all()

    reasons = []
    seen = set()
    for submission, comment in rows:
        if submission.id in seen:
            continue
        seen.add(submission.id)
        reasons.append(
            {
                "upload_id": submission.id,
                "filename": submission.file_name,
                "status": submission.review_status.value,
                "reason": comment.message,
                "created_at": comment.created_at,
            }
        )
        if len(reasons) >= 5:
            break
    return reasons


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
