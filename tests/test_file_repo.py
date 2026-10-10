import tempfile
import unittest
from pathlib import Path

from app.backend.repositories.file_repo import FileRepo


class TestFileRepo(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.repo = FileRepo(base_dir=str(self.base_path))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_project_env(self) -> None:
        project_dir_str = self.repo.create_project_env("sample_audio.mp3")
        project_dir = Path(project_dir_str)

        self.assertTrue(project_dir.exists())
        self.assertTrue(project_dir.is_dir())
        self.assertEqual(project_dir.name, "sample_audio")
        self.assertTrue((project_dir / "infographics").is_dir())
        self.assertTrue((project_dir / "thumbnails").is_dir())

    def test_create_project_env_with_explicit_base_dir(self) -> None:
        alt_dir = self.base_path / "custom_output"
        project_dir_str = self.repo.create_project_env(
            "episode_12.wav", base_dir=str(alt_dir)
        )
        project_dir = Path(project_dir_str)

        self.assertTrue(project_dir.exists())
        self.assertEqual(project_dir.parent.resolve(), alt_dir.resolve())
        self.assertTrue((project_dir / "infographics").is_dir())
        self.assertTrue((project_dir / "thumbnails").is_dir())

    def test_save_text_version_appends_extension(self) -> None:
        project_dir_str = self.repo.create_project_env("sample_audio.mp3")
        file_path_str = self.repo.save_text_version(
            content="# Title\nAutomated script",
            version="v1_auto",
            dir_path=project_dir_str,
        )
        file_path = Path(file_path_str)

        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.name, "v1_auto.md")
        self.assertEqual(
            file_path.read_text(encoding="utf-8"), "# Title\nAutomated script"
        )

    def test_save_text_version_with_existing_md_extension(self) -> None:
        project_dir_str = self.repo.create_project_env("sample_audio.mp3")
        file_path_str = self.repo.save_text_version(
            content="# Title\nEdited script",
            version="v2_edited.md",
            dir_path=project_dir_str,
        )
        file_path = Path(file_path_str)

        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.name, "v2_edited.md")
        self.assertEqual(
            file_path.read_text(encoding="utf-8"), "# Title\nEdited script"
        )
