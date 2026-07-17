"""FastAPI application entry point - production hardened."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.core.redis import close_redis
from app.core.bootstrap import make_first_user_admin
from app.api import api_router
from app.scheduler.reminder_scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Rate limiter (global IP-based)
limiter = Limiter(key_func=get_remote_address)


# --- Security Middleware ---

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request timing and basic info."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Log slow requests
        if duration > 2.0:
            logger.warning(
                f"SLOW REQUEST: {request.method} {request.url.path} "
                f"took {duration:.2f}s - status {response.status_code}"
            )

        response.headers["X-Process-Time"] = str(round(duration * 1000))
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent abuse."""

    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large. Maximum 10MB."},
            )
        return await call_next(request)


# --- Application Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logger.info("Starting Mia's Reminder API...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug: {settings.debug}")

    await init_db()
    await make_first_user_admin()
    start_scheduler()

    # Initialize Firebase (optional - skip gracefully if not configured)
    try:
        import firebase_admin
        from firebase_admin import credentials

        if settings.firebase_credentials_path and settings.firebase_project_id:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized")
        else:
            logger.info("Firebase not configured - OAuth login disabled")
    except Exception as e:
        logger.warning(f"Firebase initialization skipped: {e}")

    logger.info("API ready to serve requests")
    yield

    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()
    await close_db()
    await close_redis()
    logger.info("Shutdown complete")


# --- Create App ---

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Mia's Reminder API - Intelligent life management for everyone",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# --- Middleware Stack (order matters: last added = first executed) ---

# Rate limiting (global)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - allow frontend domains
# In production, set CORS_ORIGINS to your actual frontend domain(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if not settings.debug else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Process-Time"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Trusted hosts (production only)
if not settings.debug:
    allowed_hosts = [h.replace("https://", "").replace("http://", "")
                     for h in settings.cors_origins_list]
    allowed_hosts.extend(["localhost", "127.0.0.1"])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request logging
app.add_middleware(RequestLoggingMiddleware)

# Request size limit
app.add_middleware(RequestSizeLimitMiddleware)


# --- Routes ---

app.include_router(api_router, prefix=f"/api/{settings.api_version}")


@app.get("/")
async def root():
    """Public health check endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else None,
    }


@app.get("/health")
async def health():
    """Detailed health check for monitoring."""
    from app.core.redis import redis_client

    # Check Redis
    redis_ok = False
    try:
        await redis_client.ping()
        redis_ok = True
    except Exception:
        pass

    # Check DB
    db_ok = False
    try:
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    status_code = 200 if (redis_ok and db_ok) else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if status_code == 200 else "degraded",
            "checks": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
                "scheduler": "running",
            },
            "environment": settings.app_env,
        },
    )


# Telegram webhook endpoint (public - verified by Telegram)
@app.post(f"/api/{settings.api_version}/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates."""
    from app.telegram.bot import create_telegram_app
    from telegram import Update

    try:
        data = await request.json()
        telegram_app = create_telegram_app()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal error"})


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions - don't leak internal details."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
