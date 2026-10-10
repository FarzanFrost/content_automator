"""Session state data model for Gradio lifecycle."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ProjectState:
    """Holds active session state across the Gradio UI lifecycle."""

    project_dir: str = ""
    audio_path: str = ""
    summary_v1: str = ""
    themes: List[str] = field(default_factory=list)
    selected_hashtags: List[str] = field(default_factory=list)
    selected_infographic_path: str = ""

    def reset(self) -> None:
        """Reset state back to initial empty session values."""
        self.project_dir = ""
        self.audio_path = ""
        self.summary_v1 = ""
        self.themes.clear()
        self.selected_hashtags.clear()
        self.selected_infographic_path = ""
