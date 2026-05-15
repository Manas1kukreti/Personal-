from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.uploads import create_upload
from app.core.security import create_access_token, find_user_by_email, require_roles, verify_password
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas import AgentTokenResponse, LoginRequest, UploadPreview

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/login", response_model=AgentTokenResponse)
async def agent_login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AgentTokenResponse:
    user = await find_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.role != UserRole.employee:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent access requires an employee account")

    return AgentTokenResponse(access_token=create_access_token(user))


@router.post("/upload", response_model=UploadPreview)
async def agent_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.employee)),
) -> UploadPreview:
    return await create_upload(file=file, db=db, user=user)
