from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.uploads import verify_upload_access
from app.core.security import require_roles
from app.db.session import get_db
from app.models import AuditAction, Submission, SubmissionComment, User, UserRole
from app.schemas import SubmissionCommentCreate, SubmissionCommentRead
from app.services.audit import log_action
from app.services.email import send_email
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/submissions", tags=["submission-comments"])


def comment_to_schema(comment: SubmissionComment) -> SubmissionCommentRead:
    return SubmissionCommentRead(
        id=comment.id,
        submission_id=comment.submission_id,
        user_id=comment.user_id,
        user_name=comment.user.full_name if comment.user else "User",
        user_role=comment.user.role.value if comment.user else "user",
        message=comment.message,
        created_at=comment.created_at,
    )


async def get_accessible_submission(db: AsyncSession, submission_id: UUID, user: User) -> Submission:
    submission = (
        await db.execute(
            select(Submission)
            .options(selectinload(Submission.user))
            .where(Submission.id == submission_id)
        )
    ).scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    verify_upload_access(submission, user)
    return submission


@router.get("/{submission_id}/comments", response_model=list[SubmissionCommentRead])
async def list_submission_comments(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> list[SubmissionCommentRead]:
    await get_accessible_submission(db, submission_id, user)
    comments = (
        await db.execute(
            select(SubmissionComment)
            .options(selectinload(SubmissionComment.user))
            .where(SubmissionComment.submission_id == submission_id)
            .order_by(SubmissionComment.created_at)
        )
    ).scalars().all()
    return [comment_to_schema(comment) for comment in comments]


@router.post("/{submission_id}/comments", response_model=SubmissionCommentRead, status_code=201)
async def add_submission_comment(
    submission_id: UUID,
    payload: SubmissionCommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> SubmissionCommentRead:
    submission = await get_accessible_submission(db, submission_id, user)
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Comment cannot be empty")

    comment = SubmissionComment(submission_id=submission.id, user_id=user.id, message=message)
    db.add(comment)
    await db.commit()

    comment = (
        await db.execute(
            select(SubmissionComment)
            .options(selectinload(SubmissionComment.user))
            .where(SubmissionComment.id == comment.id)
        )
    ).scalar_one()
    response = comment_to_schema(comment)
    event_payload = response.model_dump(mode="json")
    await log_action(
        db,
        user,
        AuditAction.comment_added,
        target_id=submission.id,
        target_label=submission.file_name,
        detail=message[:255],
    )
    await ws_manager.broadcast("comments", "new_comment", event_payload)
    await ws_manager.broadcast("manager", "new_comment", event_payload)
    await ws_manager.broadcast("submissions", "new_comment", event_payload)
    await notify_comment_recipient(db, submission, user, message)
    return response


async def notify_comment_recipient(db: AsyncSession, submission: Submission, author: User, message: str) -> None:
    recipient: User | None = None
    if author.role == UserRole.manager:
        recipient = submission.user
    elif author.role == UserRole.employee and submission.user.manager_id:
        recipient = await db.get(User, submission.user.manager_id)

    if not recipient or recipient.id == author.id:
        return

    await send_email(
        recipient.email,
        f"New comment on {submission.file_name}",
        (
            f"Hello {recipient.full_name},\n\n"
            f"{author.full_name} commented on {submission.file_name}:\n\n"
            f"{message}\n\n"
            "Open LedgerFlow to reply."
        ),
    )
