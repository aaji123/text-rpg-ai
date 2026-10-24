"""Validate and persist each campaign's play preferences."""

from typing import Literal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.dependencies import get_story_manager

router = APIRouter(prefix="/api/stories/{story_id}/settings", tags=["settings"])


class StorySettings(BaseModel):
    """Constrain options to values the prompt engineer understands."""

    difficulty: Literal["Easy", "Moderate", "Hard"] = "Moderate"
    mode: Literal["Dice-heavy", "Narrative-heavy", "Hybrid"] = "Hybrid"
    tone: Literal["Grim", "Heroic", "Mystery"] = "Heroic"
    world_power_level: Literal["Low", "Medium", "High/Cosmic"] = "Medium"


@router.get("")
def read_settings(story_id: str) -> dict[str, Any]:
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
def update_settings(story_id: str, request: StorySettings) -> dict[str, Any]:
    """Save validated preferences so subsequent turns use the updated rules."""

    stories = get_story_manager()
    try:
        stories.load_story(story_id)
        return stories.write_settings(story_id, request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
