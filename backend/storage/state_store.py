"""Persist structured character data and derive its readable Markdown view."""

import json
from pathlib import Path
from typing import Any


class StateStore:
    """Keep JSON authoritative while maintaining a generated character summary."""

    def read(self, path: Path) -> dict[str, Any] | None:
        """Load one character state document, distinguishing missing from invalid."""

        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as error:
            raise ValueError("This story's state.json is invalid; restore it from a backup.") from error
        if not isinstance(state, dict):
            raise ValueError("This story's state.json must contain a JSON object.")
        return state

    def write(self, story_dir: Path, state: dict[str, Any], resource_label: str) -> None:
        """Commit canonical JSON first, then regenerate the human-readable sheet."""

        story_dir.mkdir(parents=True, exist_ok=True)
        json_path = story_dir / "state.json"
        temporary_path = story_dir / "state.json.tmp"
        temporary_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary_path.replace(json_path)
        self.sync_summary(story_dir, state, resource_label)

    def sync_summary(self, story_dir: Path, state: dict[str, Any], resource_label: str) -> None:
        """Refresh the derived Markdown view without rewriting authoritative JSON."""

        documents = {
            "character_state.md": self.render_markdown(state, resource_label),
            "story.md": self.render_story(state),
            "plot_pillars.md": self.render_list("Plot Pillars", state.get("plot_pillars", []), "No plot pillars chosen yet"),
            "goals.md": self.render_list("Active Goals", state.get("active_goals", []), "No active goals yet"),
        }
        for filename, contents in documents.items():
            self._write_if_changed(story_dir / filename, contents)

    @staticmethod
    def render_story(state: dict[str, Any]) -> str:
        """Render campaign identity and its starting premise from structured data."""

        title = StateStore._clean(state.get("campaign_name", "Untitled Story"))
        setting = StateStore._clean(state.get("setting_description", "A new adventure begins."))
        return f"# {title}\n\n## Setting\n\n{setting}\n"

    @staticmethod
    def render_list(title: str, items: Any, empty_message: str) -> str:
        """Keep list documents derived so edits to state JSON remain authoritative."""

        values = [StateStore._clean(item) for item in items if str(item).strip()] if isinstance(items, list) else []
        lines = [f"# {title}", ""] + ([f"- {value}" for value in values] or [f"- ({empty_message})"])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _write_if_changed(path: Path, contents: str) -> None:
        """Avoid unnecessary disk writes while keeping each generated view consistent."""

        try:
            if path.read_text(encoding="utf-8") == contents:
                return
        except FileNotFoundError:
            pass
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(contents, encoding="utf-8")
        temporary_path.replace(path)

    @staticmethod
    def render_markdown(state: dict[str, Any], resource_label: str) -> str:
        """Turn structured state into a stable sheet whose format never drives logic."""

        identity = state.get("identity", {})
        stats = state.get("stats", {})
        realm = state.get("realm_progress", {})
        inventory = state.get("inventory", [])
        lines = [
            "# Character Sheet",
            "",
            "## Identity",
            f"- Name: {StateStore._clean(identity.get('name', 'Adventurer'))}",
            f"- Age: {identity.get('age', 18)}",
            f"- Background: {StateStore._clean(identity.get('background', 'Unchosen'))}",
            f"- Realm: {StateStore._clean(realm.get('current', 'Unranked'))}",
            "",
            "## Stats",
        ]
        lines.extend(f"- {StateStore._clean(label)}: {value}" for label, value in stats.items())
        lines.extend(["", f"## {StateStore._clean(resource_label)}"])
        resource = state.get("resource", {})
        lines.extend([f"- Current: {resource.get('current', 0)}", f"- Maximum: {resource.get('maximum', 0)}", "", "## Inventory"])
        if inventory:
            for item in inventory:
                label = f"- {StateStore._clean(item.get('name', 'Unnamed item'))} ({StateStore._clean(item.get('kind', 'Permanent'))})"
                if item.get("kind") == "Consumable":
                    label += f" — Quantity: {item.get('quantity', 0)}"
                elif item.get("kind") == "Durable":
                    label += f" — Durability: {item.get('durability', 0)}/{item.get('max_durability', 0)}"
                tags = item.get("tags", [])
                if tags:
                    label += f" — Tags: {', '.join(StateStore._clean(tag) for tag in tags)}"
                lines.append(label)
        else:
            lines.append("- (empty)")
        for title, key, display_key in (
            ("Relationships", "relationships", "name"),
            ("Lore Bank", "lore_bank", "fact"),
            ("Technique Library", "techniques", "name"),
        ):
            lines.extend(["", f"## {title}"])
            entries = state.get(key, [])
            if not entries:
                lines.append("- (empty)")
                continue
            for entry in entries:
                summary = StateStore._clean(entry.get(display_key, ""))
                details = [StateStore._clean(value) for name, value in entry.items() if name != display_key and value]
                lines.append(f"- {summary}" + (f" — {'; '.join(details)}" if details else ""))
        return "\n".join(lines) + "\n"

    @staticmethod
    def _clean(value: Any) -> str:
        """Keep generated Markdown fields on one line and avoid broken table syntax."""

        return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()
