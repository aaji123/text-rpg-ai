"""Gather current JSON-backed game state before every narrator request."""

import json

from backend.storage.story_manager import StoryManager


class GameState:
    """Represent structured character state as consistent prompt context."""

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
                "STARTING SETTING:\n" + story["setting_description"],
                "AUTHORITATIVE CHARACTER STATE JSON:\n" + json.dumps(story["state"], indent=2, ensure_ascii=False),
                "HUMAN-READABLE CHARACTER SUMMARY:\n" + story["character"],
                "ACTIVE GOALS (from authoritative JSON):\n"
                + ("\n".join(f"- {goal}" for goal in story["state"].get("active_goals", [])) or "- None recorded."),
                "LONG-TERM PLOT PILLARS (player-selected narrative anchors, from authoritative JSON):\n"
                + ("\n".join(f"- {pillar}" for pillar in story["state"].get("plot_pillars", [])) or "- None recorded."),
                "RECENT HISTORY:\n" + (recent_events or "No events have been recorded yet."),
            )
        )
