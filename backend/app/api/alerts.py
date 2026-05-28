from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models import Alert, User, UserRole
from app.schemas import AlertCreate, AlertRead
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AlertRead:
    settings = get_settings()
    if not settings.agent_email or user.email.lower() != settings.agent_email.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the notification agent can post alerts")

    alert = Alert(
        entry_no=payload.entry_no,
        account_code=payload.account_code,
        sub_account=payload.sub_account,
        difference=payload.difference,
        status=payload.status.upper(),
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    alert_payload = alert_to_schema(alert).model_dump(mode="json")
    await ws_manager.broadcast("dashboard", "dtcd_alert", alert_payload)
    await ws_manager.broadcast("notifications", "dtcd_alert", alert_payload)
    return alert_to_schema(alert)


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    entry: str | None = Query(default=None),
    account: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> list[AlertRead]:
    stmt = select(Alert).order_by(desc(Alert.created_at)).limit(500)
    if entry:
        stmt = stmt.where(Alert.entry_no.ilike(f"%{entry}%"))
    if account:
        stmt = stmt.where(Alert.account_code.ilike(f"%{account}%"))

    alerts = (await db.execute(stmt)).scalars().all()
    return [alert_to_schema(alert) for alert in alerts]


@router.patch("/{alert_id}/read", response_model=AlertRead)
async def mark_alert_read(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> AlertRead:
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.is_read = True
    await db.commit()
    await db.refresh(alert)
    return alert_to_schema(alert)


@router.patch("/read-all")
async def mark_all_alerts_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee, UserRole.manager, UserRole.admin)),
) -> dict[str, int]:
    result = await db.execute(update(Alert).where(Alert.is_read.is_(False)).values(is_read=True))
    await db.commit()
    return {"updated": result.rowcount or 0}


def alert_to_schema(alert: Alert) -> AlertRead:
    return AlertRead(
        id=alert.id,
        entry_no=alert.entry_no,
        account_code=alert.account_code,
        sub_account=alert.sub_account,
        difference=float(alert.difference),
        status=alert.status,
        is_read=alert.is_read,
        created_at=alert.created_at,
    )
