"""Automation service orchestrating repositories and utilities for content automation."""

import asyncio
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Callable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

from app.backend.config.settings import AppSettings
from app.backend.entities.ai_models import ConceptList, ThumbnailConcept
from app.backend.entities.project import ProjectState
from app.backend.repositories.file_repo import FileRepo
from app.backend.repositories.gdrive_repo import GoogleDriveRepo
from app.backend.repositories.gemini_repo import GeminiRepo
from app.backend.repositories.notebooklm_repo import NotebookLMRepo
from app.backend.utils.ffmpeg_wrapper import FFmpegWrapper
from app.backend.utils.prompt_manager import PromptManager


def clean_summary(summary: Optional[str]) -> str:
    """Clean markdown artifacts, citations, and excessive whitespace from summary text."""
    if not summary:
        return ""
    # Strip markdown formatting characters
    cleaned = summary.strip().replace("*", "").replace("#", "").replace("---", "")
    # Remove citations like [1] or [1, 2]
    cleaned = re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", "", cleaned)

    # Collapse 3+ newlines to 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


class AutomationService:
    """Orchestrates end-to-end content processing across repositories and utilities."""

    def __init__(
        self,
        file_repo: Optional[FileRepo] = None,
        gdrive_repo: Optional[GoogleDriveRepo] = None,
        notebooklm_repo: Optional[NotebookLMRepo] = None,
        gemini_repo: Optional[GeminiRepo] = None,
        prompt_manager: Optional[PromptManager] = None,
        ffmpeg_wrapper: Optional[FFmpegWrapper] = None,
        bgm_path: Optional[str] = None,
        resources_dir: Optional[str] = None,
    ) -> None:
        """Initialize AutomationService with repository and utility dependencies."""
        self._file_repo = file_repo or FileRepo()
        self._gdrive_repo = gdrive_repo or GoogleDriveRepo()
        self._prompt_manager = prompt_manager or PromptManager()
        self._notebooklm_repo = notebooklm_repo or NotebookLMRepo(
            prompt_manager=self._prompt_manager
        )
        self._gemini_repo = gemini_repo or GeminiRepo()

        self._ffmpeg_wrapper = ffmpeg_wrapper or FFmpegWrapper()
        self._bgm_path = bgm_path or AppSettings.load().SHORTS_BGM_PATH
        self._resources_dir = resources_dir or AppSettings.load().RESOURCES_DIR
        self._background_tasks: Set[asyncio.Task] = set()

    async def _safe_generate_image(self, prompt: str, out_file: str) -> Optional[str]:
        """Safely execute image generation, catching and logging errors without unhandled exceptions."""
        try:
            return await self._gemini_repo.generate_image(prompt, out_file)
        except Exception as exc:
            logger.error("Failed to generate image at %s: %s", out_file, exc)
            return None

    async def generate_notebooklm_artifacts(
        self, drive_link: str, themes: List[str]
    ) -> ProjectState:
        """Download audio, setup project env, and generate NotebookLM summary and hashtags.

        Args:
            drive_link: Google Drive URL to the source audio.
            themes: List of creative themes.

        Returns:
            Populated ProjectState with project directory, audio, summary, and hashtags.
        """
        # 1. Download audio via GoogleDriveRepo and extract filename
        downloaded_path = Path(
            self._gdrive_repo.download_audio(drive_link, str(self._file_repo._base_dir))
        )
        filename = downloaded_path.name

        # 2. Setup project environment via FileRepo
        project_dir_str = self._file_repo.create_project_env(filename)
        project_dir = Path(project_dir_str)
        final_audio_path = project_dir / filename

        # Relocate audio to project directory if needed
        if (
            downloaded_path.resolve() != final_audio_path.resolve()
            and downloaded_path.exists()
        ):
            project_dir.mkdir(parents=True, exist_ok=True)
            downloaded_path.replace(final_audio_path)
            target_audio_str = str(final_audio_path.resolve())
        elif downloaded_path.exists():
            target_audio_str = str(downloaded_path.resolve())
        else:
            target_audio_str = str(final_audio_path.resolve())

        # 3. Concurrently await NotebookLM summary and hashtags
        raw_summary, hashtags = await asyncio.gather(
            self._notebooklm_repo.generate_summary(target_audio_str),
            self._notebooklm_repo.generate_hashtags(target_audio_str),
        )
        summary = clean_summary(raw_summary)

        # 4. Save summary as v1_auto.md via FileRepo
        self._file_repo.save_text_version(summary, "v1_auto.md", str(project_dir))

        return ProjectState(
            project_dir=str(project_dir.resolve()),
            audio_path=target_audio_str,
            summary_v1=summary,
            themes=list(themes),
            selected_hashtags=hashtags,
        )

    async def generate_infographics(
        self, state: ProjectState, n_infographics: int = 3
    ) -> List[str]:
        """Generate infographic images for the project summary.

        Args:
            state: Populated ProjectState with project_dir and summary_v1.
            n_infographics: Number of infographic variations to generate.

        Returns:
            List of generated infographic file paths.
        """
        if not state.project_dir:
            raise ValueError("No active project directory in ProjectState.")

        prompt = self._prompt_manager.get_infographic_prompt(state.summary_v1)
        infographics_dir = Path(state.project_dir) / "infographics"
        infographics_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        out_paths: List[str] = []
        for i in range(1, n_infographics + 1):
            out_path = infographics_dir / f"infographic_{i}.png"
            out_file = str(out_path.resolve())
            out_paths.append(out_file)
            tasks.append(self._safe_generate_image(prompt, out_file))

        await asyncio.gather(*tasks)
        return out_paths

    async def generate_thumbnails(self, state: ProjectState) -> List[str]:
        """Generate concept list and thumbnails in parallel with Gemini.

        Args:
            state: Populated ProjectState with selected infographic path.

        Returns:
            List of generated thumbnail image file paths.
        """
        if not state.selected_infographic_path:
            raise ValueError("No selected infographic found in project state.")

        concept_prompts: List[str] = [
            self._prompt_manager.get_concept_prompt(state.summary_v1, theme=None)
        ]
        for theme in state.themes:
            concept_prompts.append(
                self._prompt_manager.get_concept_prompt(state.summary_v1, theme=theme)
            )

        concept_lists: List[ConceptList] = await asyncio.gather(
            *[
                self._gemini_repo.generate_structured_concepts(
                    prompt, state.selected_infographic_path
                )
                for prompt in concept_prompts
            ]
        )

        flattened_concepts: List[ThumbnailConcept] = []
        for cl in concept_lists:
            flattened_concepts.extend(cl.concepts)

        thumbnails_dir = Path(state.project_dir) / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_tasks = []
        thumbnail_paths: List[str] = []

        for i, concept in enumerate(flattened_concepts, 1):
            out_path = str((thumbnails_dir / f"thumbnail_{i}.png").resolve())
            thumbnail_paths.append(out_path)
            thumb_prompt = self._prompt_manager.get_thumbnail_prompt(
                concept.model_dump(), state.selected_infographic_path
            )
            thumbnail_tasks.append(
                self._gemini_repo.generate_image(thumb_prompt, out_path)
            )

        await asyncio.gather(*thumbnail_tasks)
        return thumbnail_paths

    async def create_final_video(self, state: ProjectState) -> str:
        """Compose 16:9 MP4 video using selected infographic and audio track.

        Args:
            state: Populated ProjectState with selected infographic and audio.

        Returns:
            File path of the generated final video.
        """
        if not state.selected_infographic_path:
            raise ValueError("No selected infographic found in project state.")
        project_path = Path(state.project_dir)
        final_video_path = str((project_path / "final_video.mp4").resolve())
        await self._ffmpeg_wrapper.create_final_video(
            state.selected_infographic_path, state.audio_path, final_video_path
        )
        return final_video_path

    async def create_short_video(self, state: ProjectState) -> str:
        """Compose 9:16 short video using selected infographic and background music.

        Args:
            state: Populated ProjectState with selected infographic.

        Returns:
            File path of the generated shorts video.
        """
        if not state.selected_infographic_path:
            raise ValueError("No selected infographic found in project state.")
        project_path = Path(state.project_dir)
        resources_dir_path = Path(self._resources_dir)
        shorts_bgm_file = resources_dir_path / "shorts_bgm_dont_delete.m4a"

        if self._bgm_path:
            bgm_track = self._bgm_path
            shorts_video_name = "shorts_video.mp4"
        elif shorts_bgm_file.exists():
            bgm_track = str(shorts_bgm_file.resolve())
            shorts_video_name = "shorts_video_fancy.mp4"
        else:
            bgm_track = state.audio_path
            shorts_video_name = "shorts_video.mp4"

        shorts_video_path = str((project_path / shorts_video_name).resolve())
        await self._ffmpeg_wrapper.create_short_video(
            state.selected_infographic_path, bgm_track, shorts_video_path
        )

        fancy_src = resources_dir_path / "shorts_video_fancy.mp4"
        effective_shorts_path = shorts_video_path
        if fancy_src.exists():
            fancy_dest = project_path / "shorts_video_fancy.mp4"
            shutil.copy2(fancy_src, fancy_dest)
            effective_shorts_path = str(fancy_dest.resolve())

        return effective_shorts_path

    async def create_short_thumbnail(self, state: ProjectState) -> str:
        """Produce a 9:16 thumbnail from the user's selected 16:9 thumbnail.

        Args:
            state: Populated ProjectState with selected_thumbnail_path.

        Returns:
            File path of the generated 9:16 short thumbnail.

        Raises:
            ValueError: If selected_thumbnail_path is empty.
        """
        if not state.selected_thumbnail_path:
            raise ValueError("No selected thumbnail found in project state.")

        project_path = Path(state.project_dir)
        shorts_thumb_path = str((project_path / "shorts_thumbnail.png").resolve())
        await self._ffmpeg_wrapper.create_short_thumbnail(
            state.selected_thumbnail_path, shorts_thumb_path
        )
        return shorts_thumb_path

    async def phase_1_process(
        self, drive_link: str, themes: List[str], n_infographics: int
    ) -> Tuple[ProjectState, List[str]]:
        """Execute Phase 1: audio ingestion, summary, hashtags, and early infographic tasks.

        Args:
            drive_link: Google Drive URL to the source audio.
            themes: List of creative themes for downstream thumbnail concept generation.
            n_infographics: Number of background infographic images to spawn.

        Returns:
            Tuple of populated ProjectState and list of infographic placeholder paths.
        """
        state = await self.generate_notebooklm_artifacts(drive_link, themes)
        project_dir = Path(state.project_dir)
        infographics_dir = project_dir / "infographics"
        infographics_dir.mkdir(parents=True, exist_ok=True)
        placeholders: List[str] = []

        placeholder_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
            b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        prompt = self._prompt_manager.get_infographic_prompt(state.summary_v1)

        for i in range(1, n_infographics + 1):
            out_path = infographics_dir / f"infographic_{i}.png"
            if not out_path.exists():
                out_path.write_bytes(placeholder_png)
            out_file = str(out_path.resolve())
            placeholders.append(out_file)
            task = asyncio.create_task(
                self._safe_generate_image(prompt, out_file)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return state, placeholders

    async def phase_2_process(
        self,
        state: ProjectState,
        progress_callback: Optional[Callable[[float, str], Any]] = None,
    ) -> List[str]:
        """Execute Phase 2: concept math, thumbnail generation, and video composition.

        Args:
            state: Populated ProjectState with selected infographic path.
            progress_callback: Optional callback receiving (progress_pct: float, message: str).

        Returns:
            List of file paths for all generated assets (thumbnails, video, shorts).

        Raises:
            ValueError: If state.selected_infographic_path is empty.
        """
        if not state.selected_infographic_path:
            raise ValueError(
                "No selected infographic found in project state. Select an infographic before Phase 2."
            )

        if progress_callback:
            progress_callback(
                0.1, "Generating creative thumbnail concepts with Gemini..."
            )

        thumbnail_paths = await self.generate_thumbnails(state)

        if progress_callback:
            progress_callback(
                0.65, "Rendering final 16:9 video and 9:16 shorts with FFmpeg..."
            )

        project_path = Path(state.project_dir)
        shorts_thumb_path = str((project_path / "shorts_thumbnail.png").resolve())
        thumb_source = state.selected_thumbnail_path or state.selected_infographic_path

        final_vid, short_vid, _ = await asyncio.gather(
            self.create_final_video(state),
            self.create_short_video(state),
            self._ffmpeg_wrapper.create_short_thumbnail(
                thumb_source, shorts_thumb_path
            ),
        )

        if progress_callback:
            progress_callback(1.0, "All video deliverables rendered.")

        return [
            *thumbnail_paths,
            final_vid,
            short_vid,
            shorts_thumb_path,
        ]
