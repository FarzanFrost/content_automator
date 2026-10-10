"""Automation service orchestrating repositories and utilities for content automation."""

import asyncio
from pathlib import Path
from typing import List, Optional, Set, Tuple

from app.backend.config.settings import AppSettings
from app.backend.entities.ai_models import ConceptList, ThumbnailConcept
from app.backend.entities.project import ProjectState
from app.backend.repositories.file_repo import FileRepo
from app.backend.repositories.gdrive_repo import GoogleDriveRepo
from app.backend.repositories.gemini_repo import GeminiRepo
from app.backend.repositories.notebooklm_repo import NotebookLMRepo
from app.backend.utils.ffmpeg_wrapper import FFmpegWrapper
from app.backend.utils.prompt_manager import PromptManager


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
    ) -> None:
        """Initialize AutomationService with repository and utility dependencies."""
        self._file_repo = file_repo or FileRepo()
        self._gdrive_repo = gdrive_repo or GoogleDriveRepo()
        self._notebooklm_repo = notebooklm_repo or NotebookLMRepo()
        self._gemini_repo = gemini_repo or GeminiRepo()
        self._prompt_manager = prompt_manager or PromptManager()
        self._ffmpeg_wrapper = ffmpeg_wrapper or FFmpegWrapper()
        self._bgm_path = bgm_path or AppSettings.load().SHORTS_BGM_PATH
        self._background_tasks: Set[asyncio.Task] = set()

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
        # 1. Download audio via GoogleDriveRepo and extract filename
        downloaded_path = Path(
            self._gdrive_repo.download_audio(
                drive_link, str(self._file_repo._base_dir)
            )
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
        summary, hashtags = await asyncio.gather(
            self._notebooklm_repo.generate_summary(target_audio_str),
            self._notebooklm_repo.generate_hashtags(target_audio_str),
        )

        # 4. Save summary as v1_auto.md via FileRepo
        self._file_repo.save_text_version(summary, "v1_auto.md", str(project_dir))

        # 5. EARLY EXECUTION: Spawn n_infographics non-blocking tasks via GeminiRepo
        prompt = self._prompt_manager.get_infographic_prompt(summary)
        infographics_dir = project_dir / "infographics"
        placeholders: List[str] = []

        for i in range(1, n_infographics + 1):
            out_file = str((infographics_dir / f"infographic_{i}.png").resolve())
            placeholders.append(out_file)
            task = asyncio.create_task(
                self._gemini_repo.generate_image(prompt, out_file)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        state = ProjectState(
            project_dir=str(project_dir.resolve()),
            audio_path=target_audio_str,
            summary_v1=summary,
            themes=list(themes),
            selected_hashtags=hashtags,
        )

        return state, placeholders

    async def phase_2_process(self, state: ProjectState) -> List[str]:
        """Execute Phase 2: concept math, thumbnail generation, and video composition.

        Args:
            state: Populated ProjectState with selected infographic path.

        Returns:
            List of file paths for all generated assets (thumbnails, video, shorts).

        Raises:
            ValueError: If state.selected_infographic_path is empty.
        """
        if not state.selected_infographic_path:
            raise ValueError(
                "No selected infographic found in project state. Select an infographic before Phase 2."
            )

        # 1. Concept Math: execute concept generation prompt k+1 times concurrently
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

        # 2. Flatten result to 3 * (k + 1) concepts
        flattened_concepts: List[ThumbnailConcept] = []
        for cl in concept_lists:
            flattened_concepts.extend(cl.concepts)

        # 3. Image Math: Concurrently generate thumbnails for every concept
        thumbnails_dir = Path(state.project_dir) / "thumbnails"
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

        # 4. Video Math: Call FFmpegWrapper using selected infographic as visual input
        project_path = Path(state.project_dir)
        final_video_path = str((project_path / "final_video.mp4").resolve())
        shorts_video_path = str((project_path / "shorts_video.mp4").resolve())
        shorts_thumb_path = str((project_path / "shorts_thumbnail.png").resolve())

        bgm_track = self._bgm_path or state.audio_path

        await asyncio.gather(
            self._ffmpeg_wrapper.create_final_video(
                state.selected_infographic_path, state.audio_path, final_video_path
            ),
            self._ffmpeg_wrapper.create_short_video(
                state.selected_infographic_path, bgm_track, shorts_video_path
            ),
            self._ffmpeg_wrapper.create_short_thumbnail(
                state.selected_infographic_path, shorts_thumb_path
            ),
        )

        return [
            *thumbnail_paths,
            final_video_path,
            shorts_video_path,
            shorts_thumb_path,
        ]
