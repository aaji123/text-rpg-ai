"""Expose safe story listing, creation, and loading endpoints."""

import json
import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from backend.ai.prompt_engineer import build_brainstorm_prompt, build_example_prompt
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
    tone: Literal["Gritty", "Heroic", "Mysterious", "Dark", "Whimsical", "Philosophical", "Grim", "Mystery"] = "Heroic"
    mode: Literal["Dice-heavy", "Narrative-heavy", "Hybrid"] = "Hybrid"
    world_power_level: Literal["Low", "Medium", "High/Cosmic"] = "Medium"
    highest_power_level: str = Field(default="unspecified", max_length=60)
    starting_plane: str = Field(default="Mortal Plane", max_length=100)
    house_rules: str = Field(default="", max_length=2000)
    atmosphere: str = Field(default="", max_length=2000)
    realm_hierarchy: list[str] = Field(default_factory=list, max_length=100)


class ExampleRequest(BaseModel):
    """Validate the small world-setting payload sent for a helper example."""

    field: Literal["setting_description", "house_rules", "atmosphere"]
    world_template: Literal["Xianxia", "Fantasy", "Sci-Fi", "Cyberpunk"] = "Fantasy"
    setting_description: str = Field(default="", max_length=2000)
    tone: Literal["Gritty", "Heroic", "Mysterious", "Dark", "Whimsical", "Philosophical"] = "Heroic"
    mode: Literal["Dice-heavy", "Narrative-heavy", "Hybrid"] = "Hybrid"
    world_power_level: Literal["Low", "Medium", "High/Cosmic"] = "Medium"
    highest_power_level: str = Field(default="unspecified", max_length=100)
    starting_plane: str = Field(default="Mortal Plane", max_length=100)
    house_rules: str = Field(default="", max_length=2000)
    atmosphere: str = Field(default="", max_length=2000)
    realm_hierarchy: list[str] = Field(default_factory=list, max_length=100)


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
    cleaned = []
    for item in suggestions:
        if not isinstance(item, str) or not item.strip():
            continue
        value = item.strip()
        if len(value) >= 160:
            value = value[:157].rsplit(" ", 1)[0].rstrip() + "…"
        cleaned.append(value)
    if len(cleaned) < 3:
        raise HTTPException(status_code=502, detail="The brainstorm service returned fewer than three suggestions.")
    return {"suggestions": cleaned[:3]}


@router.post("/example")
async def generate_example(request: ExampleRequest) -> dict[str, str]:
    """Generate an optional genre-aware sample for one wizard field."""

    settings = request.model_dump(exclude={"field"})
    try:
        example = await get_narrator().generate_example(build_example_prompt(request.field, settings))
    except ValueError as error:
        raise HTTPException(status_code=503, detail="Groq API key is not configured in .env.") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="The example generator could not complete the request.") from error
    cleaned_example = re.sub(r"<think>[\s\S]*?</think>", "", example).strip().strip('"')
    if not cleaned_example:
        raise HTTPException(status_code=502, detail="The example generator returned an empty response.")
    if len(cleaned_example) > 500:
        cleaned_example = cleaned_example[:497].rsplit(" ", 1)[0].rstrip() + "…"
    return {"example": cleaned_example}


@router.post("/import", status_code=201)
async def import_story(request: Request, name: str = "") -> dict[str, str]:
    """Import a bounded ZIP without extracting untrusted archive paths."""

    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in {"application/zip", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Upload a story ZIP archive.")
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Story archive must be no larger than 25 MB.")
    chunks = []
    total_size = 0
    async for chunk in request.stream():
        total_size += len(chunk)
        if total_size > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Story archive must be no larger than 25 MB.")
        chunks.append(chunk)
    archive_bytes = b"".join(chunks)
    try:
        return get_story_manager().import_archive(archive_bytes, name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{story_id}/export")
def export_story(story_id: str) -> Response:
    """Download a portable, whitelist-only archive of one campaign."""

    try:
        archive = get_story_manager().export_archive(story_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{story_id}.zip"'},
    )


@router.delete("/{story_id}", status_code=204)
def delete_story(story_id: str) -> Response:
    """Delete a single campaign after the story manager checks its folder."""

    try:
        get_story_manager().delete_story(story_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
    return Response(status_code=204)


@router.get("/{story_id}")
def load_story(story_id: str) -> dict:
    """Load the campaign state required by the frontend play screen."""

    try:
        return get_story_manager().load_story(story_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
