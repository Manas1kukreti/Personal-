from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_roles
from app.db.session import get_db
from app.models import AuditLog, User, UserRole

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
) -> list[dict]:
    logs = (
        await db.execute(
            select(AuditLog)
            .order_by(desc(AuditLog.created_at))
            .limit(200)
        )
    ).scalars().all()

    return [
        {
            "id": log.id,
            "actor_name": log.actor_name,
            "actor_role": log.actor_role,
            "action": log.action.value,
            "target_label": log.target_label,
            "detail": log.detail,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]