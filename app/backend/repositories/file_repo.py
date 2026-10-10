"""Local filesystem repository handling project directory and file operations."""

from pathlib import Path
from typing import Optional

from app.backend.config.settings import AppSettings


class FileRepo:
    """Repository managing local workspace paths, assets, and text outputs."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        """Initialize FileRepo with default or configured output directory."""
        if base_dir:
            self._base_dir = Path(base_dir)
        else:
            configured_dir = AppSettings.load().BASE_OUTPUT_DIR
            self._base_dir = (
                Path(configured_dir) if configured_dir else Path.cwd() / "output"
            )

    def create_project_env(
        self, audio_filename: str, base_dir: Optional[str] = None
    ) -> str:
        """Create parent directory and required subdirectories for audio project."""
        parent_base = Path(base_dir) if base_dir else self._base_dir
        project_name = Path(audio_filename).stem
        project_dir = parent_base / project_name

        infographics_dir = project_dir / "infographics"
        thumbnails_dir = project_dir / "thumbnails"

        project_dir.mkdir(parents=True, exist_ok=True)
        infographics_dir.mkdir(parents=True, exist_ok=True)
        thumbnails_dir.mkdir(parents=True, exist_ok=True)

        return str(project_dir.resolve())

    def save_text_version(self, content: str, version: str, dir_path: str) -> str:
        """Save text content to markdown file within specified directory."""
        target_dir = Path(dir_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = version if version.endswith(".md") else f"{version}.md"
        file_path = target_dir / filename

        # Atomic write to temporary file then replace to avoid corruption
        temp_path = target_dir / f".tmp_{filename}"
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(file_path)

        return str(file_path.resolve())
