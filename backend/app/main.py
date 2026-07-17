"""Mia's Reminder - FastAPI Application (crash-proof startup)."""

import os
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Minimal config from env ---
APP_NAME = os.environ.get("APP_NAME", "Mia's Reminder")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start services gracefully - don't crash if something is unavailable."""
    logger.info(f"Starting {APP_NAME}...")

    # Try to init database
    try:
        from app.core.database import init_db
        await init_db()
        logger.info("Database connected and tables created")
    except Exception as e:
        logger.error(f"Database init failed (will retry on requests): {e}")

    # Try to start scheduler
    try:
        from app.scheduler.reminder_scheduler import start_scheduler
        start_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler start failed: {e}")

    logger.info(f"{APP_NAME} is ready!")
    yield

    # Shutdown
    logger.info("Shutting down...")
    try:
        from app.scheduler.reminder_scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    try:
        from app.core.database import close_db
        await close_db()
    except Exception:
        pass
    try:
        from app.core.redis import close_redis
        await close_redis()
    except Exception:
        pass


# Create app
app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
    description="Mia's Reminder - AI-powered life organizer",
    lifespan=lifespan,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)


# --- Health endpoints (always work, no imports) ---

@app.get("/")
async def root():
    return {"name": APP_NAME, "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "name": APP_NAME}


# --- Load API routes (wrapped in try/except so app starts even if imports fail) ---

try:
    from app.api import api_router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("API routes loaded")
except Exception as e:
    logger.error(f"Failed to load API routes: {e}")

    # Fallback route
    @app.get("/api/v1/status")
    async def api_status():
        return {"error": "API routes failed to load", "detail": str(e)}


# --- Telegram webhook ---

@app.post("/api/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    try:
        from app.telegram.bot import create_telegram_app
        from telegram import Update
        data = await request.json()
        telegram_app = create_telegram_app()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return JSONResponse(status_code=500, content={"error": "Telegram error"})


# --- Global exception handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})
