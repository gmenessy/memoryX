"""
Prompt API Routes - REST Endpoints for Prompt Operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.swarm.models.prompt import (
    PromptCreate,
    PromptHealth,
    PromptResponse,
    PromptSearchParams,
    PromptState,
    PromptType,
    PromptUpdate,
)
from app.swarm.services.prompt_service import PromptService

router = APIRouter(prefix="/api/swarm/prompts", tags=["Swarm: Prompts"])


@router.post("/", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: PromptCreate,
    session: AsyncSession = Depends(get_db_session)
) -> PromptResponse:
    """
    Create a new prompt.

    Prompts are versioned and tracked with health metrics.
    Creating a prompt with an existing name creates a new version.
    """
    try:
        service = PromptService(session)
        return await service.create_prompt(prompt_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=list[PromptResponse])
async def list_prompts(
    prompt_type: PromptType | None = Query(None, description="Filter by prompt type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    state: PromptState | None = Query(None, description="Filter by state"),
    tags: list[str] | None = Query(None, description="Filter by tags (any match)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session)
) -> list[PromptResponse]:
    """
    List prompts with optional filtering and pagination.

    Results are ordered by creation time (newest first).
    """
    service = PromptService(session)
    return await service.list_prompts(
        prompt_type=prompt_type,
        is_active=is_active,
        state=state,
        tags=tags,
        limit=limit,
        offset=offset
    )


@router.get("/search", response_model=list[PromptResponse])
async def search_prompts(
    query: str = Query(..., description="Search query"),
    prompt_type: PromptType | None = Query(None, description="Filter by prompt type"),
    min_health_score: float | None = Query(None, ge=0.0, le=1.0, description="Minimum health score"),
    limit: int = Query(50, ge=1, le=200, description="Max results (1-200)"),
    session: AsyncSession = Depends(get_db_session)
) -> list[PromptResponse]:
    """
    Search prompts by content, name, or purpose.

    Results are ordered by health score (highest first).
    """
    service = PromptService(session)
    search_params = PromptSearchParams(
        query=query,
        prompt_type=prompt_type,
        min_health_score=min_health_score,
        limit=limit
    )
    return await service.search_prompts(search_params)


@router.get("/active/{name}", response_model=PromptResponse)
async def get_active_prompt(
    name: str,
    session: AsyncSession = Depends(get_db_session)
) -> PromptResponse:
    """
    Get the active version of a prompt by name.
    """
    service = PromptService(session)
    prompt = await service.get_active_prompt(name)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active prompt '{name}' not found"
        )
    return prompt


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> PromptResponse:
    """
    Get a specific prompt by ID.
    """
    service = PromptService(session)
    prompt = await service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    return prompt


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: UUID,
    prompt_data: PromptUpdate,
    session: AsyncSession = Depends(get_db_session)
) -> PromptResponse:
    """
    Update prompt properties.

    Note: Updating content creates a new version.
    """
    service = PromptService(session)
    prompt = await service.update_prompt(prompt_id, prompt_data)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    return prompt


@router.post("/{prompt_id}/activate", response_model=PromptResponse)
async def activate_prompt(
    prompt_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> PromptResponse:
    """
    Activate a prompt version.

    Deactivates all other versions with the same name.
    """
    service = PromptService(session)
    prompt = await service.activate_prompt(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    return prompt


@router.post("/{prompt_id}/health", response_model=PromptResponse)
async def update_prompt_health(
    prompt_id: UUID,
    health: PromptHealth,
    session: AsyncSession = Depends(get_db_session)
) -> PromptResponse:
    """
    Update prompt health metrics.

    Records a usage event and updates health scores.
    """
    service = PromptService(session)
    prompt = await service.update_prompt_health(prompt_id, health)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    return prompt


@router.get("/{prompt_id}/history", response_model=list[PromptResponse])
async def get_prompt_history(
    prompt_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> list[PromptResponse]:
    """
    Get version history for a prompt.

    Returns all versions of the prompt ordered by version number.
    """
    service = PromptService(session)
    return await service.get_prompt_history(prompt_id)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Delete a prompt.

    Permanently removes the prompt from the system.
    """
    service = PromptService(session)
    success = await service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
