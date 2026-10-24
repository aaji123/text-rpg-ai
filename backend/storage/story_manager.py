"""Manage isolated story folders while rejecting unsafe names and identifiers."""

import json
import re
from pathlib import Path
from typing import Any

from backend.storage.markdown_handler import MarkdownHandler


DEFAULT_SETTINGS: dict[str, str] = {
    "difficulty": "Moderate",
    "mode": "Hybrid",
    "tone": "Adventurous",
}
DEFAULT_CHARACTER = """# Character Sheet

## Identity
- Name: Adventurer
- Level: 1

## Stats
- Strength: 10
- Dexterity: 10
- Constitution: 10
- Intelligence: 10
- Wisdom: 10
- Charisma: 10

## Qi
- Current: 0
- Maximum: 0

## Inventory
- (empty)
"""
DEFAULT_GOALS = "# Active Goals\n\n- (No active goals yet)\n"


class StoryManager:
    """Own story folder layout and enforce path containment at its boundary."""

    def __init__(self, stories_dir: Path, markdown: MarkdownHandler | None = None) -> None:
        """Keep storage rooted at one configured local directory."""

        self.stories_dir = stories_dir.resolve()
        self.markdown = markdown or MarkdownHandler()
        self.stories_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _slug_for_name(name: str) -> str:
        """Convert a display name into a conservative folder identifier."""

        clean_name = name.strip()
        if not clean_name or len(clean_name) > 60:
            raise ValueError("Story names must contain between 1 and 60 characters.")
        if any(ord(character) < 32 for character in clean_name):
            raise ValueError("Story names cannot contain control characters.")
        slug = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")
        if not slug:
            raise ValueError("Story name must include at least one letter or number.")
        return slug

    @staticmethod
    def _validate_story_id(story_id: str) -> str:
        """Accept only generated slug identifiers before resolving user paths."""

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", story_id):
            raise ValueError("Invalid story identifier.")
        return story_id

    def story_path(self, story_id: str) -> Path:
        """Resolve a checked story identifier and confirm it stays under storage."""

        safe_id = self._validate_story_id(story_id)
        path = (self.stories_dir / safe_id).resolve()
        if path.parent != self.stories_dir:
            raise ValueError("Invalid story identifier.")
        return path

    def create_story(self, name: str) -> dict[str, Any]:
        """Create a complete starter story so the game can begin immediately."""

        slug = self._slug_for_name(name)
        story_id = slug
        suffix = 2
        while (self.stories_dir / story_id).exists():
            story_id = f"{slug}-{suffix}"
            suffix += 1
        root = self.story_path(story_id)
        root.mkdir()
        (root / "sessions").mkdir()
        self.markdown.write_text(root / "character.md", DEFAULT_CHARACTER)
        self.markdown.write_text(root / "goals.md", DEFAULT_GOALS)
        self.markdown.write_text(root / "story.md", f"# {name.strip()}\n\nA new adventure begins.\n")
        self.write_settings(story_id, DEFAULT_SETTINGS)
        return {"id": story_id, "name": name.strip()}

    def list_stories(self) -> list[dict[str, str]]:
        """Expose story ids and friendly names without returning local paths."""

        stories: list[dict[str, str]] = []
        for directory in sorted(self.stories_dir.iterdir(), key=lambda item: item.name):
            if not directory.is_dir() or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", directory.name):
                continue
            title = self.markdown.read_text(directory / "story.md", f"# {directory.name}\n")
            first_line = next((line[2:].strip() for line in title.splitlines() if line.startswith("# ")), directory.name)
            stories.append({"id": directory.name, "name": first_line})
        return stories

    def load_story(self, story_id: str) -> dict[str, Any]:
        """Return the public story documents needed to restore the play screen."""

        root = self.story_path(story_id)
        if not root.is_dir():
            raise FileNotFoundError("Story not found.")
        return {
            "id": story_id,
            "name": next((line[2:].strip() for line in self.markdown.read_text(root / "story.md").splitlines() if line.startswith("# ")), story_id),
            "character": self.markdown.read_text(root / "character.md", DEFAULT_CHARACTER),
            "goals": self.markdown.read_text(root / "goals.md", DEFAULT_GOALS),
            "settings": self.read_settings(story_id),
            "recent_history": self.recent_session_text(story_id),
        }

    def read_settings(self, story_id: str) -> dict[str, str]:
        """Load settings with safe defaults if a file is missing or malformed."""

        path = self.story_path(story_id) / "settings.json"
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        return {**DEFAULT_SETTINGS, **{key: str(value) for key, value in stored.items() if key in DEFAULT_SETTINGS}}

    def write_settings(self, story_id: str, settings: dict[str, str]) -> dict[str, str]:
        """Persist only supported preference fields to keep config predictable."""

        allowed = {key: settings[key] for key in DEFAULT_SETTINGS if key in settings}
        current = self.read_settings(story_id) if self.story_path(story_id).is_dir() else DEFAULT_SETTINGS.copy()
        merged = {**current, **allowed}
        path = self.story_path(story_id) / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        return merged

    def recent_session_text(self, story_id: str, limit: int = 12) -> str:
        """Read the newest events in chronological order for bounded AI context."""

        sessions_dir = self.story_path(story_id) / "sessions"
        paths = sorted(sessions_dir.glob("session_*.md"))
        events: list[str] = []
        for path in paths:
            contents = path.read_text(encoding="utf-8")
            events.extend(re.split(r"(?=^## )", contents, flags=re.MULTILINE))
        recent_events = [event.strip() for event in events if event.strip()][-max(1, limit):]
        return "\n\n".join(recent_events)

    def append_event(self, story_id: str, heading: str, content: str) -> Path:
        """Route a log event to the checked story's session folder."""

        root = self.story_path(story_id)
        if not root.is_dir():
            raise FileNotFoundError("Story not found.")
        return self.markdown.append_event(root / "sessions", heading, content)
