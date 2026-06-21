"""
Swarm API Package
Export all swarm-related routers for easy importing.
"""

from fastapi import APIRouter

from app.api.swarm.agents import router as agents_router
from app.api.swarm.prompts import router as prompts_router
from app.api.swarm.swarms import router as swarms_router
from app.api.swarm.tasks import router as tasks_router

# Create main swarm router
router = APIRouter()

# Include sub-routers
router.include_router(agents_router)
router.include_router(prompts_router)
router.include_router(swarms_router)
router.include_router(tasks_router)

__all__ = ["router"]
