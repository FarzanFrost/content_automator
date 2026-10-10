import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from app.backend.entities.ai_models import ConceptList, ThumbnailConcept
from app.backend.repositories.gemini_repo import GeminiRepo


class TestGeminiRepo(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_generate_image_saves_bytes(self) -> None:
        mock_inline_data = MagicMock()
        mock_inline_data.data = b"fake-gemini-image-bytes"

        mock_part = MagicMock()
        mock_part.inline_data = mock_inline_data

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        repo = GeminiRepo(image_client=mock_client)
        output_file = self.tmp_path / "thumbnails" / "thumb_1.png"

        result_path = await repo.generate_image(
            prompt="High quality YouTube thumbnail with glowing neon text",
            output_path=str(output_file),
        )

        self.assertEqual(result_path, str(output_file.resolve()))
        self.assertTrue(output_file.exists())
        self.assertEqual(output_file.read_bytes(), b"fake-gemini-image-bytes")

        mock_client.aio.models.generate_content.assert_awaited_once()
        call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
        self.assertIsInstance(call_kwargs["model"], str)
        self.assertEqual(call_kwargs["contents"], "High quality YouTube thumbnail with glowing neon text")

    async def test_generate_image_empty_raises_value_error(self) -> None:
        mock_response = MagicMock()
        mock_response.candidates = []

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        repo = GeminiRepo(image_client=mock_client)
        output_file = self.tmp_path / "thumbnails" / "thumb_empty.png"

        with self.assertRaises(ValueError):
            await repo.generate_image(
                prompt="Prompt",
                output_path=str(output_file),
            )

    async def test_generate_structured_concepts_returns_concept_list(self) -> None:
        # Create a mock image file
        mock_img_path = self.tmp_path / "source.png"
        mock_img_path.write_bytes(b"image-binary-data")

        expected_concept = ThumbnailConcept(
            category="educational",
            visual_hook="Brain exploding with light",
            design_directive="Split screen layout",
            text_hook="Stop Doing This!",
            color_theory="High contrast yellow and black",
        )
        expected_list = ConceptList(concepts=[expected_concept])

        mock_response = MagicMock()
        mock_response.text = expected_list.model_dump_json()

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        repo = GeminiRepo(concepts_client=mock_client)

        result = await repo.generate_structured_concepts(
            prompt="Analyze this visual and generate thumbnail concepts",
            image_path=str(mock_img_path),
        )

        self.assertIsInstance(result, ConceptList)
        self.assertEqual(len(result.concepts), 1)
        self.assertEqual(result.concepts[0].text_hook, "Stop Doing This!")
        self.assertEqual(result.concepts[0].category, "educational")
        mock_client.aio.models.generate_content.assert_awaited_once()
