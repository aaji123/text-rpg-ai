"""Expose safe story listing, creation, and loading endpoints."""

import json
import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.ai.prompt_engineer import build_brainstorm_prompt
from backend.api.dependencies import get_narrator, get_story_manager

router = APIRouter(prefix="/api/stories", tags=["stories"])


class CreateStoryRequest(BaseModel):
    """Validate user story names before folder creation."""

    name: str = Field(min_length=1, max_length=60)
    world_template: Literal["Xianxia", "Fantasy", "Sci-Fi", "Cyberpunk"] = "Fantasy"
    setting_description: str = Field(default="", max_length=2000)
    plot_pillars: list[str] = Field(default_factory=list, max_length=12)
    character: dict[str, Any] = Field(default_factory=dict)
    world_settings: dict[str, Any] = Field(default_factory=dict)


class BrainstormRequest(BaseModel):
    """Bound brainstorm inputs before including them in an external model call."""

    idea: str = Field(min_length=3, max_length=1000)
    world_template: Literal["Xianxia", "Fantasy", "Sci-Fi", "Cyberpunk"] = "Fantasy"
    setting_description: str = Field(default="", max_length=2000)
    tone: Literal["Grim", "Heroic", "Mystery"] = "Heroic"
    mode: Literal["Dice-heavy", "Narrative-heavy", "Hybrid"] = "Hybrid"
    world_power_level: Literal["Low", "Medium", "High/Cosmic"] = "Medium"
    highest_power_level: str = Field(default="unspecified", max_length=60)
    realm_hierarchy: list[str] = Field(default_factory=list, max_length=20)


@router.get("")
def list_stories() -> list[dict[str, str]]:
    """Return public story summaries without disclosing filesystem paths."""

    return get_story_manager().list_stories()


@router.post("", status_code=201)
def create_story(request: CreateStoryRequest) -> dict[str, str]:
    """Create a starter campaign and translate name errors into client errors."""

    try:
        return get_story_manager().create_story(
            request.name,
            request.world_template,
            request.setting_description,
            request.plot_pillars,
            request.character,
            request.world_settings,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/brainstorm")
async def brainstorm(request: BrainstormRequest) -> dict[str, list[str]]:
    """Ask Groq for three optional plot anchors without creating a story yet."""

    try:
        settings = request.model_dump(exclude={"idea"})
        raw_suggestions = await get_narrator().brainstorm(build_brainstorm_prompt(request.idea.strip(), settings), request.idea.strip())
    except ValueError as error:
        raise HTTPException(status_code=503, detail="Groq API key is not configured in .env.") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="The brainstorm service could not complete the request.") from error
    cleaned_response = re.sub(r"<think>[\s\S]*?</think>", "", raw_suggestions).strip()
    array_start = cleaned_response.find("[")
    array_end = cleaned_response.rfind("]")
    candidate = cleaned_response[array_start:array_end + 1] if array_start >= 0 and array_end > array_start else cleaned_response
    try:
        suggestions = json.loads(candidate)
    except json.JSONDecodeError:
        suggestions = re.findall(r"(?:^|\n)\s*(?:[-*\d.)]+\s+)?(.+)", cleaned_response)
    if not isinstance(suggestions, list):
        raise HTTPException(status_code=502, detail="The brainstorm service returned an invalid response.")
    cleaned = [item.strip() for item in suggestions if isinstance(item, str) and item.strip()]
    if len(cleaned) < 3:
        raise HTTPException(status_code=502, detail="The brainstorm service returned fewer than three suggestions.")
    return {"suggestions": cleaned[:3]}


@router.get("/{story_id}")
def load_story(story_id: str) -> dict:
    """Load the campaign state required by the frontend play screen."""

    try:
        return get_story_manager().load_story(story_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
