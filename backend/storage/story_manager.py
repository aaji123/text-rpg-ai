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
    "world_template": "Fantasy",
    "world_power_level": "Medium",
}
WORLD_TEMPLATES: dict[str, dict[str, Any]] = {
    "Xianxia": {
        "stats": ["Strength", "Agility", "Constitution", "Comprehension", "Perception", "Willpower"],
        "resource": "Qi",
        "extra": "Cultivation Stage",
    },
    "Fantasy": {
        "stats": ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"],
        "resource": "Mana",
        "extra": "Class",
    },
    "Sci-Fi": {
        "stats": ["Strength", "Agility", "Endurance", "Intelligence", "Perception", "Technical Skill"],
        "resource": "Energy",
        "extra": "Augmentations",
    },
    "Cyberpunk": {
        "stats": ["Body", "Reflexes", "Technical Ability", "Intelligence", "Cool", "Empathy"],
        "resource": "Stamina",
        "extra": "Cyberware",
    },
}
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

    def create_story(
        self,
        name: str,
        world_template: str = "Fantasy",
        setting_description: str = "",
        plot_pillars: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a complete campaign from wizard inputs before play begins."""

        slug = self._slug_for_name(name)
        if world_template not in WORLD_TEMPLATES:
            raise ValueError("Choose a supported world template.")
        if len(setting_description) > 2000:
            raise ValueError("Setting description must be 2,000 characters or fewer.")
        pillars = [pillar.strip() for pillar in (plot_pillars or []) if pillar.strip()]
        if len(pillars) > 12 or any(len(pillar) > 160 for pillar in pillars):
            raise ValueError("Add up to 12 plot pillars, each 160 characters or fewer.")
        story_id = slug
        suffix = 2
        while (self.stories_dir / story_id).exists():
            story_id = f"{slug}-{suffix}"
            suffix += 1
        root = self.story_path(story_id)
        root.mkdir()
        (root / "sessions").mkdir()
        self.markdown.write_text(root / "character_state.md", self._character_template(world_template))
        self.markdown.write_text(root / "goals.md", DEFAULT_GOALS)
        self.markdown.write_text(root / "plot_pillars.md", self._plot_pillars_markdown(pillars))
        setting_text = setting_description.strip() or "A new adventure begins."
        self.markdown.write_text(root / "story.md", f"# {name.strip()}\n\n## Setting\n\n{setting_text}\n")
        story_settings = {**DEFAULT_SETTINGS, "world_template": world_template}
        self.write_settings(story_id, story_settings)
        return {"id": story_id, "name": name.strip()}

    @staticmethod
    def _character_template(world_template: str) -> str:
        """Generate a resource and stat sheet that fits the chosen setting genre."""

        template = WORLD_TEMPLATES[world_template]
        stat_lines = "\n".join(f"- {stat}: 10" for stat in template["stats"])
        resource = template["resource"]
        extra = template["extra"]
        return (
            "# Character Sheet\n\n## Identity\n- Name: Adventurer\n- Level: 1\n"
            f"- {extra}: Unset\n\n## Stats\n{stat_lines}\n\n"
            f"## {resource}\n- Current: 0\n- Maximum: 0\n\n## Inventory\n- (empty)\n"
        )

    @staticmethod
    def _plot_pillars_markdown(pillars: list[str]) -> str:
        """Keep player-chosen narrative anchors separate from immediate goals."""

        items = "\n".join(f"- {pillar}" for pillar in pillars) or "- (No plot pillars chosen yet)"
        return f"# Plot Pillars\n\n{items}\n"

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
        character_path = root / "character_state.md"
        legacy_character_path = root / "character.md"
        default_character = self._character_template(self.read_settings(story_id)["world_template"])
        character = self.markdown.read_text(character_path, self.markdown.read_text(legacy_character_path, default_character))
        return {
            "id": story_id,
            "name": next((line[2:].strip() for line in self.markdown.read_text(root / "story.md").splitlines() if line.startswith("# ")), story_id),
            "character": character,
            "goals": self.markdown.read_text(root / "goals.md", DEFAULT_GOALS),
            "plot_pillars": self.markdown.read_text(root / "plot_pillars.md", "# Plot Pillars\n\n- (No plot pillars chosen yet)\n"),
            "setting_description": self._setting_from_markdown(root / "story.md"),
            "settings": self.read_settings(story_id),
            "recent_history": self.recent_session_text(story_id),
        }

    def _setting_from_markdown(self, path: Path) -> str:
        """Return the saved starting premise without leaking a file path."""

        story_text = self.markdown.read_text(path)
        match = re.search(r"^## Setting\s*\n+([\s\S]*?)(?=\n## |\Z)", story_text, re.MULTILINE)
        return match.group(1).strip() if match else "A new adventure begins."

    def read_settings(self, story_id: str) -> dict[str, str]:
        """Load settings with safe defaults if a file is missing or malformed."""

        path = self.story_path(story_id) / "settings.json"
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        settings = {**DEFAULT_SETTINGS, **{key: str(value) for key, value in stored.items() if key in DEFAULT_SETTINGS}}
        if settings["world_template"] not in WORLD_TEMPLATES:
            settings["world_template"] = DEFAULT_SETTINGS["world_template"]
        if settings["world_power_level"] not in {"Low", "Medium", "High/Cosmic"}:
            settings["world_power_level"] = DEFAULT_SETTINGS["world_power_level"]
        return settings

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
