from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import admin, agent, analytics, approvals, auth, uploads, websockets
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
app.include_router(agent.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(websockets.router)


@app.on_event("startup")
async def on_startup() -> None:
    async with AsyncSessionLocal() as db:
        await seed_user(
            db,
            name=settings.default_admin_name,
            email=settings.default_admin_email,
            password=settings.default_admin_password,
            role=UserRole.admin,
        )
        if settings.agent_email and settings.agent_password:
            await seed_user(
                db,
                name=settings.agent_name,
                email=settings.agent_email,
                password=settings.agent_password,
                role=UserRole.employee,
            )


async def seed_user(db, *, name: str, email: str, password: str, role: UserRole) -> None:
    existing_user = (
        await db.execute(select(User).where(User.email == email.lower()))
    ).scalar_one_or_none()
    if existing_user is not None:
        return

    db.add(
        User(
            full_name=name,
            email=email.lower(),
            hashed_password=hash_password(password),
            role=role,
        )
    )
    await db.commit()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
