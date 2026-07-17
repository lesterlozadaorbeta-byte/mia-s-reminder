"""FastAPI application - Mia's Reminder API."""

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mia's Reminder",
    version="1.0.0",
    description="AI Personal Assistant API",
)

# CORS - allow all for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    try:
        from app.core.database import init_db
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init skipped: {e}")

    try:
        from app.core.bootstrap import make_first_user_admin
        await make_first_user_admin()
    except Exception as e:
        logger.warning(f"Bootstrap skipped: {e}")


@app.get("/")
async def root():
    return {
        "name": "Mia's Reminder",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Import and include API routes
try:
    from app.api import api_router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("API routes loaded")
except Exception as e:
    logger.error(f"Failed to load API routes: {e}")
