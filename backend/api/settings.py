"""Validate and persist each campaign's play preferences."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.dependencies import get_story_manager

router = APIRouter(prefix="/api/stories/{story_id}/settings", tags=["settings"])


class StorySettings(BaseModel):
    """Constrain options to values the prompt engineer understands."""

    difficulty: Literal["Easy", "Moderate", "Hard"] = "Moderate"
    mode: Literal["Dice", "Narrative", "Hybrid"] = "Hybrid"
    tone: str = Field(default="Adventurous", min_length=1, max_length=80)
    world_power_level: Literal["Low", "Medium", "High/Cosmic"] = "Medium"


@router.get("")
def read_settings(story_id: str) -> dict[str, str]:
    """Return saved preferences for the selected story."""

    stories = get_story_manager()
    try:
        stories.load_story(story_id)
        return stories.read_settings(story_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error


@router.put("")
def update_settings(story_id: str, request: StorySettings) -> dict[str, str]:
    """Save validated preferences so subsequent turns use the updated rules."""

    stories = get_story_manager()
    try:
        stories.load_story(story_id)
        return stories.write_settings(story_id, request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
