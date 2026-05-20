from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.security import (
    create_access_token, create_refresh_token, hash_token,
    find_user_by_email, get_current_user, hash_password,
    verify_password, REFRESH_TOKEN_EXPIRE_DAYS
)
from app.db.session import get_db
from app.models import User, UserRole, RefreshToken
from app.schemas import AccountUpdateRequest, LoginRequest, PasswordChangeRequest, TokenResponse, UserCreate, UserRead
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_PATH = "/api/auth"


def user_to_schema(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.full_name,
        email=user.email,
        role=user.role.value,
        manager_id=user.manager_id,
        manager_name=user.manager.full_name if user.manager else None,
    )

async def _issue_tokens(user: User, db: AsyncSession, response: Response) -> TokenResponse:
    access_token = create_access_token(user)
    raw_refresh, hashed_refresh = create_refresh_token()

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=False,       # set to True in production (HTTPS)
        samesite="lax",
        max_age=60 * 60 * 24 * REFRESH_TOKEN_EXPIRE_DAYS,
        path=REFRESH_COOKIE_PATH,
    )
    return TokenResponse(access_token=access_token, user=user_to_schema(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, response: Response, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await find_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    user = User(
        full_name=payload.name.strip(),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=UserRole(payload.role),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await _issue_tokens(user, db, response)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await find_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return await _issue_tokens(user, db, response)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    token_hash = hash_token(refresh_token)
    record = (
        await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.revoked == False)
            .where(RefreshToken.expires_at > datetime.now(timezone.utc))
        )
    ).scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    record.revoked = True
    await db.commit()

    user = await db.get(User, record.user_id)
    return await _issue_tokens(user, db, response)


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> dict:
    if refresh_token:
        token_hash = hash_token(refresh_token)
        record = (
            await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        ).scalar_one_or_none()
        if record:
            record.revoked = True
            await db.commit()

    response.delete_cookie("refresh_token", path=REFRESH_COOKIE_PATH)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)) -> UserRead:
    return user_to_schema(user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: AccountUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserRead:
    user.full_name = payload.name.strip()
    await db.commit()
    await db.refresh(user)
    return user_to_schema(user)


@router.post("/change-password")
async def change_password(
    payload: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return {"message": "Password updated"}
