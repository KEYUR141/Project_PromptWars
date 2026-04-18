"""
VenueIQ — AI-Powered Real-Time Crowd Intelligence Platform
===========================================================
Hack2Skill PromptWars 2026 | Physical Event Experience Vertical

Author:  VenueIQ Team
Version: 3.0.0 (Enterprise Refactor)

Architecture:
  - Modular FastAPI backend
  - JWT Authentication via HttpOnly cookies
  - Gemini 2.0 Flash for context-aware AI decisions
  - Google Cloud Logging & Firestore
  - Deployed on Google Cloud Run via Docker
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from config import logger, GEMINI_API_KEY, db, MAPS_API_KEY
from security import limiter, add_security_headers
from simulation import run_crowd_simulation
from routes import api_router, page_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Manage application lifespan: start background tasks on startup."""
    task = asyncio.create_task(run_crowd_simulation())
    logger.info(
        "VenueIQ started | gemini=%s | firestore=%s | maps=%s",
        bool(GEMINI_API_KEY), db is not None, bool(MAPS_API_KEY),
    )
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("VenueIQ shutdown complete")

app = FastAPI(
    title="VenueIQ",
    description="AI-Powered Real-Time Crowd Intelligence Platform for Physical Events",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Setup Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Security Headers Middleware
app.middleware("http")(add_security_headers)

# Setup Static and Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.templates = Jinja2Templates(directory="templates")

# Include Routers
app.include_router(page_router)
app.include_router(api_router)

# Health Check Route
@app.get("/health", summary="Health check for Cloud Run", tags=["System"])
async def health():
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "venueiq",
        "version": "3.0.0",
        "ai_configured":        bool(GEMINI_API_KEY),
        "maps_configured":      bool(MAPS_API_KEY),
        "firestore_configured": db is not None,
        "cloud_logging":        True,
        "timestamp":            datetime.now().isoformat(),
    }
