from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import require_roles
from app.db.session import get_db
from app.models import Review, ReviewAction, ReviewStatus, Submission, User, UserRole
from app.schemas import ApprovalActionRequest, ApprovalRequest, RejectActionRequest, RejectRequest, ReuploadActionRequest, ReuploadRequest
from app.services.email import send_email
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/approve")
async def approve_upload_by_body(
    request: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    manager: User = Depends(require_roles(UserRole.manager)),
) -> dict:
    return await create_review(request.upload_id, ReviewAction.approved, request.comment, db, manager)


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
    if action != ReviewAction.approved and not comment:
        raise HTTPException(status_code=422, detail="Comment is required for declined or reupload_requested reviews")

    submission.review_status = ReviewStatus(action.value)
    db.add(Review(submission_id=submission.id, manager_id=manager.id, action=action, comment=comment))
    await db.commit()

    payload = {"upload_id": submission.id, "status": submission.review_status.value, "filename": submission.file_name}
    if comment:
        payload["comment"] = comment
    await ws_manager.broadcast("uploads", "upload_status", payload)
    await ws_manager.broadcast("uploads", "approval.decision", payload)
    await ws_manager.broadcast("manager", "upload_reviewed", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)
    await ws_manager.broadcast("dashboard", "kpi.update", payload)
    comment_line = f"\n\nManager comment: {comment}" if comment else ""
    await send_email(
        submission.user.email,
        f"Upload {submission.review_status.value}",
        (
            f"Hello {submission.user.full_name},\n\n"
            f"Your upload {submission.file_name} was marked {submission.review_status.value}."
            f"{comment_line}"
        ),
    )
    return {"message": f"Submission {submission.review_status.value}", **payload}
