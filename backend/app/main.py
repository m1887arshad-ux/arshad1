"""
Bharat Biz-Agent Backend — Central authority for PS-2.
Connects: Telegram (user interaction), Owner Website (approval & control), Database (source of truth).
No AI. Rule-based agent only. All actions require owner approval.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, business, agent, records
from app.api.routes import settings as settings_routes
from app.core.config import settings
from app.db.init_db import init_db
from app.telegram.bot import start_bot_background, stop_bot_background


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and start Telegram bot on startup; stop bot on shutdown."""
    init_db()
    start_bot_background()
    yield
    stop_bot_background()


app = FastAPI(
    title="Bharat Biz-Agent API",
    description="Owner control panel & Telegram bridge. Draft → Approve → Execute.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(business.router, prefix="/business", tags=["business"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(records.router, prefix="/records", tags=["records"])
app.include_router(settings_routes.router, prefix="/settings", tags=["settings"])


@app.get("/health")
def health():
    return {"status": "ok"}
