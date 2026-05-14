from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.security import require_roles
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas import AdminEmployeeRead, AdminUserRead, AssignmentRequest
from app.services.email import send_email

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/managers", response_model=list[AdminUserRead])
async def list_managers(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
) -> list[AdminUserRead]:
    employee_alias = aliased(User)
    rows = (
        await db.execute(
            select(User, func.count(employee_alias.id).label("employee_count"))
            .join(employee_alias, employee_alias.manager_id == User.id, isouter=True)
            .where(User.role == UserRole.manager)
            .group_by(User.id)
            .order_by(User.full_name)
        )
    ).all()
    return [
        AdminUserRead(
            id=manager.id,
            name=manager.full_name,
            email=manager.email,
            role=manager.role.value,
            manager_id=manager.manager_id,
            manager_name=None,
            assigned_employee_count=employee_count,
        )
        for manager, employee_count in rows
    ]


@router.get("/employees", response_model=list[AdminEmployeeRead])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
) -> list[AdminEmployeeRead]:
    employees = (
        await db.execute(
            select(User)
            .options(selectinload(User.manager))
            .where(User.role == UserRole.employee)
            .order_by(User.full_name)
        )
    ).scalars().all()
    return [
        AdminEmployeeRead(
            id=employee.id,
            name=employee.full_name,
            email=employee.email,
            role=employee.role.value,
            manager_id=employee.manager_id,
            manager_name=employee.manager.full_name if employee.manager else None,
            assignment_status="assigned" if employee.manager_id else "unassigned",
        )
        for employee in employees
    ]


@router.post("/assign", response_model=AdminEmployeeRead)
async def assign_employee(
    payload: AssignmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
) -> AdminEmployeeRead:
    return await save_assignment(payload, db, allow_existing=False)


@router.post("/reassign", response_model=AdminEmployeeRead)
async def reassign_employee(
    payload: AssignmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
) -> AdminEmployeeRead:
    return await save_assignment(payload, db, allow_existing=True)


async def save_assignment(payload: AssignmentRequest, db: AsyncSession, allow_existing: bool) -> AdminEmployeeRead:
    employee = await db.get(User, payload.employee_id)
    manager = await db.get(User, payload.manager_id)
    if not employee or employee.role != UserRole.employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if not manager or manager.role != UserRole.manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    if employee.manager_id and not allow_existing:
        raise HTTPException(status_code=409, detail="Employee is already assigned")

    employee.manager_id = manager.id
    await db.commit()
    await db.refresh(employee, attribute_names=["manager"])

    await send_email(
        employee.email,
        "You have been assigned to a manager",
        f"Hello {employee.full_name},\n\nYou are now assigned to {manager.full_name} for upload review.",
    )

    return AdminEmployeeRead(
        id=employee.id,
        name=employee.full_name,
        email=employee.email,
        role=employee.role.value,
        manager_id=employee.manager_id,
        manager_name=manager.full_name,
        assignment_status="assigned",
    )
