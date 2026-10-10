import unittest
from unittest.mock import AsyncMock, MagicMock

from app.backend.repositories.notebooklm_repo import NotebookLMRepo


class TestNotebookLMRepo(unittest.IsolatedAsyncioTestCase):
    async def test_generate_summary_calls_client(self) -> None:
        mock_client = MagicMock()
        mock_notebook = MagicMock()
        mock_notebook.id = "nb-123"

        mock_ask_result = MagicMock()
        mock_ask_result.answer = "This is a detailed summary of the audio file."

        mock_client.notebooks.create = AsyncMock(return_value=mock_notebook)
        mock_client.sources.add_file = AsyncMock()
        mock_client.chat.ask = AsyncMock(return_value=mock_ask_result)

        repo = NotebookLMRepo(client=mock_client)
        summary = await repo.generate_summary("/path/to/podcast.mp3")

        self.assertEqual(summary, "This is a detailed summary of the audio file.")
        mock_client.notebooks.create.assert_awaited_once()
        mock_client.sources.add_file.assert_awaited_once_with(
            notebook_id="nb-123", file_path="/path/to/podcast.mp3", wait=True
        )
        mock_client.chat.ask.assert_awaited_once()

    async def test_generate_hashtags_extracts_tags(self) -> None:
        mock_client = MagicMock()
        mock_notebook = MagicMock()
        mock_notebook.id = "nb-456"

        mock_ask_result = MagicMock()
        mock_ask_result.answer = "Here are the tags: #YouTube #AI #Automation #Podcast"

        mock_client.notebooks.create = AsyncMock(return_value=mock_notebook)
        mock_client.sources.add_file = AsyncMock()
        mock_client.chat.ask = AsyncMock(return_value=mock_ask_result)

        repo = NotebookLMRepo(client=mock_client)
        tags = await repo.generate_hashtags("/path/to/podcast.mp3")

        self.assertEqual(tags, ["#YouTube", "#AI", "#Automation", "#Podcast"])
        mock_client.notebooks.create.assert_awaited_once()
        mock_client.sources.add_file.assert_awaited_once_with(
            notebook_id="nb-456", file_path="/path/to/podcast.mp3", wait=True
        )
        mock_client.chat.ask.assert_awaited_once()

    async def test_generate_hashtags_fallback_formatting(self) -> None:
        mock_client = MagicMock()
        mock_notebook = MagicMock()
        mock_notebook.id = "nb-789"

        mock_ask_result = MagicMock()
        mock_ask_result.answer = "tech, coding, tutorial"

        mock_client.notebooks.create = AsyncMock(return_value=mock_notebook)
        mock_client.sources.add_file = AsyncMock()
        mock_client.chat.ask = AsyncMock(return_value=mock_ask_result)

        repo = NotebookLMRepo(client=mock_client)
        tags = await repo.generate_hashtags("/path/to/code.mp3")

        self.assertEqual(tags, ["#tech", "#coding", "#tutorial"])
