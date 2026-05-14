from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import admin, analytics, approvals, auth, uploads, websockets
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models import User, UserRole

settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploads.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(websockets.router)


@app.on_event("startup")
async def on_startup() -> None:
    async with AsyncSessionLocal() as db:
        existing_admin = (
            await db.execute(select(User).where(User.email == settings.default_admin_email.lower()))
        ).scalar_one_or_none()
        if existing_admin is None:
            db.add(
                User(
                    full_name=settings.default_admin_name,
                    email=settings.default_admin_email.lower(),
                    hashed_password=hash_password(settings.default_admin_password),
                    role=UserRole.admin,
                )
            )
            await db.commit()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
