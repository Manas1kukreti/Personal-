from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, approvals, auth, uploads, websockets
from app.core.config import get_settings
from app.db.session import engine
from app.models import Base

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
app.include_router(websockets.router)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
