"""
Main FastAPI Application for BrainDump NextGen
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.logging_config import setup_logging, get_logger
from app.error_handlers import register_exception_handlers
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
from app.api.auth import router as auth_router
from app.api.planning import router as planning_router
from app.api.rate_limit import limiter

# Setup structured logging
setup_logging()
logger = get_logger(__name__)


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

    # Shutdown logic
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""## BrainDump NextGen

An Agentic Memory Operating System for GenAI Applications.

### Features
- **Event System**: Append-only truth layer for auditability
- **Memory Cards**: Typed information storage with 8 memory types
- **Evolution Memory**: Memory evolution through patches with fitness scoring
- **Governance**: Executable memory rules and policies
- **Memory Graph**: Knowledge relationship management
- **fRAG Engine**: Fragment-aware retrieval generation
- **Evaluation Layer**: Quality metrics and benchmarking
- **Dream Engine**: Asynchronous consolidation

### Authentication
Most endpoints require authentication. Use the `/api/auth/login` endpoint to obtain a JWT token.

### Rate Limiting
API requests are rate-limited. Default: 100 requests per minute per IP.

### Documentation
- Interactive Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
""",
    debug=settings.debug,
    lifespan=lifespan,
    contact={
        "name": "BrainDump NextGen Team",
        "url": "https://github.com/braindump-nextgen",
    },
    license_info={
        "name": "TBD",
    },
    openapi_tags=[
        {
            "name": "Events",
            "description": "Event system operations - append-only truth layer",
        },
        {
            "name": "Memory",
            "description": "Memory card operations - typed information storage",
        },
        {
            "name": "Evolution",
            "description": "Memory evolution operations - patches and fitness",
        },
        {
            "name": "Governance",
            "description": "Governance rules and policy operations",
        },
        {
            "name": "Gatekeeper",
            "description": "Memory gatekeeper validation and risk assessment",
        },
        {
            "name": "Graph",
            "description": "Memory graph operations - knowledge relationships",
        },
        {
            "name": "fRAG",
            "description": "Fragment-aware retrieval generation",
        },
        {
            "name": "Evaluation",
            "description": "Quality metrics and benchmarking",
        },
        {
            "name": "Dream",
            "description": "Dream engine for memory consolidation",
        },
        {
            "name": "Auth",
            "description": "Authentication and authorization",
        },
        {
            "name": "Swarm",
            "description": "Multi-agent orchestration",
        },
        {
            "name": "Planning",
            "description": "Decision making and goal decomposition",
        },
        {
            "name": "Health",
            "description": "Health check and system status",
        },
        {
            "name": "Root",
            "description": "Root endpoints",
        },
    ],
)

# Register exception handlers
register_exception_handlers(app)

# Apply rate limiter to the app
app.state.limiter = limiter

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router)  # Must be first for authentication
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
app.include_router(planning_router)


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