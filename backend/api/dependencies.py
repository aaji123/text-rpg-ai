"""Share configured service objects across route modules."""

from functools import lru_cache

from backend.ai.groq_client import GroqNarrator
from backend.config import get_settings
from backend.mcp_server.game_state import GameState
from backend.storage.story_manager import StoryManager


@lru_cache(maxsize=1)
def get_story_manager() -> StoryManager:
    """Use one storage root so every route sees the same local campaigns."""

    return StoryManager(get_settings().stories_dir)


@lru_cache(maxsize=1)
def get_game_state() -> GameState:
    """Build prompt context through the same manager used by the routes."""

    return GameState(get_story_manager())


def get_narrator() -> GroqNarrator:
    """Create the provider wrapper only when an AI response is requested."""

    settings = get_settings()
    return GroqNarrator(settings.groq_api_key, settings.groq_model)
