"""
Main FastAPI Application for BrainDump NextGen
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.api.events import router as events_router
from app.api.memory import router as memory_router
from app.api.evolution import router as evolution_router
from app.api.governance import router as governance_router
from app.api.graph import router as graph_router
from app.api.frag import router as frag_router
from app.api.evaluation import router as evaluation_router
from app.api.swarm import router as swarm_router
from app.api.gatekeeper import router as gatekeeper_router
from app.api.dream import router as dream_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan context manager for startup and shutdown events.
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")

    logger.info("Application startup complete")

    yield

    # Shutdown logic here
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="An Agentic Memory Operating System for GenAI Applications",
    debug=settings.debug,
    lifespan=lifespan
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(events_router)
app.include_router(memory_router)
app.include_router(evolution_router)
app.include_router(governance_router)
app.include_router(gatekeeper_router)
app.include_router(dream_router)
app.include_router(graph_router)
app.include_router(frag_router)
app.include_router(evaluation_router)
app.include_router(swarm_router)


# Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# API Endpoints
@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    Root endpoint - returns basic application information.
    """
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "debug": settings.debug
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint for monitoring and load balancers.
    """
    return {
        "status": "ok",
        "application": settings.app_name,
        "version": settings.app_version
    }


@app.get("/api/info", tags=["Info"])
async def api_info() -> dict:
    """
    API information endpoint - returns system configuration and status.
    """
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "database": settings.database_url.split(":///")[0].split("+")[-1],
        "log_level": settings.log_level
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )