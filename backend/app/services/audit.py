from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditAction, AuditLog, User


async def log_action(
    db: AsyncSession,
    actor: User,
    action: AuditAction,
    target_id: str | None = None,
    target_label: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(AuditLog(
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_role=actor.role.value,
        action=action,
        target_id=str(target_id) if target_id else None,
        target_label=target_label,
        detail=detail,
    ))
    await db.commit()