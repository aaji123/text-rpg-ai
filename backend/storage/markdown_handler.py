"""Read and write Markdown safely so story history remains portable and legible."""

from datetime import datetime, timezone
from pathlib import Path


class MarkdownHandler:
    """Centralize file operations so all persisted story text uses one format."""

    def read_text(self, path: Path, default: str = "") -> str:
        """Return readable UTF-8 content, using a default for not-yet-created files."""

        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return default

    def write_text(self, path: Path, content: str) -> None:
        """Replace a Markdown document atomically to avoid partial story files."""

        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(content.rstrip() + "\n", encoding="utf-8")
        temporary_path.replace(path)

    def append_event(self, sessions_dir: Path, heading: str, content: str) -> Path:
        """Save one complete event in its own UTC-stamped log for simple recovery."""

        sessions_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc)
        stamp = timestamp.strftime("%Y-%m-%d")
        path = sessions_dir / f"session_{stamp}.md"
        body = f"\n## {heading}\n\n_Timestamp: {timestamp.isoformat()}_\n\n{content.strip()}\n"
        with path.open("a", encoding="utf-8") as session_file:
            session_file.write(body)
            session_file.flush()
        return path
