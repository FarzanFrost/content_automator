import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from app.backend.repositories.gdrive_repo import GoogleDriveRepo


class TestGoogleDriveRepo(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dest_dir = Path(self.temp_dir.name)
        self.repo = GoogleDriveRepo()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_extract_file_id_various_urls(self) -> None:
        urls = [
            (
                "https://drive.google.com/file/d/1a2b3c4d5e/view?usp=sharing",
                "1a2b3c4d5e",
            ),
            ("https://drive.google.com/open?id=xyz789", "xyz789"),
            ("https://drive.google.com/uc?id=abc12345&export=download", "abc12345"),
        ]
        for url, expected_id in urls:
            self.assertEqual(self.repo.extract_file_id(url), expected_id)

    def test_extract_filename_from_content_disposition(self) -> None:
        header = 'attachment; filename="podcast_episode_1.mp3"'
        filename = self.repo.extract_filename_from_header(header)
        self.assertEqual(filename, "podcast_episode_1.mp3")

    def test_extract_filename_fallback_when_header_absent(self) -> None:
        filename = self.repo.extract_filename_from_header(None, default_id="file123")
        self.assertEqual(filename, "file123.mp3")

    def test_download_audio_success_with_header_filename(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Disposition": 'attachment; filename="interview_recording.mp3"'
        }
        mock_response.iter_bytes.return_value = [
            b"mock-audio-chunk-1",
            b"mock-audio-chunk-2",
        ]

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        repo = GoogleDriveRepo(http_client=mock_client)
        url = "https://drive.google.com/file/d/test1234/view"

        saved_path_str = repo.download_audio(url=url, dest_dir=str(self.dest_dir))
        saved_path = Path(saved_path_str)

        self.assertTrue(saved_path.exists())
        self.assertEqual(saved_path.name, "interview_recording.mp3")
        self.assertEqual(
            saved_path.read_bytes(), b"mock-audio-chunk-1mock-audio-chunk-2"
        )

    def test_download_audio_fallback_filename(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.iter_bytes.return_value = [b"audio-bytes"]

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        repo = GoogleDriveRepo(http_client=mock_client)
        url = "https://drive.google.com/uc?id=unique_id_999"

        saved_path_str = repo.download_audio(url=url, dest_dir=str(self.dest_dir))
        saved_path = Path(saved_path_str)

        self.assertTrue(saved_path.exists())
        self.assertEqual(saved_path.name, "unique_id_999.mp3")
        self.assertEqual(saved_path.read_bytes(), b"audio-bytes")
