"""FastAPI application assembly."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app.routes import analytics, enrollment, recognition, status, ui
from src.db.database import init_db, test_connection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown."""
    # Startup
    logger.info("Starting Face Recognition API...")
    
    # Initialize database
    try:
        if test_connection():
            init_db()
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database connection failed - running without database")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        logger.warning("Application will continue without database support")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Face Recognition API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Face Recognition API",
        version="2.0.0",
        description="Production-ready face recognition with PostgreSQL backend",
        lifespan=lifespan
    )

    api_prefix = "/api"

    app.include_router(status.router, prefix=api_prefix)
    app.include_router(enrollment.router, prefix=api_prefix)
    app.include_router(recognition.router, prefix=api_prefix)
    app.include_router(analytics.router, prefix=api_prefix)
    app.include_router(ui.router)

    return app


app = create_app()


__all__ = ["app", "create_app"]
