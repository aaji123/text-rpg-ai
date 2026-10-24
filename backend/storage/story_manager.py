"""Manage isolated story folders while rejecting unsafe names and identifiers."""

import json
import re
import shutil
import stat
import zipfile
from io import BytesIO
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from backend.storage.markdown_handler import MarkdownHandler
from backend.storage.state_store import StateStore


STAT_POINT_BUDGET = 72
MIN_STAT_VALUE = 3
MAX_STAT_VALUE = 18
DEFAULT_SETTINGS: dict[str, Any] = {
    "difficulty": "Moderate",
    "mode": "Hybrid",
    "tone": "Heroic",
    "world_template": "Fantasy",
    "world_power_level": "Medium",
    "highest_power_level": "Mythic",
    "starting_plane": "Mortal Plane",
    "house_rules": "",
    "atmosphere": "",
    "realm_hierarchy": ["Commoner", "Novice", "Adept", "Expert", "Master", "Legendary", "Mythic"],
}
_CULTIVATION_REALMS = [
    ("Body Tempering", "Qi Refining", "Foundation Establishment", "Core Formation", "Golden Core"),
    ("Nascent Soul", "Soul Formation", "Divine Transformation", "Void Refinement", "Integration"),
    ("True Immortal", "Heavenly Immortal", "Golden Immortal"),
    ("Immortal King", "Immortal Emperor", "Celestial Immortal", "Dao Lord", "Eternal Sovereign"),
    ("Heavenly Dao Master", "Saint/Sage", "Supreme Saint", "Chaos Realm", "Universal Creator", "Origin Ancestor"),
]
XIANXIA_REALM_HIERARCHY = [
    "Mortal/Beginner",
    *(f"{realm} — {stage}" for group in _CULTIVATION_REALMS for realm in group for stage in ("Early", "Mid", "Late")),
]
WORLD_TEMPLATES: dict[str, dict[str, Any]] = {
    "Xianxia": {
        "stats": ["Strength", "Agility", "Constitution", "Comprehension", "Perception", "Willpower"],
        "resource": "Qi",
        "extra": "Cultivation Stage",
        "realms": XIANXIA_REALM_HIERARCHY,
    },
    "Fantasy": {
        "stats": ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"],
        "resource": "Mana",
        "extra": "Class",
        "realms": ["Commoner", "Novice", "Adept", "Expert", "Master", "Legendary", "Mythic"],
    },
    "Sci-Fi": {
        "stats": ["Strength", "Agility", "Endurance", "Intelligence", "Perception", "Technical Skill"],
        "resource": "Energy",
        "extra": "Augmentations",
        "realms": ["Tier 0: Civilian", "Tier 1: Enhanced", "Tier 2: Operative", "Tier 3: Elite", "Tier 4: Apex", "Tier 5: Posthuman"],
    },
    "Cyberpunk": {
        "stats": ["Body", "Reflexes", "Technical Ability", "Intelligence", "Cool", "Empathy"],
        "resource": "Stamina",
        "extra": "Cyberware",
        "realms": ["Civilian", "Streetwise", "Professional", "Elite", "Corporate Legend", "Night City Myth"],
    },
}
DEFAULT_GOALS = "# Active Goals\n\n- (No active goals yet)\n"


