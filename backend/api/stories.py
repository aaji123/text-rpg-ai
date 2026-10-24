"""Expose safe story listing, creation, and loading endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.dependencies import get_story_manager

router = APIRouter(prefix="/api/stories", tags=["stories"])


class CreateStoryRequest(BaseModel):
    """Validate user story names before folder creation."""

    name: str = Field(min_length=1, max_length=60)


@router.get("")
def list_stories() -> list[dict[str, str]]:
    """Return public story summaries without disclosing filesystem paths."""

    return get_story_manager().list_stories()


@router.post("", status_code=201)
def create_story(request: CreateStoryRequest) -> dict[str, str]:
    """Create a starter campaign and translate name errors into client errors."""

    try:
        return get_story_manager().create_story(request.name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{story_id}")
def load_story(story_id: str) -> dict:
    """Load the campaign state required by the frontend play screen."""

    try:
        return get_story_manager().load_story(story_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
