from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import auth, business, agent, records, analytics
from app.api.routes import settings as settings_routes
from app.core.config import settings
from app.core.rate_limiter import RateLimitMiddleware
from app.db.init_db import init_db
from app.telegram.bot import start_bot_background, stop_bot_background
from app.agent.proactive_scheduler import start_reminder_scheduler, stop_reminder_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("[*] Initializing database...")
        init_db()
        print("[OK] Database initialized")
        
        if settings.TELEGRAM_BOT_TOKEN:
            print("[*] Starting Telegram bot...")
            start_bot_background()
            print("[*] Starting reminder scheduler...")
            start_reminder_scheduler()
            print("[OK] Bot and scheduler started")
        else:
            print("[WARN] Telegram bot disabled (no token)")
    except Exception as e:
        print(f"[ERROR] Startup error: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    
    try:
        if settings.TELEGRAM_BOT_TOKEN:
            stop_bot_background()
            stop_reminder_scheduler()
    except Exception as e:
        print(f"[ERROR] Shutdown error: {e}")


app = FastAPI(
    title="Bharat Biz-Agent API",
    description="Owner control panel & Telegram bridge. Draft → Approve → Execute.",
    version="0.1.0",
    lifespan=lifespan,
)

trusted_hosts = [
    "localhost",
    "127.0.0.1",
    "localhost:3000",
    "127.0.0.1:3000",
    "localhost:3001",
    "127.0.0.1:3001",
    # Docker container names
    "frontend",
    "backend",
    "frontend:3000",
    "backend:8000",
]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
    ],
    max_age=600,
    expose_headers=["Content-Type"],
)

app.add_middleware(RateLimitMiddleware)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self';"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(business.router, prefix="/business", tags=["business"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(records.router, prefix="/records", tags=["records"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


# Health check endpoint for Docker
@app.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Bharat Biz-Agent Backend",
        "version": "0.1.0"
    }

app.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
