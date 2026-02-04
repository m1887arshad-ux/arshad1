"""
Bharat Biz-Agent Backend — Central authority for PS-2.

ARCHITECTURE:
- Telegram Bot: Customer interaction (Hinglish voice/text)
- FastAPI Backend: Business logic, safety enforcement, persistence
- SQLite DB: Source of truth for all state
- Next.js Dashboard: Owner approval interface

SAFETY MODEL:
- All actions go through Draft → Approve → Execute pipeline
- Proactive agent can CREATE drafts, never EXECUTE autonomously
- LLM used only for intent parsing, not decision making

No autonomous financial execution. Human-in-the-loop always.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, business, agent, records
from app.api.routes import settings as settings_routes
from app.core.config import settings
from app.db.init_db import init_db
from app.telegram.bot import start_bot_background, stop_bot_background
from app.agent.proactive_scheduler import start_reminder_scheduler, stop_reminder_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Startup:
    1. Initialize database tables
    2. Start Telegram bot polling
    3. Start proactive agent scheduler (payment reminders)
    
    Shutdown:
    1. Stop Telegram bot gracefully
    2. Stop proactive scheduler
    """
    init_db()
    start_bot_background()
    start_reminder_scheduler()  # PROACTIVE AGENT: Background payment reminder scanner
    yield
    stop_bot_background()
    stop_reminder_scheduler()


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
    return {"status": "ok", "proactive_agent": "enabled"}
