from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_roles
from app.db.session import get_db
from app.models import Review, ReviewStatus, Submission, SubmissionComment, TransactionRow, User, UserRole


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/kpis")
async def get_kpis(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> dict:
    role_filters = _role_filters(user)
    date_filters = _date_filters(date_from, date_to)

    # ------------------------------------------------------------------ #
    # Row-level totals                                                     #
    # ------------------------------------------------------------------ #
    total_rows: int = await db.scalar(
        select(func.count(TransactionRow.id))
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*role_filters, *date_filters)
    ) or 0

    total_debits: float = await db.scalar(
        select(func.coalesce(func.sum(TransactionRow.debit_amount), 0))
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*role_filters, *date_filters)
    ) or 0.0

    total_credits: float = await db.scalar(
        select(func.coalesce(func.sum(TransactionRow.credit_amount), 0))
        .join(Submission, TransactionRow.submission_id == Submission.id)
        .where(*role_filters, *date_filters)
    ) or 0.0

    entry_group_rows = (
        await db.execute(
            select(
                TransactionRow.submission_id,
                TransactionRow.entry_group,
                func.coalesce(func.sum(TransactionRow.debit_amount), 0).label("sum_debit"),
                func.coalesce(func.sum(TransactionRow.credit_amount), 0).label("sum_credit"),
            )
            .join(Submission, TransactionRow.submission_id == Submission.id)
            .where(*role_filters, *date_filters)
            .group_by(TransactionRow.submission_id, TransactionRow.entry_group)
        )
    ).all()

    total_entry_groups = len(entry_group_rows)
    balanced_entry_groups = sum(
        1 for _, _, d, c in entry_group_rows if round(float(d), 2) == round(float(c), 2)
    )
    unbalanced_entry_groups = total_entry_groups - balanced_entry_groups

    # ------------------------------------------------------------------ #
    # Submission-level counts (workflow)                                   #
    # ------------------------------------------------------------------ #
    # For workflow counts, scope by role only (no approved filter)
    role_only_filters = _role_filters_no_status(user)
    scoped_submission_ids = (
        select(Submission.id)
        .where(*role_only_filters, *date_filters)
        .distinct()
        .subquery()
    )

    submission_status_rows = (
        await db.execute(
            select(Submission.review_status, func.count(Submission.id).label("cnt"))
            .where(Submission.id.in_(select(scoped_submission_ids)))
            .group_by(Submission.review_status)
        )
    ).all()

    status_counts: dict[str, int] = {row.review_status.value: row.cnt for row in submission_status_rows}
    total_submissions = sum(status_counts.values())
    approved_count = status_counts.get(ReviewStatus.approved.value, 0)
    pending_count = status_counts.get(ReviewStatus.pending.value, 0)
    declined_count = status_counts.get(ReviewStatus.declined.value, 0)
    reupload_count = status_counts.get(ReviewStatus.reupload_requested.value, 0)
    processing_count = status_counts.get(ReviewStatus.processing.value, 0)
    parse_failed_count = status_counts.get(ReviewStatus.parse_failed.value, 0)
    reviewed_count = approved_count + declined_count
    approval_rate = approved_count / reviewed_count if reviewed_count else 0.0

    # ------------------------------------------------------------------ #
    # Average review time                                                  #
    # ------------------------------------------------------------------ #
    average_review_seconds: float = await db.scalar(
        select(func.avg(func.extract("epoch", Review.reviewed_at - Submission.uploaded_at)))
        .select_from(Submission)
        .join(Review, Review.submission_id == Submission.id)
        .where(Submission.id.in_(select(scoped_submission_ids)))
    ) or 0.0

    # ------------------------------------------------------------------ #
    # Account-class breakdown                                              #
    # ------------------------------------------------------------------ #
    class_rows = (
        await db.execute(
            select(
                TransactionRow.account_class,
                func.coalesce(func.sum(TransactionRow.debit_amount), 0).label("debits"),
                func.coalesce(func.sum(TransactionRow.credit_amount), 0).label("credits"),
                func.count(TransactionRow.id).label("row_count"),
            )
            .join(Submission, TransactionRow.submission_id == Submission.id)
            .where(*role_filters, *date_filters)
            .group_by(TransactionRow.account_class)
            .order_by(desc("debits"))
        )
    ).all()

    account_class_breakdown = [
        {
            "account_class": row.account_class,
            "debits": float(row.debits),
            "credits": float(row.credits),
            "net": float(row.debits) - float(row.credits),
            "row_count": row.row_count,
        }
        for row in class_rows
    ]

    # ------------------------------------------------------------------ #
    # Daily trend (debit/credit by date)                                  #
    # ------------------------------------------------------------------ #
    trend_rows = (
        await db.execute(
            select(
                TransactionRow.date.label("day"),
                func.coalesce(func.sum(TransactionRow.debit_amount), 0).label("debits"),
                func.coalesce(func.sum(TransactionRow.credit_amount), 0).label("credits"),
                func.count(TransactionRow.id).label("row_count"),
            )
            .join(Submission, TransactionRow.submission_id == Submission.id)
            .where(*role_filters, *date_filters)
            .group_by(TransactionRow.date)
            .order_by(TransactionRow.date)
            .limit(90)
        )
    ).all()

    daily_trends = [
        {
            "date": row.day.isoformat() if row.day else None,
            "debits": float(row.debits),
            "credits": float(row.credits),
            "net": float(row.debits) - float(row.credits),
            "row_count": row.row_count,
        }
        for row in trend_rows
    ]

    # ------------------------------------------------------------------ #
    # Daily transaction trend (completed / under investigation / total)   #
    # ------------------------------------------------------------------ #
    tx_group_rows = (
        await db.execute(
            select(
                TransactionRow.date.label("day"),
                TransactionRow.entry_group,
                func.coalesce(func.sum(TransactionRow.debit_amount), 0).label("sum_debit"),
                func.coalesce(func.sum(TransactionRow.credit_amount), 0).label("sum_credit"),
            )
            .join(Submission, TransactionRow.submission_id == Submission.id)
            .where(*role_filters, *date_filters)
            .group_by(TransactionRow.date, TransactionRow.entry_group)
            .order_by(TransactionRow.date)
        )
    ).all()

    # Group by date, classify each entry group
    from collections import defaultdict
    tx_by_date: dict = defaultdict(lambda: {"total": 0, "completed": 0, "under_investigation": 0})
    for row in tx_group_rows:
        day = row.day.isoformat() if row.day else None
        if not day:
            continue
        tx_by_date[day]["total"] += 1
        if round(float(row.sum_debit), 2) == round(float(row.sum_credit), 2):
            tx_by_date[day]["completed"] += 1
        else:
            tx_by_date[day]["under_investigation"] += 1

    daily_transaction_trends = [
        {
            "date": day,
            "total": counts["total"],
            "completed": counts["completed"],
            "under_investigation": counts["under_investigation"],
        }
        for day, counts in sorted(tx_by_date.items())
    ]

    # ------------------------------------------------------------------ #
    # Recent submissions                                                   #
    # ------------------------------------------------------------------ #
    recent_submissions = (
        await db.execute(
            select(Submission)
            .where(Submission.id.in_(select(scoped_submission_ids)))
            .order_by(desc(Submission.uploaded_at))
            .limit(5)
        )
    ).scalars().all()

    latest_submission = await db.scalar(
        select(Submission)
        .where(*role_filters)
        .order_by(desc(Submission.uploaded_at))
        .limit(1)
    )

    latest_rows: list[TransactionRow] = []
    if latest_submission:
        latest_rows = (
            await db.execute(
                select(TransactionRow)
                .where(TransactionRow.submission_id == latest_submission.id)
                .order_by(TransactionRow.date, TransactionRow.entry_group, TransactionRow.entry_line)
                .limit(10)
            )
        ).scalars().all()

    # ------------------------------------------------------------------ #
    # Response                                                             #
    # ------------------------------------------------------------------ #
    return {
        "totals": {
            "uploads": total_submissions,
            "approved": approved_count,
            "pending": pending_count,
            "declined": declined_count,
            "reupload_requested": reupload_count,
            "processing": processing_count,
            "parse_failed": parse_failed_count,
            "reviewed": reviewed_count,
            "approval_rate": round(approval_rate * 100, 1),
            "average_review_seconds": float(average_review_seconds),
            "rows": total_rows,
            "total_debits": float(total_debits),
            "total_credits": float(total_credits),
            "net": float(total_debits) - float(total_credits),
            "total_entry_groups": total_entry_groups,
            "balanced_entry_groups": balanced_entry_groups,
            "unbalanced_entry_groups": unbalanced_entry_groups,
        },
        "date_mode": "gl_date",
        "account_class_breakdown": account_class_breakdown,
        "daily_trends": daily_trends,
        "daily_transaction_trends": daily_transaction_trends,
        "recent_uploads": [
            {
                "id": submission.id,
                "filename": submission.file_name,
                "status": submission.review_status.value,
                "rows": await _row_count_for_submission(db, submission.id),
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
        "last_rows": [_format_gl_row(row, latest_submission) for row in latest_rows],
        "personal": {
            "scope": user.role.value,
            "average_review_seconds": float(average_review_seconds),
            "approval_rate": round(approval_rate * 100, 1),
            "rejection_reasons": await _rejection_reasons(db, role_filters, select(scoped_submission_ids)),
        },
        "kpi_snapshots": [],
    }


# ------------------------------------------------------------------ #
# Private helpers                                                     #
# ------------------------------------------------------------------ #

def _role_filters(user: User) -> list:
    approved = Submission.review_status == ReviewStatus.approved
    if user.role == UserRole.employee:
        return [Submission.user_id == user.id, approved]
    if user.role == UserRole.manager:
        return [Submission.user_id.in_(select(User.id).where(User.manager_id == user.id)), approved]
    return [approved]  # admin also sees only approved GL data


def _date_filters(date_from: datetime | None, date_to: datetime | None) -> list:
    filters = []
    if date_from:
        filters.append(Submission.uploaded_at >= date_from)
    if date_to:
        filters.append(Submission.uploaded_at <= date_to)
    return filters


async def _row_count_for_submission(db: AsyncSession, submission_id) -> int:
    return await db.scalar(
        select(func.count()).select_from(TransactionRow).where(TransactionRow.submission_id == submission_id)
    ) or 0


async def _rejection_reasons(db: AsyncSession, role_filters: list, scoped_submission_ids) -> list[dict]:
    rows = (
        await db.execute(
            select(Submission, SubmissionComment)
            .select_from(Submission)
            .join(SubmissionComment, SubmissionComment.submission_id == Submission.id)
            .join(User, User.id == SubmissionComment.user_id)
            .where(
                *role_filters,
                Submission.id.in_(scoped_submission_ids),
                Submission.review_status.in_([ReviewStatus.declined, ReviewStatus.reupload_requested]),
                User.role == UserRole.manager,
            )
            .order_by(desc(Submission.uploaded_at), desc(SubmissionComment.created_at))
            .limit(25)
        )
    ).all()

    reasons = []
    seen: set = set()
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


def _format_gl_row(row: TransactionRow, submission: Submission | None) -> dict:
    return {
        "upload_id": str(row.submission_id),
        "upload_status": submission.review_status.value if submission else None,
        "uploaded_at": submission.uploaded_at.isoformat() if submission and submission.uploaded_at else None,
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

def _role_filters_no_status(user: User) -> list:
    if user.role == UserRole.employee:
        return [Submission.user_id == user.id]
    if user.role == UserRole.manager:
        return [Submission.user_id.in_(select(User.id).where(User.manager_id == user.id))]
    return []