class StoryManager:
    """Own story folder layout and enforce path containment at its boundary."""

    def __init__(self, stories_dir: Path, markdown: MarkdownHandler | None = None) -> None:
        """Keep storage rooted at one configured local directory."""

        self.stories_dir = stories_dir.resolve()
        self.markdown = markdown or MarkdownHandler()
        self.state_store = StateStore()
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
        candidate = self.stories_dir / safe_id
        if candidate.is_symlink():
            raise ValueError("Invalid story identifier.")
        path = candidate.resolve()
        if path.parent != self.stories_dir:
            raise ValueError("Invalid story identifier.")
        return path

    def create_story(
        self,
        name: str,
        world_template: str = "Fantasy",
        setting_description: str = "",
        plot_pillars: list[str] | None = None,
        character: dict[str, Any] | None = None,
        world_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a campaign with validated JSON state and generated Markdown."""

        slug = self._slug_for_name(name)
        if world_template not in WORLD_TEMPLATES:
            raise ValueError("Choose a supported world template.")
        if len(setting_description) > 2000:
            raise ValueError("Setting description must be 2,000 characters or fewer.")
        pillars = [pillar.strip() for pillar in (plot_pillars or []) if pillar.strip()]
        if len(pillars) > 12 or any(len(pillar) > 160 for pillar in pillars):
            raise ValueError("Add up to 12 plot pillars, each 160 characters or fewer.")
        settings = self._validate_world_settings(world_template, world_settings or {})
        state = self._new_character_state(world_template, character or {}, settings["realm_hierarchy"])
        story_id = slug
        suffix = 2
        while (self.stories_dir / story_id).exists():
            story_id = f"{slug}-{suffix}"
            suffix += 1
        root = self.story_path(story_id)
        root.mkdir()
        (root / "sessions").mkdir()
        setting_text = setting_description.strip() or "A new adventure begins."
        state.update({
            "campaign_name": name.strip(),
            "setting_description": setting_text,
            "plot_pillars": pillars,
            "active_goals": [],
        })
        self.state_store.write(root, state, WORLD_TEMPLATES[world_template]["resource"])
        story_settings = {**settings, "world_template": world_template}
        self.write_settings(story_id, story_settings)
        return {"id": story_id, "name": name.strip()}

    def import_archive(self, archive_bytes: bytes, requested_name: str = "") -> dict[str, str]:
        """Validate a portable story ZIP and copy only recognized files into storage."""

        if not archive_bytes or len(archive_bytes) > 25 * 1024 * 1024:
            raise ValueError("Story archive must be no larger than 25 MB.")
        try:
            archive = zipfile.ZipFile(BytesIO(archive_bytes))
        except (zipfile.BadZipFile, OSError) as error:
            raise ValueError("Choose a valid story ZIP archive.") from error
        with archive:
            entries = archive.infolist()
            if not 1 <= len(entries) <= 1200:
                raise ValueError("Story archive contains too many files.")
            safe_entries: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
            for entry in entries:
                raw_name = entry.filename
                if "\\" in raw_name or "\x00" in raw_name:
                    raise ValueError("Story archive contains an unsafe file name.")
                path = PurePosixPath(raw_name)
                if path.is_absolute() or any(part in {"..", "."} for part in path.parts):
                    raise ValueError("Story archive contains an unsafe file path.")
                file_mode = entry.external_attr >> 16
                if stat.S_ISLNK(file_mode):
                    raise ValueError("Story archives cannot contain symbolic links.")
                if not entry.is_dir():
                    safe_entries.append((entry, path.parts))

            state_entries = [(entry, parts) for entry, parts in safe_entries if parts[-1:] == ("state.json",)]
            if len(state_entries) != 1:
                raise ValueError("Story archive must contain exactly one state.json file.")
            _, state_parts = state_entries[0]
            root_prefix = state_parts[:-1]
            if len(root_prefix) > 1:
                raise ValueError("Story files may be at the archive root or in one campaign folder.")
            extracted: dict[str, bytes] = {}
            uncompressed_total = 0
            for entry, parts in safe_entries:
                if root_prefix:
                    if parts[:len(root_prefix)] != root_prefix:
                        raise ValueError("Story archive mixes files from multiple folders.")
                    parts = parts[len(root_prefix):]
                relative_name = "/".join(parts)
                if relative_name in extracted:
                    raise ValueError("Story archive contains duplicate paths.")
                allowed = relative_name in {"state.json", "settings.json"} or relative_name in {
                    "character_state.md", "goals.md", "plot_pillars.md", "story.md"
                } or bool(re.fullmatch(r"sessions/session_\d{4}-\d{2}-\d{2}\.md", relative_name))
                if not allowed:
                    raise ValueError("Story archive contains an unsupported file.")
                file_limit = 5 * 1024 * 1024 if relative_name.startswith("sessions/") else 2 * 1024 * 1024
                if entry.file_size > file_limit:
                    raise ValueError("A file in the story archive exceeds its size limit.")
                uncompressed_total += entry.file_size
                if uncompressed_total > 25 * 1024 * 1024:
                    raise ValueError("Uncompressed story data exceeds 25 MB.")
                try:
                    contents = archive.read(entry)
                except (zipfile.BadZipFile, RuntimeError, OSError) as error:
                    raise ValueError("A story archive file could not be safely read.") from error
                if len(contents) != entry.file_size:
                    raise ValueError("A story archive file did not match its declared size.")
                extracted[relative_name] = contents

        try:
            state = json.loads(extracted["state.json"].decode("utf-8"))
            raw_settings = json.loads(extracted.get("settings.json", b"{}").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Story JSON files must contain valid UTF-8 JSON.") from error
        if not isinstance(state, dict) or not isinstance(raw_settings, dict):
            raise ValueError("Story state and settings must be JSON objects.")
        world_template = str(raw_settings.get("world_template", state.get("world_template", "Fantasy")))
        if world_template not in WORLD_TEMPLATES:
            raise ValueError("Story archive uses an unsupported world template.")
        settings = self._validate_world_settings(world_template, raw_settings)
        difficulty = raw_settings.get("difficulty", "Moderate")
        settings["difficulty"] = difficulty if isinstance(difficulty, str) and difficulty in {"Easy", "Moderate", "Hard"} else "Moderate"
        state["world_template"] = world_template
        name = requested_name.strip() or str(state.get("campaign_name", "Imported Story")).strip()
        slug = self._slug_for_name(name)
        story_id = slug
        suffix = 2
        while (self.stories_dir / story_id).exists():
            story_id = f"{slug}-{suffix}"
            suffix += 1
        normalized_state = self._normalize_existing_state(state, settings)
        normalized_state["campaign_name"] = name[:60]
        root = self.story_path(story_id)
        root.mkdir()
        try:
            (root / "sessions").mkdir()
            self.state_store.write(root, normalized_state, WORLD_TEMPLATES[world_template]["resource"])
            (root / "settings.json").write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            for relative_name, contents in extracted.items():
                if relative_name.startswith("sessions/"):
                    destination = root.joinpath(*PurePosixPath(relative_name).parts)
                    destination.write_bytes(contents)
        except OSError:
            shutil.rmtree(root, ignore_errors=True)
            raise
        return {"id": story_id, "name": normalized_state["campaign_name"]}

    def export_archive(self, story_id: str) -> bytes:
        """Package only portable campaign documents for safe sharing and import."""

        root = self.story_path(story_id)
        if not root.is_dir():
            raise FileNotFoundError("Story not found.")
        self.load_state(story_id)
        output = BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for filename in ("state.json", "settings.json", "character_state.md", "goals.md", "plot_pillars.md", "story.md"):
                path = root / filename
                if path.is_file() and not path.is_symlink():
                    archive.write(path, filename)
            sessions_dir = root / "sessions"
            if sessions_dir.is_dir() and not sessions_dir.is_symlink():
                for path in sorted(sessions_dir.glob("session_*.md")):
                    if path.is_file() and not path.is_symlink() and path.resolve().parent == sessions_dir.resolve():
                        archive.write(path, f"sessions/{path.name}")
        return output.getvalue()

    def delete_story(self, story_id: str) -> None:
        """Remove one checked campaign folder after confirming it is a local directory."""

        root = self.story_path(story_id)
        if not root.is_dir() or root.parent != self.stories_dir:
            raise FileNotFoundError("Story not found.")
        shutil.rmtree(root)

    @staticmethod
    def _validate_world_settings(world_template: str, supplied: dict[str, Any]) -> dict[str, Any]:
        """Validate editable realm progression and its declared world ceiling."""

        defaults = list(WORLD_TEMPLATES[world_template]["realms"])
        realms = supplied.get("realm_hierarchy", defaults)
        if not isinstance(realms, list):
            raise ValueError("Realm hierarchy must be a list of names.")
        realms = [str(realm).strip() for realm in realms if str(realm).strip()]
        if not 2 <= len(realms) <= 100 or any(len(realm) > 100 for realm in realms):
            raise ValueError("Realm hierarchy must contain 2 to 100 names, each 100 characters or fewer.")
        if len({realm.casefold() for realm in realms}) != len(realms):
            raise ValueError("Realm names must be unique.")
        highest = str(supplied.get("highest_power_level", realms[-1])).strip()
        if highest not in realms:
            raise ValueError("Highest power level must match a realm in the hierarchy.")
        power_level = str(supplied.get("world_power_level", "Medium"))
        if power_level not in {"Low", "Medium", "High/Cosmic"}:
            raise ValueError("World power level must be Low, Medium, or High/Cosmic.")
        mode = str(supplied.get("mode", "Hybrid"))
        if mode not in {"Dice-heavy", "Narrative-heavy", "Hybrid"}:
            raise ValueError("Play mode must be Dice-heavy, Narrative-heavy, or Hybrid.")
        tone = str(supplied.get("tone", "Heroic"))
        tone_aliases = {"Grim": "Gritty", "Mystery": "Mysterious", "Dark": "Dark", "Whimsical": "Whimsical", "Philosophical": "Philosophical"}
        tone = tone_aliases.get(tone, tone)
        if tone not in {"Gritty", "Heroic", "Mysterious", "Dark", "Whimsical", "Philosophical"}:
            raise ValueError("Choose a supported adventure tone.")
        starting_plane = str(supplied.get("starting_plane", "Mortal Plane")).strip()
        house_rules = str(supplied.get("house_rules", "")).strip()
        atmosphere = str(supplied.get("atmosphere", "")).strip()
        if not starting_plane or len(starting_plane) > 100 or len(house_rules) > 2000 or len(atmosphere) > 2000:
            raise ValueError("Starting plane, house rules, or atmosphere exceeds its allowed length.")
        return {
            "difficulty": "Moderate",
            "mode": mode,
            "tone": tone,
            "world_power_level": power_level,
            "highest_power_level": highest,
            "realm_hierarchy": realms,
            "starting_plane": starting_plane,
            "house_rules": house_rules,
            "atmosphere": atmosphere,
            "world_template": world_template,
        }

    @staticmethod
    def _new_character_state(
        world_template: str,
        character: dict[str, Any],
        realms: list[str],
    ) -> dict[str, Any]:
        """Create schema-versioned state and enforce valid stats and item metadata."""

        template = WORLD_TEMPLATES[world_template]
        identity = character.get("identity", {})
        if not isinstance(identity, dict):
            raise ValueError("Character identity must be an object.")
        name = str(identity.get("name", "Adventurer")).strip()
        background = str(identity.get("background", "Unchosen")).strip()
        age = identity.get("age", 18)
        if not name or len(name) > 80 or not background or len(background) > 1000:
            raise ValueError("Character name or background is empty or too long.")
        if isinstance(age, bool) or not isinstance(age, int) or not 1 <= age <= 999:
            raise ValueError("Character age must be a whole number from 1 to 999.")
        raw_stats = character.get("stats", {})
        if not isinstance(raw_stats, dict):
            raise ValueError("Character stats must be an object.")
        stat_labels = template["stats"]
        unknown_stats = set(raw_stats) - set(stat_labels)
        if unknown_stats:
            raise ValueError("Character stats do not match the selected world template.")
        stats = {label: raw_stats.get(label, 10) for label in stat_labels}
        if any(isinstance(value, bool) or not isinstance(value, int) or not MIN_STAT_VALUE <= value <= MAX_STAT_VALUE for value in stats.values()):
            raise ValueError(f"Every stat must be a whole number from {MIN_STAT_VALUE} to {MAX_STAT_VALUE}.")
        if sum(stats.values()) > STAT_POINT_BUDGET:
            raise ValueError(f"Character stats may use at most {STAT_POINT_BUDGET} points total.")
        inventory = StoryManager._validate_inventory(character.get("inventory", []))
        current_realm = realms[0]
        return {
            "schema_version": 1,
            "campaign_name": "Untitled Story",
            "setting_description": "A new adventure begins.",
            "plot_pillars": [],
            "active_goals": [],
            "world_template": world_template,
            "identity": {"name": name, "age": age, "background": background},
            "stats": stats,
            "resource_label": template["resource"],
            "resource": {"current": 0, "maximum": 0},
            "realm_progress": {"current": current_realm, "rank_index": 0},
            "inventory": inventory,
            "relationships": [],
            "lore_bank": [],
            "techniques": [],
        }

    @staticmethod
    def _validate_inventory(items: Any) -> list[dict[str, Any]]:
        """Normalize each starting item so its usage metadata has predictable fields."""

        if not isinstance(items, list) or len(items) > 50:
            raise ValueError("Inventory must be a list of no more than 50 items.")
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValueError("Each inventory item must be an object.")
            name = str(item.get("name", "")).strip()
            kind = str(item.get("kind", "Permanent"))
            if not name or len(name) > 80 or kind not in {"Consumable", "Durable", "Permanent"}:
                raise ValueError("Each item needs a name and a supported item type.")
            tags = item.get("tags", [kind])
            if not isinstance(tags, list) or len(tags) > 8 or any(not isinstance(tag, str) or len(tag) > 40 for tag in tags):
                raise ValueError("Item tags must be a list of up to eight short labels.")
            normalized_item: dict[str, Any] = {
                "id": str(item.get("id", f"item-{index}")),
                "name": name,
                "kind": kind,
                "tags": tags,
                "description": str(item.get("description", ""))[:300],
            }
            if kind == "Consumable":
                quantity = item.get("quantity", 1)
                if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 999:
                    raise ValueError("Consumable quantity must be from 1 to 999.")
                normalized_item["quantity"] = quantity
            elif kind == "Durable":
                maximum = item.get("max_durability", 10)
                durability = item.get("durability", maximum)
                if any(isinstance(value, bool) or not isinstance(value, int) for value in (maximum, durability)) or not 1 <= maximum <= 1000 or not 0 <= durability <= maximum:
                    raise ValueError("Durability must be between zero and a maximum from 1 to 1,000.")
                normalized_item["durability"] = durability
                normalized_item["max_durability"] = maximum
            normalized.append(normalized_item)
        return normalized

    def load_state(self, story_id: str) -> dict[str, Any]:
        """Read structured state, migrate a legacy sheet once, and refresh its view."""

        root = self.story_path(story_id)
        if not root.is_dir():
            raise FileNotFoundError("Story not found.")
        settings = self.read_settings(story_id)
        state = self.state_store.read(root / "state.json")
        if state is None:
            state = self._migrate_legacy_state(root, settings)
            self.state_store.write(root, state, WORLD_TEMPLATES[state["world_template"]]["resource"])
        else:
            state = self._normalize_existing_state(state, settings)
            if state != self.state_store.read(root / "state.json"):
                self.state_store.write(root, state, WORLD_TEMPLATES[state["world_template"]]["resource"])
            else:
                self.state_store.sync_summary(root, state, WORLD_TEMPLATES[state["world_template"]]["resource"])
        return state

    def save_state(self, story_id: str, state: dict[str, Any]) -> None:
        """Commit a state mutation and regenerate its Markdown summary afterward."""

        root = self.story_path(story_id)
        if not root.is_dir():
            raise FileNotFoundError("Story not found.")
        world_template = state["world_template"]
        self.state_store.write(root, state, WORLD_TEMPLATES[world_template]["resource"])

    def _normalize_existing_state(self, state: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
        """Apply schema defaults and reject invalid structured data without parsing Markdown."""

        world_template = str(state.get("world_template", settings["world_template"]))
        if world_template not in WORLD_TEMPLATES:
            world_template = settings["world_template"]
        candidate = self._new_character_state(
            world_template,
            {"identity": state.get("identity", {}), "stats": state.get("stats", {}), "inventory": state.get("inventory", [])},
            settings["realm_hierarchy"],
        )
        candidate["campaign_name"] = str(state.get("campaign_name", "Untitled Story"))[:60]
        candidate["setting_description"] = str(state.get("setting_description", "A new adventure begins."))[:2000]
        candidate["plot_pillars"] = self._normalize_string_list(state.get("plot_pillars", []), 12, 160)
        candidate["active_goals"] = self._normalize_string_list(state.get("active_goals", []), 40, 160)
        candidate["relationships"] = self._normalize_records(state.get("relationships", []), {"name": 80, "attitude": 40, "notes": 500}, 100)
        candidate["lore_bank"] = self._normalize_records(state.get("lore_bank", []), {"fact": 500, "source": 120}, 200)
        candidate["techniques"] = self._normalize_records(state.get("techniques", []), {"name": 100, "proficiency": 40, "description": 300}, 100)
        resource = state.get("resource", {})
        if isinstance(resource, dict):
            maximum = resource.get("maximum", 0)
            current = resource.get("current", 0)
            if all(isinstance(value, int) and not isinstance(value, bool) for value in (current, maximum)) and 0 <= current <= maximum:
                candidate["resource"] = {"current": current, "maximum": maximum}
        realm = state.get("realm_progress", {})
        if isinstance(realm, dict):
            current_realm = str(realm.get("current", candidate["realm_progress"]["current"]))
            hierarchy = settings["realm_hierarchy"]
            if current_realm in hierarchy:
                candidate["realm_progress"] = {
                    "current": current_realm,
                    "rank_index": hierarchy.index(current_realm),
                }
        candidate["schema_version"] = 1
        return candidate

    @staticmethod
    def _normalize_string_list(values: Any, maximum_items: int, maximum_length: int) -> list[str]:
        """Bound campaign lists loaded from hand-edited JSON before rendering them."""

        if not isinstance(values, list):
            return []
        return [str(value).strip()[:maximum_length] for value in values[:maximum_items] if str(value).strip()]

    @staticmethod
    def _normalize_records(values: Any, fields: dict[str, int], maximum_items: int) -> list[dict[str, str]]:
        """Bound model-suggested lore records so persisted state stays predictable."""

        if not isinstance(values, list):
            return []
        records = []
        for value in values[:maximum_items]:
            if isinstance(value, dict):
                record = {key: str(value.get(key, "")).strip()[:limit] for key, limit in fields.items()}
                if any(record.values()):
                    records.append(record)
        return records

    def _migrate_legacy_state(self, root: Path, settings: dict[str, Any]) -> dict[str, Any]:
        """Convert an older Markdown-only character sheet into structured JSON once."""

        template = settings["world_template"]
        legacy_path = root / "character_state.md"
        if not legacy_path.exists():
            legacy_path = root / "character.md"
        markdown = self.markdown.read_text(legacy_path)
        identity: dict[str, Any] = {}
        for key in ("name", "age", "background"):
            match = re.search(rf"^-\s*{re.escape(key)}:\s*(.+)$", markdown, re.IGNORECASE | re.MULTILINE)
            if match:
                identity[key] = int(match.group(1)) if key == "age" and match.group(1).isdigit() else match.group(1).strip()
        stat_labels = WORLD_TEMPLATES[template]["stats"]
        stats: dict[str, int] = {}
        for label in stat_labels:
            match = re.search(rf"^-\s*{re.escape(label)}:\s*(\d+)\s*$", markdown, re.IGNORECASE | re.MULTILINE)
            if match:
                stats[label] = max(MIN_STAT_VALUE, min(MAX_STAT_VALUE, int(match.group(1))))
        inventory_section = re.search(r"^## Inventory\s*\n([\s\S]*?)(?=^## |\Z)", markdown, re.MULTILINE | re.IGNORECASE)
        items: list[dict[str, Any]] = []
        if inventory_section:
            for line in inventory_section.group(1).splitlines():
                item_name = re.sub(r"^-\s*", "", line).strip()
                if item_name and item_name.casefold() != "(empty)":
                    items.append({"name": item_name, "kind": "Permanent", "tags": ["Permanent"]})
        state = self._new_character_state(
            template,
            {"identity": identity, "stats": stats, "inventory": items},
            settings["realm_hierarchy"],
        )
        story_text = self.markdown.read_text(root / "story.md", "# Untitled Story\n")
        state["campaign_name"] = next((line[2:].strip() for line in story_text.splitlines() if line.startswith("# ")), "Untitled Story")
        setting_match = re.search(r"^## Setting\s*\n+([\s\S]*?)(?=\n## |\Z)", story_text, re.MULTILINE)
        state["setting_description"] = setting_match.group(1).strip() if setting_match else "A new adventure begins."
        state["plot_pillars"] = self._legacy_list(root / "plot_pillars.md", "Plot Pillars")
        state["active_goals"] = self._legacy_list(root / "goals.md", "Active Goals")
        return state

    def _legacy_list(self, path: Path, heading: str) -> list[str]:
        """Recover a legacy Markdown list once before JSON becomes authoritative."""

        contents = self.markdown.read_text(path)
        section = re.search(rf"^#\s*{re.escape(heading)}\s*\n([\s\S]*)", contents, re.MULTILINE | re.IGNORECASE)
        if not section:
            return []
        return [line[2:].strip() for line in section.group(1).splitlines() if line.startswith("- ") and not line.startswith("- (No ") and line[2:].strip()]

    def update_item_usage(self, story_id: str, message: str) -> list[str]:
        """Apply explicit consumable use or durable damage before narrator context loads."""

        state = self.load_state(story_id)
        changes: list[str] = []
        consumable_actions = r"use|uses|using|used|consume|consumes|consuming|consumed|drink|drinks|drinking|drank|eat|eats|eating|ate|take|takes|taking|took|activate|activates|activated"
        damage_actions = r"damage|damages|damaged|wear|wears|wore|worn|break|breaks|broke|broken|strike|strikes|struck|hit|hits|parry|parries"
        for item in state["inventory"]:
            name_pattern = re.escape(item["name"])
            mention = re.search(rf"\b{name_pattern}(?:s)?\b", message, re.IGNORECASE)
            if not mention:
                continue
            nearby = message[max(0, mention.start() - 100):min(len(message), mention.end() + 100)]
            if re.search(r"\b(?:don't|do not|didn't|never|not)\b.{0,30}\b(?:use|consume|drink|eat|take|damage|break)\b", nearby, re.IGNORECASE):
                continue
            if item["kind"] == "Consumable" and re.search(rf"\b(?:{consumable_actions})\b", nearby, re.IGNORECASE):
                quantity_match = re.search(rf"\b(?:use|consume|drink|eat|take|activate)\s+(\d+)\s+(?:of\s+)?(?:the\s+)?{name_pattern}", message, re.IGNORECASE)
                requested = int(quantity_match.group(1)) if quantity_match else 1
                used = min(requested, item["quantity"])
                if used:
                    item["quantity"] -= used
                    changes.append(f"Used {used} {item['name']}; {item['quantity']} remaining.")
            elif item["kind"] == "Durable" and re.search(rf"\b(?:{damage_actions})\b", nearby, re.IGNORECASE):
                if item["durability"] > 0:
                    item["durability"] -= 1
                    condition = "broken" if item["durability"] == 0 else f"durability {item['durability']}/{item['max_durability']}"
                    changes.append(f"{item['name']} was damaged; {condition}.")
        if changes:
            self.save_state(story_id, state)
        return changes

    def apply_narrative_updates(self, story_id: str, updates: dict[str, Any]) -> list[str]:
        """Persist bounded NPC, lore, and technique facts returned with a narrator turn."""

        state = self.load_state(story_id)
        changed: list[str] = []
        mapping = {
            "relationships": ("name", {"Friendly", "Neutral", "Wary", "Hostile", "Unknown"}),
            "lore_bank": ("fact", None),
            "techniques": ("name", {"Untrained", "Novice", "Practiced", "Proficient", "Mastered"}),
        }
        for collection, (identity_key, allowed_values) in mapping.items():
            incoming = updates.get(collection, [])
            if not isinstance(incoming, list):
                continue
            current = state[collection]
            index = {str(item.get(identity_key, "")).casefold(): position for position, item in enumerate(current)}
            for item in incoming[:20]:
                if not isinstance(item, dict) or not str(item.get(identity_key, "")).strip():
                    continue
                normalized = self._normalize_records([item], {
                    field: limit for field, limit in (
                        ("name", 100), ("attitude", 40), ("notes", 500),
                        ("fact", 500), ("source", 120), ("proficiency", 40),
                        ("description", 300),
                    ) if field in item
                }, 1)
                if not normalized:
                    continue
                record = normalized[0]
                if allowed_values:
                    property_name = "attitude" if collection == "relationships" else "proficiency"
                    if record.get(property_name) not in allowed_values:
                        continue
                key = record[identity_key].casefold()
                if key in index:
                    current[index[key]].update(record)
                else:
                    current.append(record)
                    index[key] = len(current) - 1
                changed.append(record[identity_key])
        if changed:
            self.save_state(story_id, state)
        return changed

    def list_stories(self) -> list[dict[str, str]]:
        """Expose story ids and friendly names without returning local paths."""

        stories: list[dict[str, str]] = []
        for directory in sorted(self.stories_dir.iterdir(), key=lambda item: item.name):
            if not directory.is_dir() or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", directory.name):
                continue
            try:
                state = self.state_store.read(directory / "state.json")
                if state is None:
                    state = self.load_state(directory.name)
                first_line = str(state.get("campaign_name", directory.name))
            except ValueError:
                first_line = directory.name
            stories.append({"id": directory.name, "name": first_line})
        return stories

    def load_story(self, story_id: str) -> dict[str, Any]:
        """Return the public story documents needed to restore the play screen."""

        root = self.story_path(story_id)
        if not root.is_dir():
            raise FileNotFoundError("Story not found.")
        state = self.load_state(story_id)
        character = self.markdown.read_text(root / "character_state.md")
        return {
            "id": story_id,
            "name": state["campaign_name"],
            "character": character,
            "state": state,
            "goals": self.markdown.read_text(root / "goals.md", DEFAULT_GOALS),
            "plot_pillars": self.markdown.read_text(root / "plot_pillars.md", "# Plot Pillars\n\n- (No plot pillars chosen yet)\n"),
            "setting_description": state["setting_description"],
            "settings": self.read_settings(story_id),
            "recent_history": self.recent_session_text(story_id),
        }

    def read_settings(self, story_id: str) -> dict[str, Any]:
        """Load settings with safe defaults if a file is missing or malformed."""

        path = self.story_path(story_id) / "settings.json"
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        settings = {**DEFAULT_SETTINGS, **{key: value for key, value in stored.items() if key in DEFAULT_SETTINGS}}
        if settings["world_template"] not in WORLD_TEMPLATES:
            settings["world_template"] = DEFAULT_SETTINGS["world_template"]
        if not isinstance(stored.get("realm_hierarchy"), list) or not 2 <= len(stored["realm_hierarchy"]) <= 100:
            settings["realm_hierarchy"] = list(WORLD_TEMPLATES[settings["world_template"]]["realms"])
        if settings.get("highest_power_level") not in settings["realm_hierarchy"]:
            settings["highest_power_level"] = settings["realm_hierarchy"][-1]
        if settings["world_power_level"] not in {"Low", "Medium", "High/Cosmic"}:
            settings["world_power_level"] = DEFAULT_SETTINGS["world_power_level"]
        if settings["mode"] == "Dice":
            settings["mode"] = "Dice-heavy"
        elif settings["mode"] == "Narrative":
            settings["mode"] = "Narrative-heavy"
        if settings["tone"] not in {"Grim", "Heroic", "Mystery", "Gritty", "Mysterious", "Dark", "Whimsical", "Philosophical"}:
            settings["tone"] = "Heroic"
        if settings.get("difficulty") not in {"Easy", "Moderate", "Hard"}:
            settings["difficulty"] = "Moderate"
        try:
            validated = self._validate_world_settings(settings["world_template"], settings)
            validated["difficulty"] = settings["difficulty"]
            settings.update(validated)
        except ValueError:
            fallback = self._validate_world_settings(settings["world_template"], {})
            fallback["difficulty"] = settings["difficulty"]
            settings.update(fallback)
        return settings

    def write_settings(self, story_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        """Persist only supported preference fields to keep config predictable."""

        allowed = {key: settings[key] for key in DEFAULT_SETTINGS if key in settings}
        current = self.read_settings(story_id) if self.story_path(story_id).is_dir() else DEFAULT_SETTINGS.copy()
        merged = {**current, **allowed}
        normalized = self._validate_world_settings(merged["world_template"], merged)
        normalized["difficulty"] = merged.get("difficulty", "Moderate")
        path = self.story_path(story_id) / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return normalized

    def recent_session_text(self, story_id: str, limit: int = 12) -> str:
        """Read recent events in chronological order for gameplay or recap context."""

        sessions_dir = self.story_path(story_id) / "sessions"
        paths = sorted(sessions_dir.glob("session_*.md"))
        events: list[str] = []
        for path in paths:
            contents = path.read_text(encoding="utf-8")
            events.extend(re.split(r"(?=^## )", contents, flags=re.MULTILINE))
        recent_events = [event.strip() for event in events if event.strip()][-max(1, limit):]
        return "\n\n".join(recent_events)

    def count_conversation_turns(self, story_id: str) -> int:
        """Count saved player turns to schedule world ticks and session breaks."""

        sessions_dir = self.story_path(story_id) / "sessions"
        return sum(
            len(re.findall(r"(?m)^## Conversation turn\s*$", path.read_text(encoding="utf-8")))
            for path in sorted(sessions_dir.glob("session_*.md"))
        )

    def append_event(self, story_id: str, heading: str, content: str) -> Path:
        """Route a log event to the checked story's session folder."""

        root = self.story_path(story_id)
        if not root.is_dir():
            raise FileNotFoundError("Story not found.")
        return self.markdown.append_event(root / "sessions", heading, content)
