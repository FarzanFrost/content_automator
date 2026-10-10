"""Tests for AutomationService orchestrating content pipeline workflows."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from app.backend.entities.ai_models import ConceptList, ThumbnailConcept
from app.backend.entities.project import ProjectState
from app.backend.services.automation_service import AutomationService


class TestAutomationService(unittest.IsolatedAsyncioTestCase):
    """Test suite for AutomationService orchestration logic."""

    def setUp(self) -> None:
        """Create temporary test directory and mocked repository/utility instances."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

        self.file_repo = MagicMock()
        self.file_repo._base_dir = self.tmp_path / "base"
        self.file_repo.create_project_env.return_value = str(
            self.tmp_path / "khutbah_1"
        )
        self.file_repo.save_text_version.return_value = str(
            self.tmp_path / "khutbah_1" / "v1_auto.md"
        )

        self.gdrive_repo = MagicMock()
        self.gdrive_repo.download_audio.return_value = str(
            self.tmp_path / "khutbah_1.mp3"
        )

        self.notebooklm_repo = MagicMock()
        self.notebooklm_repo.generate_summary = AsyncMock(
            return_value="Detailed sermon summary."
        )
        self.notebooklm_repo.generate_hashtags = AsyncMock(
            return_value=["#Khutbah", "#Islam", "#Faith"]
        )

        self.gemini_repo = MagicMock()
        self.gemini_repo.generate_image = AsyncMock(side_effect=lambda prompt, out: out)

        def mock_concepts(prompt, image_path):
            concept = ThumbnailConcept(
                category="Spiritual",
                visual_hook="Glowing minaret",
                design_directive="Golden ratio layout",
                text_hook="Wake Up Before It's Too Late",
                color_theory="Deep indigo and gold",
            )
            return ConceptList(concepts=[concept, concept, concept])

        self.gemini_repo.generate_structured_concepts = AsyncMock(
            side_effect=mock_concepts
        )

        self.prompt_manager = MagicMock()
        self.prompt_manager.get_infographic_prompt.return_value = (
            "Infographic prompt text"
        )
        self.prompt_manager.get_concept_prompt.return_value = "Concept prompt text"
        self.prompt_manager.get_thumbnail_prompt.return_value = "Thumbnail prompt text"

        self.ffmpeg_wrapper = MagicMock()
        self.ffmpeg_wrapper.create_final_video = AsyncMock()
        self.ffmpeg_wrapper.create_short_video = AsyncMock()
        self.ffmpeg_wrapper.create_short_thumbnail = AsyncMock()

    def tearDown(self) -> None:
        """Clean up temporary test directory."""
        self.temp_dir.cleanup()

    async def test_phase_1_process_success(self) -> None:
        """Verify Phase 1 downloads audio, sets up env, summarizes, and spawns infographic tasks."""
        test_audio = self.tmp_path / "audio.mp3"
        test_audio.write_text("dummy audio")

        self.gdrive_repo.download_audio.return_value = str(test_audio)
        project_dir = self.tmp_path / "project_audio"
        self.file_repo.create_project_env.return_value = str(project_dir)

        service = AutomationService(
            file_repo=self.file_repo,
            gdrive_repo=self.gdrive_repo,
            notebooklm_repo=self.notebooklm_repo,
            gemini_repo=self.gemini_repo,
            prompt_manager=self.prompt_manager,
            ffmpeg_wrapper=self.ffmpeg_wrapper,
        )

        drive_link = "https://drive.google.com/file/d/test1234/view"
        themes = ["Tawheed", "Tawbah"]
        n_infographics = 3

        state, placeholders = await service.phase_1_process(
            drive_link=drive_link, themes=themes, n_infographics=n_infographics
        )

        # Verify ProjectState
        self.assertEqual(state.project_dir, str(project_dir.resolve()))
        self.assertEqual(Path(state.audio_path).name, "audio.mp3")
        self.assertEqual(state.summary_v1, "Detailed sermon summary.")
        self.assertEqual(state.themes, ["Tawheed", "Tawbah"])
        self.assertEqual(state.selected_hashtags, ["#Khutbah", "#Islam", "#Faith"])

        # Verify FileRepo interactions
        self.gdrive_repo.download_audio.assert_called_once()
        self.file_repo.create_project_env.assert_called_once_with("audio.mp3")
        self.file_repo.save_text_version.assert_called_once_with(
            "Detailed sermon summary.", "v1_auto.md", str(project_dir)
        )

        # Verify NotebookLM concurrency
        self.notebooklm_repo.generate_summary.assert_called_once_with(state.audio_path)
        self.notebooklm_repo.generate_hashtags.assert_called_once_with(state.audio_path)

        # Verify Infographics early execution placeholders and background tasks
        self.assertEqual(len(placeholders), 3)
        for i, path in enumerate(placeholders, 1):
            self.assertTrue(path.endswith(f"infographic_{i}.png"))

        # Let background tasks complete
        await asyncio.sleep(0.05)
        self.assertEqual(self.gemini_repo.generate_image.call_count, 3)

    async def test_phase_2_process_missing_infographic(self) -> None:
        """Verify Phase 2 raises ValueError if no infographic selected in state."""
        service = AutomationService(
            file_repo=self.file_repo,
            gdrive_repo=self.gdrive_repo,
            notebooklm_repo=self.notebooklm_repo,
            gemini_repo=self.gemini_repo,
            prompt_manager=self.prompt_manager,
            ffmpeg_wrapper=self.ffmpeg_wrapper,
        )

        state = ProjectState(
            project_dir="/mock/base/khutbah_1",
            audio_path="/mock/base/khutbah_1/audio.mp3",
            summary_v1="Summary",
            themes=["Theme1"],
            selected_infographic_path="",
        )

        with self.assertRaises(ValueError) as ctx:
            await service.phase_2_process(state)
        self.assertIn("selected infographic", str(ctx.exception))

    async def test_phase_2_process_success(self) -> None:
        """Verify Phase 2 executes concept math, image math, and video math."""
        project_dir = self.tmp_path / "project_1"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "thumbnails").mkdir(parents=True, exist_ok=True)

        infographic_path = str(project_dir / "infographic_1.png")
        audio_path = str(project_dir / "audio.mp3")
        bgm_path = str(self.tmp_path / "bgm.mp3")

        service = AutomationService(
            file_repo=self.file_repo,
            gdrive_repo=self.gdrive_repo,
            notebooklm_repo=self.notebooklm_repo,
            gemini_repo=self.gemini_repo,
            prompt_manager=self.prompt_manager,
            ffmpeg_wrapper=self.ffmpeg_wrapper,
            bgm_path=bgm_path,
        )

        themes = ["ThemeA", "ThemeB"]  # k = 2
        state = ProjectState(
            project_dir=str(project_dir),
            audio_path=audio_path,
            summary_v1="Summary text",
            themes=themes,
            selected_infographic_path=infographic_path,
        )

        assets = await service.phase_2_process(state)

        # Concept Math: k=2 -> k+1 = 3 calls to generate_structured_concepts
        self.assertEqual(self.gemini_repo.generate_structured_concepts.call_count, 3)

        # Flattened concepts: 3 * (k + 1) = 9
        # Image Math: 9 thumbnails generated
        self.assertEqual(self.gemini_repo.generate_image.call_count, 9)

        # Video Math: FFmpegWrapper called with selected infographic
        self.ffmpeg_wrapper.create_final_video.assert_called_once_with(
            infographic_path,
            audio_path,
            str((project_dir / "final_video.mp4").resolve()),
        )
        self.ffmpeg_wrapper.create_short_video.assert_called_once_with(
            infographic_path,
            bgm_path,
            str((project_dir / "shorts_video.mp4").resolve()),
        )
        self.ffmpeg_wrapper.create_short_thumbnail.assert_called_once_with(
            infographic_path, str((project_dir / "shorts_thumbnail.png").resolve())
        )

        # Total assets returned: 9 thumbnails + 3 video/short assets = 12
        self.assertEqual(len(assets), 12)
        self.assertIn(str((project_dir / "final_video.mp4").resolve()), assets)
        self.assertIn(str((project_dir / "shorts_video.mp4").resolve()), assets)
        self.assertIn(str((project_dir / "shorts_thumbnail.png").resolve()), assets)

    async def test_phase_2_copies_fancy_shorts_when_resource_present(self) -> None:
        """Verify phase_2 copies shorts_video_fancy.mp4 if found in resources_dir."""
        base_dir = Path(self.temp_dir.name)
        project_dir = base_dir / "test_project_fancy"
        project_dir.mkdir(parents=True, exist_ok=True)
        resources_dir = base_dir / "custom_resources"
        resources_dir.mkdir(parents=True, exist_ok=True)
        fancy_file = resources_dir / "shorts_video_fancy.mp4"
        fancy_file.write_bytes(b"mock fancy mp4 bytes")

        service = AutomationService(
            file_repo=self.file_repo,
            gdrive_repo=self.gdrive_repo,
            notebooklm_repo=self.notebooklm_repo,
            gemini_repo=self.gemini_repo,
            prompt_manager=self.prompt_manager,
            ffmpeg_wrapper=self.ffmpeg_wrapper,
            resources_dir=str(resources_dir),
        )

        state = ProjectState(
            project_dir=str(project_dir.resolve()),
            audio_path=str((project_dir / "audio.mp3").resolve()),
            summary_v1="Summary",
            themes=[],
            selected_infographic_path=str((project_dir / "info.png").resolve()),
        )

        self.gemini_repo.generate_structured_concepts.return_value = ConceptList(
            concepts=[]
        )
        assets = await service.phase_2_process(state)

        copied_fancy = project_dir / "shorts_video_fancy.mp4"
        self.assertTrue(copied_fancy.exists())
        self.assertEqual(copied_fancy.read_bytes(), b"mock fancy mp4 bytes")
        self.assertIn(str(copied_fancy.resolve()), assets)
