import unittest
from unittest.mock import AsyncMock, MagicMock, patch

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
        mock_client.chat.ask.assert_awaited_once_with(
            notebook_id="nb-123",
            question="Translate this into English and structure the content in well defined topics.",
        )

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
        mock_client.chat.ask.assert_awaited_once_with(
            notebook_id="nb-456",
            question=(
                "Provide me with 5 to 10 topic-specific hashtags that I can use to upload "
                "this as a YouTube video. Output each hashtag prefixed with # separated by spaces."
            ),
        )

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

    async def test_custom_prompt_manager_injection(self) -> None:
        mock_client = MagicMock()
        mock_notebook = MagicMock()
        mock_notebook.id = "nb-custom"

        mock_ask_result = MagicMock()
        mock_ask_result.answer = "custom answer"

        mock_client.notebooks.create = AsyncMock(return_value=mock_notebook)
        mock_client.sources.add_file = AsyncMock()
        mock_client.chat.ask = AsyncMock(return_value=mock_ask_result)

        mock_pm = MagicMock()
        mock_pm.get_summary_prompt.return_value = "custom summary prompt"

        repo = NotebookLMRepo(client=mock_client, prompt_manager=mock_pm)
        await repo.generate_summary("/path/to/audio.mp3")

        mock_pm.get_summary_prompt.assert_called_once()
        mock_client.chat.ask.assert_awaited_once_with(
            notebook_id="nb-custom", question="custom summary prompt"
        )

    @patch("app.backend.repositories.notebooklm_repo.NotebookLMClient")
    async def test_generate_summary_from_storage(
        self, mock_client_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.from_storage.return_value = mock_ctx

        mock_notebook = MagicMock()
        mock_notebook.id = "nb-storage"
        mock_client.notebooks.create = AsyncMock(return_value=mock_notebook)
        mock_client.sources.add_file = AsyncMock()
        mock_ask_result = MagicMock()
        mock_ask_result.answer = "Storage summary"
        mock_client.chat.ask = AsyncMock(return_value=mock_ask_result)

        repo = NotebookLMRepo()
        summary = await repo.generate_summary("/path/to/podcast.mp3")

        self.assertEqual(summary, "Storage summary")
        mock_client_cls.from_storage.assert_called_once_with(
            keepalive=600, allow_headless=True
        )
        mock_ctx.__aenter__.assert_awaited_once()
        mock_ctx.__aexit__.assert_awaited_once()

    @patch("app.backend.repositories.notebooklm_repo.NotebookLMClient")
    async def test_generate_summary_with_auth(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        mock_notebook = MagicMock()
        mock_notebook.id = "nb-auth"
        mock_client.notebooks.create = AsyncMock(return_value=mock_notebook)
        mock_client.sources.add_file = AsyncMock()
        mock_ask_result = MagicMock()
        mock_ask_result.answer = "Auth summary"
        mock_client.chat.ask = AsyncMock(return_value=mock_ask_result)

        repo = NotebookLMRepo(auth="test-auth-token")
        summary = await repo.generate_summary("/path/to/podcast.mp3")

        self.assertEqual(summary, "Auth summary")
        mock_client_cls.assert_called_once_with(auth="test-auth-token", keepalive=600)
        mock_client.__aenter__.assert_awaited_once()
        mock_client.__aexit__.assert_awaited_once()
