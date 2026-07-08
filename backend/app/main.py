"""FastAPI application entry point.

OffroadTrip - 越野智行: AI-powered off-road road trip planner.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import generate, routes, weather

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="越野智行 - 大模型智能体驱动的越野自驾游规划平台",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(routes.router, prefix="/api", tags=["routes"])
app.include_router(weather.router, prefix="/api", tags=["weather"])


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
