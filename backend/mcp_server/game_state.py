"""Gather a small, current view of a story before every narrator request."""

from backend.storage.story_manager import StoryManager


class GameState:
    """Represent the Markdown-backed state as consistent prompt context."""

    def __init__(self, stories: StoryManager) -> None:
        """Reuse the story manager so context and persistence share one source."""

        self.stories = stories

    def build_context(self, story_id: str) -> str:
        """Combine character, goals, and recent events for narrative continuity."""

        story = self.stories.load_story(story_id)
        recent_events = self.stories.recent_session_text(story_id)
        return "\n\n".join(
            (
                f"STORY: {story['name']}",
                "CHARACTER STATE (treat as authoritative):\n" + story["character"],
                "ACTIVE GOALS:\n" + story["goals"],
                "RECENT HISTORY:\n" + (recent_events or "No events have been recorded yet."),
            )
        )
