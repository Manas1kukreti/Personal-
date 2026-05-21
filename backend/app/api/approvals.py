from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import require_roles
from app.db.session import get_db
from app.models import Review, ReviewAction, ReviewStatus, Submission, SubmissionComment, User, UserRole
from app.schemas import ApprovalActionRequest, ApprovalRequest, RejectActionRequest, RejectRequest, ReuploadActionRequest, ReuploadRequest
from app.services.email import send_email, verify_review_token
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/approve")
async def approve_upload_by_body(
    request: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager)),
) -> dict:
    return await create_review(request.upload_id, ReviewAction.approved, request.comment, db, manager)

@router.get("/verify-token")
async def verify_review_link_token(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        payload = verify_review_token(token)
    except ValueError as e:
        raise HTTPException(status_code=410, detail=str(e))

    submission_id = payload["submission_id"]
    submission = (
        await db.execute(
            select(Submission)
            .options(selectinload(Submission.user))
            .where(Submission.id == submission_id)
        )
    ).scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {
        "submission_id": submission_id,
        "manager_id": payload["manager_id"],
        "filename": submission.file_name,
        "status": submission.review_status.value,
    }

@router.post("/{upload_id}/approve")
async def approve_upload(
    upload_id: UUID,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager)),
) -> dict:
    return await create_review(upload_id, ReviewAction.approved, request.comment, db, manager)


@router.post("/reject")
async def reject_upload_by_body(
    request: RejectActionRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager)),
) -> dict:
    return await create_review(request.upload_id, ReviewAction.declined, request.comment, db, manager)


@router.post("/{upload_id}/reject")
async def reject_upload(
    upload_id: UUID,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager)),
) -> dict:
    return await create_review(upload_id, ReviewAction.declined, request.comment, db, manager)


@router.post("/request-reupload")
async def request_reupload_by_body(
    request: ReuploadActionRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager)),
) -> dict:
    return await create_review(request.upload_id, ReviewAction.reupload_requested, request.comment, db, manager)


@router.post("/{upload_id}/request-reupload")
async def request_reupload(
    upload_id: UUID,
    request: ReuploadRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager)),
) -> dict:
    return await create_review(upload_id, ReviewAction.reupload_requested, request.comment, db, manager)


async def create_review(
    submission_id: UUID,
    action: ReviewAction,
    comment: str | None,
    db: AsyncSession,
    manager: User,
) -> dict:
    submission = (
        await db.execute(select(Submission).options(selectinload(Submission.user)).where(Submission.id == submission_id))
    ).scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not submission.user or submission.user.manager_id != manager.id:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.review_status != ReviewStatus.pending:
        raise HTTPException(status_code=409, detail=f"Submission is already {submission.review_status.value}")
    if action != ReviewAction.approved:
        has_thread_feedback = (
            await db.execute(
                select(SubmissionComment.id)
                .where(SubmissionComment.submission_id == submission.id)
                .where(SubmissionComment.user_id == manager.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if not has_thread_feedback:
            raise HTTPException(
                status_code=422,
                detail="Add feedback in the conversation thread before rejecting or requesting re-upload.",
            )

    submission.review_status = ReviewStatus(action.value)
    db.add(Review(submission_id=submission.id, manager_id=manager.id, action=action, comment=None))
    await db.commit()

    payload = {"upload_id": submission.id, "status": submission.review_status.value, "filename": submission.file_name}
    await ws_manager.broadcast("uploads", "upload_status", payload)
    await ws_manager.broadcast("uploads", "approval.decision", payload)
    await ws_manager.broadcast("manager", "upload_reviewed", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)
    await ws_manager.broadcast("dashboard", "kpi.update", payload)
    await send_email(
        submission.user.email,
        f"Upload {submission.review_status.value}",
        (
            f"Hello {submission.user.full_name},\n\n"
            f"Your upload {submission.file_name} was marked {submission.review_status.value}."
            "\n\nOpen LedgerFlow to view the conversation thread."
        ),
    )
    return {"message": f"Submission {submission.review_status.value}", **payload}
