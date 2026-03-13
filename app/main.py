"""
Adaptive Diagnostic Engine – FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import connect_to_mongo, close_mongo_connection
from app.routes.test_routes import router as test_router

# ── Logging ───────────────────────────────────────────────────────────────────
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (replaces deprecated on_event) ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup / shutdown tasks."""
    logger.info("Starting Adaptive Diagnostic Engine [env=%s]", settings.app_env)
    await connect_to_mongo()
    yield
    await close_mongo_connection()
    logger.info("Adaptive Diagnostic Engine shut down cleanly.")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI-Driven Adaptive Diagnostic Engine",
    description=(
        "A 1-Dimension Adaptive Testing system using IRT-inspired ability estimation "
        "and LLM-powered personalised study plans."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow all origins in dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(test_router, prefix="/api/v1")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Lightweight liveness probe."""
    return JSONResponse({"status": "ok", "version": "1.0.0"})
